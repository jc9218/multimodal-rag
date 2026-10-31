import { afterEach, describe, expect, it, vi } from "vitest";
import { getFullImageUrl, getJobStatus, queryRAG, uploadDocument } from "./api";

describe("API client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("normalizes relative image URLs without duplicating slashes", () => {
    expect(getFullImageUrl("/api/v1/images/doc/image.png")).toBe(
      "http://localhost:8000/api/v1/images/doc/image.png"
    );
    expect(getFullImageUrl("https://cdn.example/image.png")).toBe(
      "https://cdn.example/image.png"
    );
  });

  it("returns a typed job status", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            job_id: "job-1",
            document_id: "doc-1",
            filename: "manual.pdf",
            status: "EXTRACTING",
            progress: 0.25,
            message: "Página 1/4",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } }
        )
      )
    );

    await expect(getJobStatus("job-1")).resolves.toMatchObject({
      job_id: "job-1",
      status: "EXTRACTING",
      progress: 0.25,
    });
  });

  it("surfaces upload API failures instead of returning success", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "PDF inválido" }), {
        status: 400,
        headers: { "Content-Type": "application/json" },
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      uploadDocument(new File(["not a pdf"], "manual.pdf", { type: "application/pdf" }), 100, 3)
    ).rejects.toThrow("PDF inválido");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("retries transient upload failures and returns the successful job", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ detail: "Render despertando" }), { status: 503 })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ job_id: "job-1", document_id: "doc-1", filename: "manual.pdf" }),
          { status: 202, headers: { "Content-Type": "application/json" } }
        )
      );
    vi.stubGlobal("fetch", fetchMock);

    const promise = uploadDocument(
      new File(["%PDF-1.7"], "manual.pdf", { type: "application/pdf" }),
      100,
      2
    );
    await vi.advanceTimersByTimeAsync(2000);

    await expect(promise).resolves.toMatchObject({ job_id: "job-1" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });

  it("retries quota responses during upload", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify({ detail: "Quota excedida" }), { status: 429 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ job_id: "job-2", document_id: "doc-2", filename: "manual.pdf" }),
          { status: 202 }
        )
      );
    vi.stubGlobal("fetch", fetchMock);

    const promise = uploadDocument(
      new File(["%PDF-1.7"], "manual.pdf", { type: "application/pdf" }),
      100,
      2
    );
    await vi.advanceTimersByTimeAsync(2000);

    await expect(promise).resolves.toMatchObject({ job_id: "job-2" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });

  it("does not retry a definitive upload validation error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: "PDF inválido" }), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        })
      )
    );

    await expect(
      uploadDocument(new File(["not a pdf"], "manual.pdf", { type: "application/pdf" }))
    ).rejects.toThrow("PDF inválido");
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it("sends selected document IDs without logging query content", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          query: "resumen",
          answer: "Respuesta",
          sources: [],
          images: [],
          is_defensive: false,
        }),
        { status: 200, headers: { "Content-Type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchMock);
    const consoleSpy = vi.spyOn(console, "log").mockImplementation(() => undefined);

    await queryRAG("secreto del documento", undefined, ["doc-1"], [], 1000);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://localhost:8000/api/v1/chat/query",
      expect.objectContaining({
        body: expect.stringContaining('"document_ids":["doc-1"]'),
      })
    );
    expect(consoleSpy.mock.calls.flat().join(" ")).not.toContain("secreto del documento");
  });
});
