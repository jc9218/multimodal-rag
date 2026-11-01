"use client";

import React from "react";
import { Cpu, Sparkles } from "lucide-react";
// Data contract: NavbarProps.

// Inputs: onOpenSkills callback, optional onToggleSidebar for responsive mobile drawer.
// Output: Header navbar component with responsive branding and controls.
interface NavbarProps {
  onOpenSkills: () => void;
}
/**
 * Navbar function.
 *
 * @param { onOpenSkills } - NavbarProps.
 * @returns void.
 */
export default function Navbar({ onOpenSkills }: NavbarProps) {
  return (

    <header className="border-b border-slate-800 bg-slate-900/60 px-3 sm:px-6 py-2.5 sm:py-3.5 flex items-center justify-between backdrop-blur shrink-0">
      <div className="flex items-center space-x-2 sm:space-x-3">
        <div className="p-1.5 sm:p-2 bg-gradient-to-tr from-indigo-600 to-blue-500 rounded-xl shadow-md text-white shrink-0">
          <Cpu className="w-4 h-4 sm:w-5 sm:h-5" />
        </div>
        <div className="min-w-0">
          <h1 className="font-bold text-sm sm:text-base tracking-tight text-white flex items-center space-x-1.5 sm:space-x-2 truncate">
            <span className="truncate">Multimodal RAG</span>
            <span className="hidden sm:inline-block text-[10px] bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 px-2 py-0.5 rounded-full font-mono shrink-0">
              Clean Arch • Multi-Chat
            </span>
          </h1>
          <p className="hidden md:block text-xs text-slate-400 truncate">
            Espacios de chat con contexto de documentos • Búsqueda Híbrida RRF
          </p>
        </div>
      </div>
      <div className="flex items-center space-x-2 sm:space-x-3 text-xs shrink-0">
        <button
          onClick={onOpenSkills}

          className="flex items-center space-x-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 px-2.5 sm:px-3 py-1.5 rounded-lg transition font-medium shadow-sm cursor-pointer"
          title="Ver las habilidades y capacidades técnicas del motor RAG"
        >
          <Sparkles className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
          <span className="hidden sm:inline">Skills del Asistente</span>
          <span className="sm:hidden text-[11px]">Skills</span>
        </button>
        <div className="flex items-center space-x-1.5 sm:space-x-2 bg-slate-900 border border-slate-800 px-2.5 sm:px-3 py-1.5 rounded-lg text-slate-300">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
          <span className="hidden sm:inline">API FastAPI: Conectada</span>
          <span className="sm:hidden text-[11px]">En línea</span>

        </div>
      </div>
    </header>
  );
}
