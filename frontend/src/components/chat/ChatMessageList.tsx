"use client";

import React, { useRef, useEffect } from "react";
import { Bot, Sparkles, Loader2 } from "lucide-react";
import { Message } from "@/types/chat";
import ChatMessageItem from "./ChatMessageItem";

interface ChatMessageListProps {
  messages: Message[];
  loading: boolean;
}

export default function ChatMessageList({ messages, loading }: ChatMessageListProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-5">
      {messages.length === 0 ? (
        <div className="h-full flex flex-col items-center justify-center text-center p-8 text-slate-500">
          <div className="p-4 bg-slate-900 border border-slate-800 rounded-2xl mb-4 text-indigo-400">
            <Sparkles className="w-8 h-8" />
          </div>
          <h3 className="text-slate-300 font-semibold mb-1">
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
        <div className="flex items-center space-x-3 text-slate-400 text-xs animate-in fade-in duration-150">
          <div className="w-8 h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
            <Bot className="w-4 h-4" />
          </div>
          <div className="bg-slate-800/80 border border-slate-700/60 rounded-2xl rounded-tl-none px-4 py-3 flex items-center space-x-2.5 shadow-sm">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-400 shrink-0" />
            <span className="text-slate-300">
              Consultando documentos técnicos y diagramas...
            </span>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
}
