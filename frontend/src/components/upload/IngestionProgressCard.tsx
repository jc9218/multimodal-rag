"use client";

import React from "react";
import { CheckCircle2, AlertCircle, Loader2, Check, Trash2, X, Clock } from "lucide-react";
import { IngestionJob } from "@/lib/api";

const STATUS_LABELS: Record<string, string> = {
  PENDING: "En espera",
  EXTRACTING: "Extrayendo contenido",
  INDEXING: "Procesando información",
  WAITING_QUOTA: "Pausado por cuota de IA (en espera)",
  COMPLETED: "Completado",
  FAILED: "Error en proceso",
  CANCELLED: "Cancelado",
};

interface IngestionProgressCardProps {
  job: IngestionJob;
  queueCount?: number;
  uploading: boolean;
  isCancelling: boolean;
  onCancel: () => void;
  onDismiss: () => void;
}

export default function IngestionProgressCard({
  job,
  queueCount = 0,
  uploading,
  isCancelling,
  onCancel,
  onDismiss,
}: IngestionProgressCardProps) {
  const isCompleted = job.status === "COMPLETED";
  const isFailed = job.status === "FAILED";
  const isWaitingQuota = job.status === "WAITING_QUOTA";

  return (
    <div
      className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-2.5 shadow-md"
      role="status"
      aria-live="polite"
      aria-atomic="true"
    >
      <div className="flex items-center justify-between text-xs">
        <span
          className="font-medium text-slate-200 truncate max-w-[200px]"
          title={job.filename}
        >
          {job.filename}
        </span>
        <button
          onClick={onDismiss}
          className="text-slate-400 hover:text-slate-200 cursor-pointer p-0.5"
          title="Ocultar"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {queueCount > 0 && (
        <div className="flex items-center space-x-1 text-[11px] text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 px-2 py-0.5 rounded-md">
          <Clock className="w-3 h-3 shrink-0" />
          <span>En cola: {queueCount} archivo{queueCount !== 1 ? "s" : ""} restante{queueCount !== 1 ? "s" : ""}</span>
        </div>
      )}

      {/* Status Badge & Percentage */}
      <div className="flex items-center justify-between text-xs">
        <span className="flex items-center space-x-1.5">
          {uploading && !isCompleted && !isFailed && (
            <Loader2 className="w-3 h-3 text-indigo-400 animate-spin shrink-0" />
          )}
          <span
            className={`font-medium ${
              isCompleted
                ? "text-emerald-400"
                : isFailed
                ? "text-rose-400"
                : isWaitingQuota
                ? "text-amber-400"
                : "text-indigo-400"
            }`}
          >
            {STATUS_LABELS[job.status] || job.status}
          </span>
        </span>
        <span className="text-slate-400 font-mono font-medium">
          {Math.round(job.progress * 100)}%
        </span>
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${
            isCompleted
              ? "bg-emerald-500"
              : isFailed
              ? "bg-rose-500"
              : isWaitingQuota
              ? "bg-amber-400 animate-pulse"
              : "bg-indigo-500"
          }`}
          style={{ width: `${Math.max(5, Math.round(job.progress * 100))}%` }}
        />
      </div>

      <p className="text-[11px] text-slate-300 leading-snug break-words">
        {job.message}
      </p>

      {/* Cancel and Delete Button (Available during active processing or quota wait) */}
      {uploading && (job.status === "PENDING" || job.status === "EXTRACTING" || job.status === "INDEXING" || isWaitingQuota) && (
        <button
          type="button"
          onClick={onCancel}
          disabled={isCancelling}
          className="w-full mt-2 inline-flex items-center justify-center space-x-1.5 py-1.5 px-3 rounded-lg text-[11px] font-medium text-rose-300 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 transition disabled:opacity-50 cursor-pointer"
          title="Detiene el procesamiento y elimina el archivo y sus datos asociados"
        >
          {isCancelling ? (
            <>
              <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0 text-rose-400" />
              <span>Deteniendo y eliminando archivo...</span>
            </>
          ) : (
            <>
              <Trash2 className="w-3.5 h-3.5 shrink-0 text-rose-400" />
              <span>Detener procesamiento y eliminar</span>
            </>
          )}
        </button>
      )}

      {isCompleted && (
        <div className="flex items-center justify-between pt-2 border-t border-slate-800/80">
          <div className="flex items-center space-x-1.5 text-emerald-400 text-xs">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Documento listo para consultas</span>
          </div>
          <button
            onClick={onDismiss}
            className="inline-flex items-center space-x-1 bg-emerald-600/30 hover:bg-emerald-600/60 border border-emerald-500/40 text-emerald-200 text-[11px] font-medium px-2.5 py-1 rounded-md transition shadow-sm cursor-pointer"
            title="Confirmar y ocultar mensaje"
          >
            <Check className="w-3.5 h-3.5" />
            <span>Listo</span>
          </button>
        </div>
      )}
    </div>
  );
}
