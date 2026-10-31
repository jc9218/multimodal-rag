"use client";

import React from "react";
import { Cpu, Sparkles } from "lucide-react";

// Clase: contrato de datos NavbarProps.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
interface NavbarProps {
  onOpenSkills: () => void;
}

export default function Navbar({ onOpenSkills }: NavbarProps) {
  return (
    <header className="border-b border-slate-800 bg-slate-900/60 px-6 py-3.5 flex items-center justify-between backdrop-blur shrink-0">
      <div className="flex items-center space-x-3">
        <div className="p-2 bg-gradient-to-tr from-indigo-600 to-blue-500 rounded-xl shadow-md text-white">
          <Cpu className="w-5 h-5" />
        </div>
        <div>
          <h1 className="font-bold text-base tracking-tight text-white flex items-center space-x-2">
            <span>Multimodal RAG Engine</span>
            <span className="text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full font-mono">
              Clean Arch • Multi-Chat
            </span>
          </h1>
          <p className="text-xs text-slate-400">
            Espacios de chat con contexto de documentos • Búsqueda Híbrida RRF
          </p>
        </div>
      </div>

      <div className="flex items-center space-x-3 text-xs">
        <button
          onClick={onOpenSkills}
          className="flex items-center space-x-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 px-3 py-1.5 rounded-lg transition font-medium shadow-sm cursor-pointer"
          title="Ver las habilidades y capacidades técnicas del motor RAG"
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
          <span>Skills del Asistente</span>
        </button>

        <div className="flex items-center space-x-2 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
          <span>API FastAPI: Conectada</span>
        </div>
      </div>
    </header>
  );
}
