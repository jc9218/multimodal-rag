const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE_URL = rawApiUrl.replace(/\/+$/, "");
const UPLOAD_RETRY_DELAYS_MS = [2000, 5000];

// Objetivo: esperar antes de repetir una operación transitoria.
// Entradas: delayMs: milisegundos de espera.
// Salida: promesa resuelta después del intervalo indicado.
function wait(delayMs: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, delayMs));
}

// Objetivo: clasificar si un estado HTTP puede recuperarse reintentando.
// Entradas: status: código HTTP recibido.
// Salida: true para errores transitorios; false para errores definitivos.
function isRetryableUploadStatus(status: number): boolean {
  return status === 408 || status === 425 || status === 429 || status >= 500;
}

// Objetivo: decidir si un error de subida puede reintentarse.
// Entradas: error: error producido por fetch o por la respuesta HTTP.
// Salida: true cuando la causa puede ser temporal.
function isRetryableUploadError(error: unknown): boolean {
  if (typeof error !== "object" || error === null) return true;
  const candidate = error as { status?: number; name?: string };
  return (
    candidate.name === "AbortError" ||
    candidate.status === undefined ||
    isRetryableUploadStatus(candidate.status)
  );
}

// Clase: contrato de datos BoundingBox.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
export interface BoundingBox {
  page: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

// Clase: contrato de datos ExtractedImage.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
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

// Clase: contrato de datos RetrievedChunk.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
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

// Clase: contrato de datos QueryResponse.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
export interface QueryResponse {
  query: string;
  answer: string;
  sources: RetrievedChunk[];
  images: ExtractedImage[];
  is_defensive: boolean;
}

// Clase: contrato de datos IngestionJob.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
export interface IngestionJob {
  job_id: string;
  document_id: string;
  filename: string;
  status: "PENDING" | "EXTRACTING" | "INDEXING" | "WAITING_QUOTA" | "COMPLETED" | "FAILED" | "CANCELLED";
  progress: number;
  message: string;
  error?: string;
}

// Objetivo: logApiRequest.
// Entradas: method: string, endpoint: string, payload?: Record<string, unknown>.
// Salida: valor indicado por la firma o efecto de la operación.
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

// Objetivo: logApiResponse.
// Entradas: method: string, endpoint: string, status: number | string, data: unknown.
// Salida: valor indicado por la firma o efecto de la operación.
function logApiResponse(method: string, endpoint: string, status: number | string, data: unknown) {
  console.log(`📡 [Frontend API Response] ${status} ${method} ${endpoint}`);
}

// Objetivo: logApiError.
// Entradas: endpoint: string, status: number | string, errorDetail: unknown.
// Salida: valor indicado por la firma o efecto de la operación.
function logApiError(endpoint: string, status: number | string, errorDetail: unknown) {
  console.error(`🚨 [Frontend API Error] Endpoint: ${endpoint} | Status: ${status}`, errorDetail);
}

// Objetivo: checkHealth.
// Entradas: Ninguna..
// Salida: valor indicado por la firma o efecto de la operación.
export async function checkHealth(): Promise<boolean> {
  const url = `${API_BASE_URL}/health`;
  try {
    const res = await fetch(url);
    return res.ok;
  } catch {
    return false;
  }
}

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
            "El servidor en la nube de Render tardó en responder después de varios intentos. "
            + "Puede estar despertándose de su estado inactivo; reintenta en unos segundos."
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

// Objetivo: getJobStatus.
// Entradas: jobId: string.
// Salida: valor indicado por la firma o efecto de la operación.
export async function getJobStatus(jobId: string): Promise<IngestionJob> {
  const url = `${API_BASE_URL}/api/v1/jobs/${jobId}`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
      logApiError(url, res.status, err);
      throw new Error("No se pudo obtener el estado del trabajo");
    }
    const data: IngestionJob = await res.json();
    logApiResponse("GET", url, res.status, data);
    return data;
  } catch (error) {
    logApiError(url, "NETWORK_ERROR", error);
    throw error;
  }
}

// Objetivo: cancelJob.
// Entradas: jobId: string.
// Salida: valor indicado por la firma o efecto de la operación.
export async function cancelJob(jobId: string): Promise<{ status: string; message: string }> {
  const url = `${API_BASE_URL}/api/v1/jobs/${jobId}/cancel`;
  logApiRequest("POST", url);
  try {
    const res = await fetch(url, { method: "POST" });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}: Error al cancelar trabajo` }));
      logApiError(url, res.status, err);
      throw new Error(err.detail || "Error al cancelar trabajo");
    }
    const data = await res.json();
    logApiResponse("POST", url, res.status, data);
    return data;
  } catch (error) {
    logApiError(url, "NETWORK_ERROR", error);
    throw error;
  }
}

// Clase: contrato de datos ChatHistoryPayload.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
export interface ChatHistoryPayload {
  role: string;
  content: string;
}

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
      throw new Error(
        err.detail || "No fue posible procesar la consulta técnica en este momento. Por favor reintenta en unos instantes."
      );
    }

    const data: QueryResponse = await res.json();
    logApiResponse("POST", url, res.status, data);
    return data;
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error?.name === "AbortError") {
      logApiError(url, "TIMEOUT", "La solicitud superó el tiempo máximo de espera.");
      throw new Error("El servidor tardó más de lo esperado en responder. Por favor, reintenta tu pregunta.");
    }
    if (!error?.message?.includes("HTTP")) {
      logApiError(url, "NETWORK_ERROR", error);
    }
    throw error;
  }
}

// Objetivo: getDocuments.
// Entradas: Ninguna..
// Salida: valor indicado por la firma o efecto de la operación.
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

// Objetivo: deleteDocument.
// Entradas: documentId: string.
// Salida: valor indicado por la firma o efecto de la operación.
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
      throw new Error(err.detail || "Error al eliminar documento de la base de datos");
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

// Objetivo: getFullImageUrl.
// Entradas: relativeUrl: string.
// Salida: valor indicado por la firma o efecto de la operación.
export function getFullImageUrl(relativeUrl: string): string {
  if (!relativeUrl) return "";
  if (relativeUrl.startsWith("http")) return relativeUrl;
  return `${API_BASE_URL}${relativeUrl}`;
}
