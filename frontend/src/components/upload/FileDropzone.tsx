"use client";

import React, { useState } from "react";
import { UploadCloud, Files } from "lucide-react";

const MAX_UPLOAD_SIZE_MB = Number(
  process.env.NEXT_PUBLIC_MAX_UPLOAD_SIZE_MB || "10"
);
const MAX_UPLOAD_SIZE_BYTES = MAX_UPLOAD_SIZE_MB * 1024 * 1024;

// Clase: contrato de datos FileDropzoneProps.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
interface FileDropzoneProps {
  uploading: boolean;
  onFilesSelected: (files: File[]) => void;
  onError: (msg: string) => void;
}

export default function FileDropzone({
  uploading,
  onFilesSelected,
  onError,
}: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);

  // Objetivo: validateAndFilterFiles.
  // Entradas: fileList: FileList | null.
  // Salida: valor indicado por la firma o efecto de la operación.
  const validateAndFilterFiles = (fileList: FileList | null): File[] => {
    if (!fileList || fileList.length === 0) return [];
    const files = Array.from(fileList);
    const validPdfs: File[] = [];
    const invalidNames: string[] = [];
    const oversizedNames: string[] = [];

    for (const f of files) {
      if (!f.name.toLowerCase().endsWith(".pdf")) {
        invalidNames.push(f.name);
      } else if (f.size > MAX_UPLOAD_SIZE_BYTES) {
        oversizedNames.push(f.name);
      } else {
        validPdfs.push(f);
      }
    }

    if (invalidNames.length > 0) {
      onError(`Solo se admiten archivos PDF técnicos. Ignorados: ${invalidNames.join(", ")}`);
    }
    if (oversizedNames.length > 0) {
      onError(
        `El tamaño máximo por PDF es ${MAX_UPLOAD_SIZE_MB} MB. Ignorados: ${oversizedNames.join(", ")}`
      );
    }

    return validPdfs;
  };

  // Objetivo: handleFileChange.
  // Entradas: e: React.ChangeEvent<HTMLInputElement>.
  // Salida: valor indicado por la firma o efecto de la operación.
  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const valid = validateAndFilterFiles(e.target.files);
    if (valid.length > 0) {
      onFilesSelected(valid);
    }
    e.target.value = "";
  };

  // Objetivo: handleDragOver.
  // Entradas: e: React.DragEvent<HTMLLabelElement>.
  // Salida: valor indicado por la firma o efecto de la operación.
  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    if (!uploading) setIsDragging(true);
  };

  // Objetivo: handleDragLeave.
  // Entradas: e: React.DragEvent<HTMLLabelElement>.
  // Salida: valor indicado por la firma o efecto de la operación.
  const handleDragLeave = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  // Objetivo: handleDrop.
  // Entradas: e: React.DragEvent<HTMLLabelElement>.
  // Salida: valor indicado por la firma o efecto de la operación.
  const handleDrop = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (uploading) return;
    const valid = validateAndFilterFiles(e.dataTransfer.files);
    if (valid.length > 0) {
      onFilesSelected(valid);
    }
  };

  return (
    <label
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`border-2 border-dashed rounded-xl p-5 flex flex-col items-center justify-center text-center cursor-pointer transition ${
        uploading
          ? "border-slate-800 bg-slate-950/40 opacity-60 cursor-not-allowed"
          : isDragging
          ? "border-indigo-500 bg-indigo-500/10 scale-[0.99]"
          : "border-slate-700/80 hover:border-slate-600 bg-slate-950/60"
      }`}
    >
      <div className="flex items-center space-x-1.5 text-slate-400 mb-2">
        <Files className="w-5 h-5 text-indigo-400" />
      </div>
      <p className="text-xs font-semibold text-slate-200">
        Toca o arrastra uno o varios PDF aquí
      </p>
      <p className="text-[11px] text-slate-400 mt-1">
        PDFs de hasta {MAX_UPLOAD_SIZE_MB} MB · selección múltiple
      </p>
      <input
        type="file"
        accept=".pdf"
        multiple
        className="hidden"
        onChange={handleFileChange}
        disabled={uploading}
      />
    </label>
  );
}
