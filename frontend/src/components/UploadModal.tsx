"use client";

import React, { useState, useEffect, useRef } from "react";
import { UploadCloud, AlertCircle, X } from "lucide-react";
import { uploadDocument, getJobStatus, cancelJob, IngestionJob } from "@/lib/api";
import FileDropzone from "./upload/FileDropzone";
import IngestionProgressCard from "./upload/IngestionProgressCard";
// Data contract UploadModalProps.

// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
interface UploadModalProps {
  onDocumentIndexed: (
    docId: string,
    filename: string,
    createdAt?: string,
    targetChatId?: string
  ) => void;
  activeChatTitle?: string;
  activeChatId?: string;
}
const ACTIVE_INGESTION_JOB_KEY = "multimodal_rag_active_ingestion_job_v1";
// Data contract PersistedJob.

// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.

interface PersistedJob {
  jobId: string;
  filename: string;
  targetChatId?: string;
  savedAt: number;
}
// Purpose: persistActiveJob.
// Inputs: jobId: string, filename: string, targetChatId?: string.
// Output: Value specified by the signature or operation effect.
/**
 * persistActiveJob function..
 *
 * @param jobId - string.
 * @param filename - string.
 * @param targetChatId? - string.
 * @returns void..
 */
function persistActiveJob(jobId: string, filename: string, targetChatId?: string) {

  try {
    const data: PersistedJob = {
      jobId,
      filename,
      targetChatId,
      savedAt: Date.now(),
    };
    localStorage.setItem(ACTIVE_INGESTION_JOB_KEY, JSON.stringify(data));
  } catch (e) {
    console.warn("Could not persist active ingestion job to localStorage:", e);
  }
}
// Purpose: clearPersistedJob.
// Inputs: None.
// Output: Value specified by the signature or operation effect.
/**
 * clearPersistedJob function..
 *
 * @returns void. */
function clearPersistedJob() {
  try {

    localStorage.removeItem(ACTIVE_INGESTION_JOB_KEY);
  } catch {}
}
/**
 * UploadModal function.
 *
 * @param {
  onDocumentIndexed - unknown.
 * @param activeChatTitle - unknown.
 * @param activeChatId - unknown.
 * @param } - UploadModalProps.
 * @returns void..
 */
export default function UploadModal({
  onDocumentIndexed,
  activeChatTitle,
  activeChatId,
}: UploadModalProps) {
  const [uploading, setUploading] = useState(false);

  const [isCancelling, setIsCancelling] = useState(false);
  const [job, setJob] = useState<IngestionJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [fileQueue, setFileQueue] = useState<File[]>([]);
  const onDocumentIndexedRef = useRef(onDocumentIndexed);
  const activeChatIdRef = useRef(activeChatId);
  const pollIntervalRef = useRef<NodeJS.Timeout | null>(null);
  useEffect(() => {
    onDocumentIndexedRef.current = onDocumentIndexed;
    activeChatIdRef.current = activeChatId;
  }, [onDocumentIndexed, activeChatId]);

  // Clean up polling timer on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {

        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);
  // Auto-dismiss completed status card after 5 seconds if no more files in queue

  useEffect(() => {
    if (job?.status === "COMPLETED" && fileQueue.length === 0) {
      const timer = setTimeout(() => {
        setJob(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [job?.status, fileQueue.length]);
  // Restore any in-progress ingestion job from localStorage after reload/close

  useEffect(() => {
    try {
      const savedRaw = localStorage.getItem(ACTIVE_INGESTION_JOB_KEY);
      if (!savedRaw) return;
      const saved: PersistedJob = JSON.parse(savedRaw);
      if (!saved?.jobId || Date.now() - (saved.savedAt || 0) > 2 * 60 * 60 * 1000) {
        clearPersistedJob();
        return;
      }
      setUploading(true);

      setJob({
        job_id: saved.jobId,
        document_id: "",
        filename: saved.filename,
        status: "PENDING",
        progress: 0.1,
        message: "Recuperando estado del procesamiento...",

      });
      pollJob(saved.jobId, saved.targetChatId);
    } catch (e) {
      console.warn("Could not restore active ingestion job from localStorage:", e);
    }

  }, []);
  // Purpose: handleCancelUpload.
  // Inputs: None.
  // Output: Value specified by the signature or operation effect.
  const handleCancelUpload = async () => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    clearPersistedJob();

    if (!job?.job_id || job.job_id === "init") {
      setUploading(false);
      setJob(null);
      setFileQueue([]);
      return;
    }

    try {
      setIsCancelling(true);
      await cancelJob(job.job_id);
      setUploading(false);
      setJob(null);
      setFileQueue([]);
      setError("Carga cancelada y archivo eliminado correctamente.");
      setTimeout(() => setError(null), 4000);
    } catch (err: any) {
      console.error("🚨 [UploadModal:handleCancelUpload] Error al cancelar trabajo:", err);

      setError("No se pudo cancelar el procesamiento del documento.");
    } finally {
      setIsCancelling(false);
    }
  };
  // Purpose: processNextInQueue.
  // Inputs: remainingQueue: File[].

  // Output: Value specified by the signature or operation effect.
  const processNextInQueue = async (remainingQueue: File[]) => {
    if (remainingQueue.length === 0) {
      setUploading(false);
      return;
    }
    const [nextFile, ...rest] = remainingQueue;
    setFileQueue(rest);
    await startSingleUpload(nextFile, rest);
  };
  // Purpose: startSingleUpload.
  // Inputs: targetFile: File, remainingFiles: File[] = [].
  // Output: Value specified by the signature or operation effect.
  const startSingleUpload = async (targetFile: File, remainingFiles: File[] = []) => {
    try {
      setUploading(true);

      setError(null);
      setJob({
        job_id: "init",
        document_id: "",
        filename: targetFile.name,
        status: "PENDING",
        progress: 0.05,
        message: "Enviando documento al servidor...",
      });

      const currentTargetChatId = activeChatIdRef.current;
      const res = await uploadDocument(targetFile, 120000);
      persistActiveJob(res.job_id, targetFile.name, currentTargetChatId);
      pollJob(res.job_id, currentTargetChatId, remainingFiles);
    } catch (err: any) {

      clearPersistedJob();
      console.error("🚨 [UploadModal:startSingleUpload] Error al subir archivo:", {
        fileName: targetFile.name,
        fileSize: targetFile.size,
        error: err,
      });
      setError(
        err?.message?.includes("límite") || err?.message?.includes("válido")
          ? err.message
          : "No se pudo subir el archivo. Intenta nuevamente."
      );
      // Continue with remaining files in queue if any
      if (remainingFiles.length > 0) {
        processNextInQueue(remainingFiles);
      } else {
        setUploading(false);

        setJob(null);
      }
    }
  };
  // Purpose: handleFilesSelected.
  // Inputs: files: File[].
  // Output: Value specified by the signature or operation effect.
  const handleFilesSelected = (files: File[]) => {
    if (files.length === 0) return;
    const [first, ...rest] = files;
    setFileQueue(rest);
    startSingleUpload(first, rest);
  };
  const pollJob = (
    jobId: string,
    targetChatId?: string,
    remainingFiles: File[] = []
  ) => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    let consecutiveErrors = 0;
    // Purpose: checkStatus.
    // Inputs: None.
    // Output: Value specified by the signature or operation effect.

    const checkStatus = async () => {
      try {
        const currentJob = await getJobStatus(jobId);
        consecutiveErrors = 0;
        setJob(currentJob);
        if (currentJob.status === "COMPLETED") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }

          clearPersistedJob();
          const createdAt =
            (currentJob as any).created_at || new Date().toISOString();
          onDocumentIndexedRef.current(
            currentJob.document_id,
            currentJob.filename,
            createdAt,
            targetChatId || activeChatIdRef.current
          );
          // Process next file in queue if any

          if (remainingFiles.length > 0) {
            processNextInQueue(remainingFiles);

          } else {
            setUploading(false);
          }
        } else if (currentJob.status === "FAILED") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          clearPersistedJob();

          console.error("🚨 [UploadModal:pollJob] Trabajo de ingesta falló en el backend:", {
            jobId,
            error: currentJob.error,
            message: currentJob.message,
          });
          setError("No se pudo completar el procesamiento del archivo. Intenta nuevamente.");
          if (remainingFiles.length > 0) {
            processNextInQueue(remainingFiles);
          } else {
            setUploading(false);
          }
        } else if (currentJob.status === "CANCELLED") {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;

          }
          clearPersistedJob();
          setUploading(false);
          setJob(null);
          setFileQueue([]);
        }
      } catch (err: any) {
        const errMsg = String(err?.message || "");
        if (errMsg.includes("404") || errMsg.includes("no encontrado") || errMsg.includes("not found")) {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          clearPersistedJob();
          setUploading(false);
          setJob(null);
          return;
        }
        consecutiveErrors += 1;
        // In Render free tier, server can take ~50s to spin up; tolerate up to 50 attempts (~60s)
        if (consecutiveErrors < 50) {
          setJob((prev) =>
            prev
              ? {
                  ...prev,
                  message: "El procesamiento está tardando más de lo esperado. Estamos intentando continuar...",
                }
              : prev
          );
        } else {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          setUploading(false);
          console.error("🚨 [UploadModal:pollJob] Error consultando el progreso del trabajo tras múltiples reintentos:", {
            jobId,
            error: err,
          });
          setError("No se pudo confirmar el estado del archivo. Intenta nuevamente en unos segundos.");
        }
      }
    };
    // Execute immediate check then start interval
    checkStatus();
    pollIntervalRef.current = setInterval(checkStatus, 1200);

  };
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-lg">
      <div className="flex items-center space-x-3 mb-4">
        <div className="p-2 bg-blue-600/20 text-blue-400 rounded-lg">
          <UploadCloud className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-semibold text-slate-100 text-sm">Carga de Documentos PDF</h3>
          <p className="text-xs text-slate-400">
            {activeChatTitle
              ? `Se asociará automáticamente a "${activeChatTitle}"`
              : "Extracción multimodal de texto, tablas y diagramas"}
          </p>
        </div>
      </div>
      <div className="space-y-4">
        <FileDropzone
          uploading={uploading}
          onFilesSelected={handleFilesSelected}
          onError={(msg) => {
            setError(msg);
            setTimeout(() => setError(null), 5000);
          }}
        />
        {job && (

          <IngestionProgressCard
            job={job}
            queueCount={fileQueue.length}
            uploading={uploading}
            isCancelling={isCancelling}

            onCancel={handleCancelUpload}
            onDismiss={() => setJob(null)}
          />
        )}
        {error && (
          <div className="flex items-center justify-between text-rose-300 text-xs bg-rose-500/10 border border-rose-500/20 p-2.5 rounded-lg animate-in fade-in duration-150">
            <div className="flex items-center space-x-2 mr-2">
              <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              onClick={() => setError(null)}
              className="text-rose-400 hover:text-rose-200 p-0.5 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>

          </div>
        )}
      </div>
    </div>
  );
}
