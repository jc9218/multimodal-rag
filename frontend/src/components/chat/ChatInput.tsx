"use client";

import React, { useState } from "react";
import { Send, Loader2 } from "lucide-react";

// Clase: contrato de datos ChatInputProps.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
interface ChatInputProps {
  chatTitle: string;
  hasAttachedDocs: boolean;
  loading: boolean;
  onSendMessage: (query: string) => void;
}

export default function ChatInput({
  chatTitle,
  hasAttachedDocs,
  loading,
  onSendMessage,
}: ChatInputProps) {
  const [input, setInput] = useState("");

  // Objetivo: handleSubmit.
  // Entradas: e: React.FormEvent.
  // Salida: valor indicado por la firma o efecto de la operación.
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || loading || !hasAttachedDocs) return;
    setInput("");
    onSendMessage(trimmed);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-4 border-t border-slate-800 bg-slate-900/90 flex space-x-3 shrink-0"
    >
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={
          !hasAttachedDocs
            ? "🔒 Chat bloqueado: Sube o asocia al menos un documento PDF para comenzar..."
            : `Pregunta sobre ${chatTitle} (se mantiene el contexto del chat)...`
        }
        disabled={!hasAttachedDocs || loading}
        className="flex-1 bg-slate-950 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 outline-none transition"
      />
      <button
        type="submit"
        disabled={!hasAttachedDocs || loading || !input.trim()}
        className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-5 py-2.5 rounded-xl transition flex items-center justify-center font-medium shadow-md shadow-indigo-600/20 cursor-pointer"
      >
        {loading ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Send className="w-4 h-4" />
        )}
      </button>
    </form>
  );
}
