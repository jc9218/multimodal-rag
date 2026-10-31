"use client";

import React, { useState } from "react";
import { Image as ImageIcon, Maximize2, X } from "lucide-react";
import { ExtractedImage, getFullImageUrl } from "@/lib/api";

// Clase: contrato de datos MultimodalImagesViewProps.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
interface MultimodalImagesViewProps {
  images: ExtractedImage[];
}

export default function MultimodalImagesView({ images }: MultimodalImagesViewProps) {
  const [zoomedImage, setZoomedImage] = useState<ExtractedImage | null>(null);

  if (!images || images.length === 0) return null;

  return (
    <div className="mt-4 pt-3 border-t border-slate-700/60">
      <div className="flex items-center space-x-2 text-xs font-semibold text-indigo-300 mb-2">
        <ImageIcon className="w-4 h-4 text-indigo-400" />
        <span>Diagramas Técnicos Correlacionados Espacialmente:</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {images.map((img) => (
          <div
            key={img.id}
            className="bg-slate-900 border border-slate-700 rounded-lg overflow-hidden group hover:border-indigo-500/50 transition cursor-pointer relative"
            onClick={() => setZoomedImage(img)}
          >
            <div className="p-2 bg-slate-950 flex items-center justify-between text-[11px] text-slate-400">
              <span>Página {img.page}</span>
              <div className="flex items-center space-x-1.5">
                <span className="text-[10px] bg-slate-800 px-1.5 py-0.5 rounded font-mono">
                  BBox: ({Math.round(img.bbox.x0)}, {Math.round(img.bbox.y0)})
                </span>
                <Maximize2 className="w-3 h-3 text-slate-500 group-hover:text-indigo-400 transition" />
              </div>
            </div>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={getFullImageUrl(
                img.url || `/api/v1/images/${img.document_id}/${img.filename}`
              )}
              alt={`Diagrama técnico pág ${img.page}`}
              loading="lazy"
              className="w-full h-44 object-contain bg-slate-950 p-2"
            />
          </div>
        ))}
      </div>

      {/* Lightbox / Modal de ampliación */}
      {zoomedImage && (
        <div
          className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-150"
          onClick={() => setZoomedImage(null)}
        >
          <div
            className="bg-slate-900 border border-slate-700 rounded-2xl max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl relative"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="p-3 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
              <span className="text-xs font-medium text-slate-300">
                Página {zoomedImage.page} • Diagrama ({zoomedImage.width_px}x{zoomedImage.height_px}px)
              </span>
              <button
                onClick={() => setZoomedImage(null)}
                className="text-slate-400 hover:text-white p-1 rounded-md transition cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 bg-slate-950 flex items-center justify-center overflow-auto max-h-[80vh]">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={getFullImageUrl(
                  zoomedImage.url ||
                    `/api/v1/images/${zoomedImage.document_id}/${zoomedImage.filename}`
                )}
                alt={`Diagrama técnico pág ${zoomedImage.page}`}
                className="max-w-full max-h-[75vh] object-contain"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
