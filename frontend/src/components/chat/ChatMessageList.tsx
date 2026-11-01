"use client";

import React, { useRef, useEffect } from "react";
import { Bot, Sparkles, Loader2 } from "lucide-react";
import { Message } from "@/types/chat";
import ChatMessageItem from "./ChatMessageItem";
// Data contract ChatMessageListProps.

// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
interface ChatMessageListProps {
  messages: Message[];
  loading: boolean;
}
/**
 * ChatMessageList function.
 *
 * @param { messages - unknown.
 * @param loading } - ChatMessageListProps.
 * @returns void.
 */
export default function ChatMessageList({ messages, loading }: ChatMessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex-1 overflow-y-auto p-3 sm:p-6 space-y-3.5 sm:space-y-5">
      {messages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-center p-4 sm:p-8 text-slate-500">

          <div className="p-3 sm:p-4 bg-slate-900 border border-slate-800 rounded-2xl mb-3 sm:mb-4 text-indigo-400">
            <Sparkles className="w-6 h-6 sm:w-8 sm:h-8" />
          </div>
          <h3 className="text-slate-300 font-semibold mb-1 text-sm sm:text-base">
            Espacio de Consulta Técnica
          </h3>
          <p className="text-xs max-w-sm text-slate-400">
            Formula preguntas técnicas basadas exclusivamente en la documentación indexada.
          </p>
        </div>
      ) : (
        messages.map((msg) => <ChatMessageItem key={msg.id} message={msg} />)
      )}
      {loading && (
        <div className="flex items-center space-x-2.5 sm:space-x-3 text-slate-400 text-xs animate-in fade-in duration-150">
          <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
            <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </div>

          <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl rounded-tl-none px-3.5 sm:px-4 py-2.5 sm:py-3 flex items-center space-x-2.5 shadow-sm">
            <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin text-indigo-400 shrink-0" />
            <span className="text-slate-300 text-xs">
              Consultando documentos técnicos y diagramas...
            </span>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}
