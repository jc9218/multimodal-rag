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
