"use client";

import React from "react";
import {
  Sparkles,
  X,
  Compass,
  Layers,
  ShieldCheck,
  Eye,
  Brain,
  Zap,
  CheckCircle2,
} from "lucide-react";

// Clase: contrato de datos SkillsModalProps.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
interface SkillsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

// Clase: contrato de datos SkillItem.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
interface SkillItem {
  icon: React.ReactNode;
  name: string;
  category: string;
  description: string;
  algorithm: string;
  badge: string;
}

const SKILLS_LIST: SkillItem[] = [
  {
    icon: <Layers className="w-5 h-5 text-indigo-400" />,
    name: "Búsqueda Híbrida RRF (Dense + Sparse)",
    category: "Recuperación de Información",
    description:
      "Combina la similitud semántica de embeddings vectoriales de 768 dimensiones en Qdrant con coincidencia léxica exacta por palabras clave mediante BM25Okapi.",
    algorithm: "RRF(d) = 1/(60 + rank_dense) + 1/(60 + rank_sparse)",
    badge: "Activo en Tiempo Real",
  },
  {
    icon: <Compass className="w-5 h-5 text-blue-400" />,
    name: "Mapeo Espacial Multimodal",
    category: "Procesamiento de Documentos",
    description:
      "Extrae coordenadas geométricas exactas (Bounding Boxes [x0, y0, x1, y1]) tanto de bloques de texto como de esquemas visuales, vinculándolos mediante cálculo euclidiano.",
    algorithm: "D(T, I) = sqrt((Cx_T - Cx_I)² + (Cy_T - Cy_I)²)",
    badge: "PyMuPDF Espacial",
  },
  {
    icon: <ShieldCheck className="w-5 h-5 text-emerald-400" />,
    name: "Generación Defensiva Anti-Alucinaciones",
    category: "Inferencia LLM",
    description:
      "Garantiza respuestas deterministas a temperatura 0.0 basadas estrictamente en la evidencia documental. Si la información no existe, declara insuficiencia explícitamente.",
    algorithm: "Zero-Shot Defensive Prompting + Citas obligatorias de página",
    badge: "Temperatura 0.0",
  },
  {
    icon: <Eye className="w-5 h-5 text-amber-400" />,
    name: "OCR Automático & Capturas de Página",
    category: "Visión y Reconocimiento",
    description:
      "Detecta si el documento PDF es escaneado (< 25 caracteres nativos) y activa automáticamente Tesseract OCR (spa+eng) con captura gráfica de la página completa.",
    algorithm: "Tesseract OCR Fallback + fitz.Pixmap Snapshot",
    badge: "Detección Automática",
  },
  {
    icon: <Brain className="w-5 h-5 text-purple-400" />,
    name: "Memoria Conversacional y Anclaje Contextual",
    category: "Gestión de Diálogo",
    description:
      "Mantiene el hilo de conversación en preguntas multi-turno dentro de cada espacio de chat, resolviendo referencias y pronombres sin mezclar contextos de otros documentos.",
    algorithm: "Contextual Query Expansion + Sliding Window (6 turnos)",
    badge: "Aislamiento por Chat",
  },
  {
    icon: <Zap className="w-5 h-5 text-cyan-400" />,
    name: "Ingesta Asíncrona & Purga en Cascada",
    category: "Arquitectura & Resiliencia",
    description:
      "Procesa documentos pesados en segundo plano con polling reactivo de job_id. Soporta borrado atómico en cascada de vectores en Qdrant, índice BM25 y archivos físicos en disco.",
    algorithm: "Background Worker + At-Least-Once Purge Pipeline",
    badge: "No Bloqueante",
  },
];

export default function SkillsModal({ isOpen, onClose }: SkillsModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-3xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[88vh]">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/90">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-indigo-500/10 text-indigo-400 rounded-xl border border-indigo-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h2 className="font-bold text-base text-slate-100 flex items-center space-x-2">
                <span>Skills & Capacidades del Motor RAG</span>
                <span className="text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-full font-mono">
                  6 Habilidades Activas
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Módulos de arquitectura limpia, recuperación híbrida e inferencia multimodal
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-lg transition"
            title="Cerrar modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Content - Skills Cards */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3.5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {SKILLS_LIST.map((skill, idx) => (
              <div
                key={idx}
                className="bg-slate-950/60 border border-slate-800/80 hover:border-indigo-500/40 rounded-xl p-4 transition group flex flex-col justify-between space-y-2.5"
              >
                <div>
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center space-x-2.5">
                      <div className="p-2 bg-slate-900 rounded-lg border border-slate-800 group-hover:border-indigo-500/30 transition">
                        {skill.icon}
                      </div>
                      <div>
                        <span className="text-[10px] uppercase font-semibold tracking-wider text-slate-500">
                          {skill.category}
                        </span>
                        <h3 className="text-xs font-semibold text-slate-200 leading-tight">
                          {skill.name}
                        </h3>
                      </div>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed">
                    {skill.description}
                  </p>
                </div>

                <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between text-[11px]">
                  <code className="text-[10px] text-indigo-300/80 font-mono truncate max-w-[200px]">
                    {skill.algorithm}
                  </code>
                  <span className="inline-flex items-center space-x-1 text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-md font-medium shrink-0">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>{skill.badge}</span>
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-950/40 flex items-center justify-between text-xs text-slate-400">
          <span>Diseñado bajo principios de Arquitectura Limpia e Inversión de Dependencias (DIP)</span>
          <button
            onClick={onClose}
            className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-4 py-1.5 rounded-lg transition"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
}
