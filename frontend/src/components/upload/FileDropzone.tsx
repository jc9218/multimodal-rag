"use client";

import React, { useState } from "react";
import { UploadCloud, Files } from "lucide-react";

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

  const validateAndFilterFiles = (fileList: FileList | null): File[] => {
    if (!fileList || fileList.length === 0) return [];
    const files = Array.from(fileList);
    const validPdfs: File[] = [];
    const invalidNames: string[] = [];

    for (const f of files) {
      if (f.name.toLowerCase().endsWith(".pdf")) {
        validPdfs.push(f);
      } else {
        invalidNames.push(f.name);
      }
    }

    if (invalidNames.length > 0) {
      onError(`Solo se admiten archivos PDF técnicos. Ignorados: ${invalidNames.join(", ")}`);
    }

    return validPdfs;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const valid = validateAndFilterFiles(e.target.files);
    if (valid.length > 0) {
      onFilesSelected(valid);
    }
    e.target.value = "";
  };

  const handleDragOver = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    if (!uploading) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLLabelElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

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
        Haz clic o arrastra uno o varios PDF aquí
      </p>
      <p className="text-[11px] text-slate-400 mt-1">
        Soporta selección múltiple de documentos técnicos
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
