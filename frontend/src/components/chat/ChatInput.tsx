"use client";

import React, { useState } from "react";
import { Send, Loader2 } from "lucide-react";
// Data contract ChatInputProps.

// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
interface ChatInputProps {
  chatTitle: string;
  hasAttachedDocs: boolean;
  loading: boolean;
  onSendMessage: (query: string) => void;
}
/**
 * ChatInput function.
 *
 * @param {
  chatTitle - unknown.
 * @param hasAttachedDocs - unknown.
 * @param loading - unknown.
 * @param onSendMessage - unknown.
 * @param } - ChatInputProps.
 * @returns void.
 */
export default function ChatInput({
  chatTitle,

  hasAttachedDocs,
  loading,
  onSendMessage,
}: ChatInputProps) {
  const [input, setInput] = useState("");
  // Purpose: handleSubmit.
  // Inputs: e: React.FormEvent.
  // Output: Value specified by the signature or operation effect.

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
      className="p-2.5 sm:p-4 border-t border-slate-800 bg-slate-900/90 flex items-center space-x-2 sm:space-x-3 shrink-0"

    >
      <input
        type="text"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={
          !hasAttachedDocs
            ? "🔒 Chat bloqueado: Asocia un PDF..."
            : `Pregunta sobre ${chatTitle}...`
        }
        disabled={!hasAttachedDocs || loading}
        className="flex-1 bg-slate-950 border border-slate-700 disabled:opacity-40 disabled:cursor-not-allowed focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 rounded-xl px-3.5 sm:px-4 py-2 sm:py-2.5 text-base sm:text-sm text-slate-100 placeholder-slate-500 outline-none transition"
      />
      <button
        type="submit"
        disabled={!hasAttachedDocs || loading || !input.trim()}
        className="bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 sm:px-5 py-2.5 min-h-[44px] min-w-[44px] rounded-xl transition flex items-center justify-center font-medium shadow-md shadow-indigo-600/20 cursor-pointer shrink-0"
        aria-label="Enviar mensaje"
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
