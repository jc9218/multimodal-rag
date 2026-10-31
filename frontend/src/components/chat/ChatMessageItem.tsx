"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User, AlertCircle } from "lucide-react";
import { Message } from "@/types/chat";
import MultimodalImagesView from "./MultimodalImagesView";
import SourcesBadgeList from "./SourcesBadgeList";

// Clase: contrato de datos ChatMessageItemProps.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
interface ChatMessageItemProps {
  message: Message;
}

export default function ChatMessageItem({ message }: ChatMessageItemProps) {
  const isUser = message.sender === "user";

  return (
    <div
      className={`flex space-x-2 sm:space-x-3.5 ${
        isUser ? "justify-end" : "justify-start"
      } animate-in fade-in duration-200`}
    >
      {!isUser && (
        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0 mt-0.5">
          <Bot className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </div>
      )}

      <div
        className={`max-w-[92%] sm:max-w-[85%] rounded-2xl px-3 sm:px-4 py-2.5 sm:py-3 text-xs sm:text-sm leading-relaxed shadow-sm ${
          isUser
            ? "bg-indigo-600 text-white rounded-tr-none font-normal"
            : message.isError
            ? "bg-rose-950/40 border border-rose-800/60 text-rose-200 rounded-tl-none"
            : "bg-slate-800/90 border border-slate-700/60 text-slate-200 rounded-tl-none"
        }`}
      >
        {isUser ? (
          <div className="whitespace-pre-wrap break-words">{message.text}</div>
        ) : (
          <div className="space-y-2 overflow-hidden">
            {message.isError && (
              <div className="flex items-center space-x-1.5 text-rose-400 font-medium text-xs mb-1">
                <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                <span>Aviso del Asistente Técnico</span>
              </div>
            )}

            <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-slate-950 prose-pre:border prose-pre:border-slate-800 prose-table:text-xs overflow-x-auto break-words">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.text}
              </ReactMarkdown>
            </div>

            {/* Multimodal Schematics / Associated Technical Images */}
            {message.responseMeta?.images && message.responseMeta.images.length > 0 && (
              <MultimodalImagesView images={message.responseMeta.images} />
            )}

            {/* Sources Metadata Badges (Grouped & Deduplicated by document) */}
            {message.responseMeta?.sources && message.responseMeta.sources.length > 0 && (
              <SourcesBadgeList sources={message.responseMeta.sources} />
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-0.5">
          <User className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
        </div>
      )}
    </div>
  );
}
