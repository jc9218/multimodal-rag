const rawApiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const API_BASE_URL = rawApiUrl.replace(/\/+$/, "");

export interface BoundingBox {
  page: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

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

export interface QueryResponse {
  query: string;
  answer: string;
  sources: RetrievedChunk[];
  images: ExtractedImage[];
  is_defensive: boolean;
}

export interface IngestionJob {
  job_id: string;
  document_id: string;
  filename: string;
  status: "PENDING" | "EXTRACTING" | "INDEXING" | "WAITING_QUOTA" | "COMPLETED" | "FAILED" | "CANCELLED";
  progress: number;
  message: string;
  error?: string;
}

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

function logApiResponse(method: string, endpoint: string, status: number | string, data: unknown) {
  console.log(`📡 [Frontend API Response] ${status} ${method} ${endpoint}`);
}

function logApiError(endpoint: string, status: number | string, errorDetail: unknown) {
  console.error(`🚨 [Frontend API Error] Endpoint: ${endpoint} | Status: ${status}`, errorDetail);
}

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
  timeoutMs: number = 120000
): Promise<{ job_id: string; document_id: string; filename: string }> {
  const url = `${API_BASE_URL}/api/v1/documents/upload`;
  logApiRequest("POST", url, { filename: file.name, sizeBytes: file.size });
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(url, {
      method: "POST",
      body: formData,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}: Error al subir el documento` }));
      logApiError(url, res.status, err);
      throw new Error(err.detail || "Error al subir documento");
    }

    const data = await res.json();
    logApiResponse("POST", url, res.status, data);
    return data;
  } catch (error: any) {
    clearTimeout(timeoutId);
    if (error?.name === "AbortError") {
      logApiError(url, "TIMEOUT", "La subida superó el tiempo de espera.");
      throw new Error(
        "El servidor en la nube de Render tardó en responder (puede estar despertándose de su estado inactivo). Por favor reintenta en unos segundos."
      );
    }
    if (!error?.message?.includes("HTTP")) {
      logApiError(url, "NETWORK_ERROR", error);
    }
    throw error;
  }
}

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

export function getFullImageUrl(relativeUrl: string): string {
  if (!relativeUrl) return "";
  if (relativeUrl.startsWith("http")) return relativeUrl;
  return `${API_BASE_URL}${relativeUrl}`;
}
