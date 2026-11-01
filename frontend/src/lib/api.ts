const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE_URL = rawApiUrl.replace(/\/+$/, "");
const UPLOAD_RETRY_DELAYS_MS = [2000, 5000];

// Purpose: Wait before retrying a transient operation.
// Inputs: delayMs: wait duration in milliseconds.
// Output: Promise resolved after the specified interval.
/**
 * wait function..
 *
 * @param delayMs - number.
 * @returns Promise<void>..
 */
function wait(delayMs: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, delayMs));
}
// Purpose: Classify whether an HTTP status can be recovered by retrying.

// Inputs: status: received HTTP status code.
// Output: True for transient errors; false for definitive errors.
/**
 * isRetryableUploadStatus function..
 *
 * @param status - number.
 * @returns boolean..
 */
function isRetryableUploadStatus(status: number): boolean {
  return status === 408 || status === 425 || status === 429 || status >= 500;
}
// Purpose: Decide whether an upload error can be retried.
// Inputs: error: error produced by fetch or an HTTP response.

// Output: True when the cause may be temporary.
/**
 * isRetryableUploadError function..
 *
 * @param error - unknown.
 * @returns boolean..
 */
function isRetryableUploadError(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return true;
  const candidate = error as { status?: number; name?: string };
  return (
    candidate.name === "AbortError" ||
    candidate.status === undefined ||
    isRetryableUploadStatus(candidate.status)
  );
}
// Data contract BoundingBox.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.

export interface BoundingBox {
  page: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}
// Data contract ExtractedImage.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
export interface ExtractedImage {

  id: string;
  document_id: string;
  filename: string;
  page: number;
  bbox: BoundingBox;
  url: string;
  format: string;
  width_px: number;
  height_px: number;
}
// Data contract RetrievedChunk.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
export interface RetrievedChunk {
  chunk_id: string;

  document_id: string;
  document_name: string;
  text: string;
  page: number;
  bbox: BoundingBox;
  score: number;
  associated_images: ExtractedImage[];
}
// Data contract QueryResponse.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
export interface QueryResponse {
  query: string;
  answer: string;

  sources: RetrievedChunk[];
  images: ExtractedImage[];
  is_defensive: boolean;
}
// Data contract IngestionJob.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
export interface IngestionJob {
  job_id: string;
  document_id: string;
  filename: string;

  status: "PENDING" | "EXTRACTING" | "INDEXING" | "WAITING_QUOTA" | "COMPLETED" | "FAILED" | "CANCELLED";
  progress: number;
  message: string;
  error?: string;
}
// Purpose: logApiRequest.
// Inputs: method: string, endpoint: string, payload?: Record<string, unknown>.
// Output: Value specified by the signature or operation effect.
/**
 * logApiRequest function..
 *
 * @param method - string.
 * @param endpoint - string.
 * @param payload? - Record<string.
 * @param unknown> - unknown.
 * @returns void..
 */
function logApiRequest(method: string, endpoint: string, payload?: Record<string, unknown>) {
  if (payload !== undefined) {
    console.log(`🚀 [Frontend API Request] ${method} ${endpoint}`, {
      ...payload,
      query: payload.query ? "[redacted]" : undefined,

      chat_history: Array.isArray(payload.chat_history)
        ? `[${payload.chat_history.length} mensajes]`
        : undefined,
    });
  } else {
    console.log(`🚀 [Frontend API Request] ${method} ${endpoint}`);
  }
}
// Purpose: logApiResponse.
// Inputs: method: string, endpoint: string, status: number | string, data: unknown.
// Output: Value specified by the signature or operation effect.
/**
 * logApiResponse function..
 *
 * @param method - string.
 * @param endpoint - string.
 * @param status - number | string.
 * @param data - unknown.
 * @returns void..
 */
function logApiResponse(method: string, endpoint: string, status: number | string, data: unknown) {
  console.log(`📡 [Frontend API Response] ${status} ${method} ${endpoint}`);
}
// Purpose: logApiError.
// Inputs: endpoint: string, status: number | string, errorDetail: unknown.
// Output: Value specified by the signature or operation effect.

/**
 * logApiError function..
 *
 * @param endpoint - string.
 * @param status - number | string.
 * @param errorDetail - unknown.
 * @returns void..
 */
function logApiError(endpoint: string, status: number | string, errorDetail: unknown) {
  console.error(`🚨 [Frontend API Error] Endpoint: ${endpoint} | Status: ${status}`, errorDetail);
}
// Purpose: checkHealth.
// Inputs: None.
// Output: Value specified by the signature or operation effect.
/**
 * checkHealth function..
 *
 * @returns Promise<boolean>. */
export async function checkHealth(): Promise<boolean> {

  const url = `${API_BASE_URL}/health`;
  try {
    const res = await fetch(url);
    return res.ok;
  } catch {
    return false;
  }

}
/**
 * uploadDocument function.
 *
 * @param file - File.
 * @param timeoutMs - number = 120000.
 * @param maxAttempts - number = UPLOAD_RETRY_DELAYS_MS.length + 1.
 * @returns Promise<..
 */
export async function uploadDocument(
  file: File,
  timeoutMs: number = 120000,
  maxAttempts: number = UPLOAD_RETRY_DELAYS_MS.length + 1
): Promise<{ job_id: string; document_id: string; filename: string }> {
  const url = `${API_BASE_URL}/api/v1/documents/upload`;
  const uploadId = crypto.randomUUID();
  logApiRequest("POST", url, { filename: file.name, sizeBytes: file.size });
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
    try {

      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(url, {
        method: "POST",
        body: formData,
        signal: controller.signal,
        headers: { "X-Upload-Id": uploadId },
      });
      if (!res.ok) {

        const err = await res.json().catch(() => ({
          detail: `HTTP ${res.status}: Error al subir el documento`,
        }));
        const uploadError = new Error(err.detail || "Error al subir documento") as Error & {

          status?: number;
        };
        uploadError.status = res.status;
        logApiError(url, res.status, err);

        if (res.status >= 500) {
          uploadError.message =
            "No se pudo subir el archivo. El archivo no fue conservado; intenta nuevamente.";
        }
        throw uploadError;
      }
      const data = await res.json();

      logApiResponse("POST", url, res.status, data);
      return data;
    } catch (error: unknown) {
      const retryable = isRetryableUploadError(error);
      const hasAttemptsLeft = attempt < maxAttempts - 1;
      if (!retryable || !hasAttemptsLeft) {
        if (error instanceof Error && error.name === "AbortError") {
          logApiError(url, "TIMEOUT", "La subida superó el tiempo de espera.");
          throw new Error(
            "No se pudo confirmar la subida del archivo después de varios intentos. "
            + "Intenta nuevamente en unos segundos."
          );
        }
        if (!(error instanceof Error && error.message.includes("HTTP"))) {
          logApiError(url, "NETWORK_ERROR", error);
        }

        throw error;
      }
      const delayMs = UPLOAD_RETRY_DELAYS_MS[attempt] ?? UPLOAD_RETRY_DELAYS_MS.at(-1)!;
      logApiError(url, `RETRY_${attempt + 1}`, {
        error,
        delayMs,
        reason: "Error transitorio durante la subida",
      });
      await wait(delayMs);
    } finally {
      clearTimeout(timeoutId);
    }
  }
  throw new Error("No fue posible subir el documento.");
}
// Purpose: getJobStatus.
// Inputs: jobId: string.
// Output: Value specified by the signature or operation effect.
/**
 * getJobStatus function..
 *
 * @param jobId - string.
 * @returns Promise<IngestionJob>..
 */
export async function getJobStatus(jobId: string): Promise<IngestionJob> {
  const url = `${API_BASE_URL}/api/v1/jobs/${jobId}`;

  try {
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      logApiError(url, res.status, err);
      throw new Error("No se pudo consultar el estado del archivo.");
    }
    const data: IngestionJob = await res.json();
    logApiResponse("GET", url, res.status, data);
    return data;
  } catch (error) {
    logApiError(url, "NETWORK_ERROR", error);

    throw error;
  }
}

// Purpose: cancelJob.
// Inputs: jobId: string.
// Output: Value specified by the signature or operation effect.
/**
 * cancelJob function..
 *
 * @param jobId - string.
 * @returns Promise<..
 */
export async function cancelJob(jobId: string): Promise<{ status: string; message: string }> {
  const url = `${API_BASE_URL}/api/v1/jobs/${jobId}/cancel`;
  logApiRequest("POST", url);
  try {
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}: Error al cancelar trabajo` }));
      logApiError(url, res.status, err);
      throw new Error("No se pudo detener el procesamiento del archivo.");
    }
    const data = await res.json();
    logApiResponse("POST", url, res.status, data);
    return data;
  } catch (error) {
    logApiError(url, "NETWORK_ERROR", error);
    throw error;
  }
}

// Data contract ChatHistoryPayload.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
export interface ChatHistoryPayload {
  role: string;
  content: string;
}
/**
 * queryRAG function.
 *
 * @param query - string.
 * @param documentId? - string.
 * @param documentIds? - string[].
 * @param chatHistory? - ChatHistoryPayload[].
 * @param timeoutMs - number = 120000.
 * @returns Promise<QueryResponse>.
 */
export async function queryRAG(
  query: string,
  documentId?: string,
  documentIds?: string[],
  chatHistory?: ChatHistoryPayload[],
  timeoutMs: number = 120000
): Promise<QueryResponse> {
  const url = `${API_BASE_URL}/api/v1/chat/query`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
  const payload = {
    query,
    top_k: 4,
    document_id: documentId || null,
    document_ids: documentIds || null,

    chat_history: chatHistory || null,
  };
  logApiRequest("POST", url, payload);
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,

      body: JSON.stringify(payload),
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      const err = await res
        .json()
        .catch(() => ({ detail: `HTTP ${res.status}: No se pudo obtener respuesta del servidor.` }));
      logApiError(url, res.status, err);
      throw new Error("No fue posible obtener una respuesta en este momento. Por favor, intenta nuevamente.");
    }
    const data: QueryResponse = await res.json();
    logApiResponse("POST", url, res.status, data);
    return data;
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error?.name === "AbortError") {
      logApiError(url, "TIMEOUT", "La solicitud superó el tiempo máximo de espera.");
      throw new Error("La respuesta está tardando más de lo esperado. Por favor, intenta nuevamente.");

    }
    if (!error?.message?.includes("HTTP")) {

      logApiError(url, "NETWORK_ERROR", error);
    }
    throw error;
  }
}
// Purpose: getDocuments.
// Inputs: None.
// Output: Value specified by the signature or operation effect.

/**
 * getDocuments function..
 *
 * @returns Promise<. */
export async function getDocuments(): Promise<{ id: string; name: string; created_at?: string }[]> {
  const url = `${API_BASE_URL}/api/v1/documents`;

  try {
    const res = await fetch(url);
    if (!res.ok) {
      logApiError(url, res.status, "Respuesta fallida al listar documentos");
      return [];
    }
    const data = await res.json();
    logApiResponse("GET", url, res.status, data);

    return data;
  } catch (error) {
    logApiError(url, "NETWORK_ERROR", error);
    return [];
  }
}
// Purpose: deleteDocument.
// Inputs: documentId: string.
// Output: Value specified by the signature or operation effect.
/**
 * deleteDocument function.
 * * @param documentId - string.
 * @returns Promise<void>..
 */
export async function deleteDocument(documentId: string): Promise<void> {
  const url = `${API_BASE_URL}/api/v1/documents/${documentId}`;
  logApiRequest("DELETE", url);
  try {
    const res = await fetch(url, {
      method: "DELETE",
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}: Error al eliminar documento` }));
      logApiError(url, res.status, err);
      throw new Error("No se pudo eliminar el archivo. Por favor, intenta nuevamente.");
    }
    const data = await res.json().catch(() => ({ status: "deleted", documentId }));
    logApiResponse("DELETE", url, res.status, data);
  } catch (error: any) {
    if (!error?.message?.includes("HTTP")) {
      logApiError(url, "NETWORK_ERROR", error);
    }
    throw error;
  }
}
// Purpose: getFullImageUrl.
// Inputs: relativeUrl: string.
// Output: Value specified by the signature or operation effect.
/**
 * getFullImageUrl function..
 *
 * @param relativeUrl - string.
 * @returns string..
 */
export function getFullImageUrl(relativeUrl: string): string {
  if (!relativeUrl) return "";
  if (relativeUrl.startsWith("http")) return relativeUrl;

  return `${API_BASE_URL}${relativeUrl}`;
}
