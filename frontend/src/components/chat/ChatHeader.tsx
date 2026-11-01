"use client";

import React, { useState, useEffect } from "react";
import { Sparkles, Edit2, Check, X, FileText, Clock, Trash2, Lock, Menu } from "lucide-react";
import { ChatSession, IndexedDoc } from "@/types/chat";
import { formatProcessedDate } from "@/lib/formatters";
// Data contract: ChatHeaderProps.

// Inputs: active chat session, indexed documents, title update and document toggle callbacks, optional sidebar toggle.
// Output: Responsive header with title editing, document attachments popover, and status indicators.
interface ChatHeaderProps {
  chat: ChatSession;
  allIndexedDocs: IndexedDoc[];
  onRenameChat: (chatId: string, newTitle: string) => void;
  onToggleDoc: (chatId: string, docId: string) => void;
  onClearChat: (chatId: string) => void;
  onToggleSidebar?: () => void;
}
/**
 * ChatHeader function.
 *
 * @param {
  chat - unknown.
 * @param allIndexedDocs - unknown.
 * @param onRenameChat - unknown.
 * @param onToggleDoc - unknown.
 * @param onClearChat - unknown.
 * @param onToggleSidebar - unknown.
 * @param } - ChatHeaderProps.
 * @returns void.
 */
export default function ChatHeader({
  chat,

  allIndexedDocs,
  onRenameChat,
  onToggleDoc,
  onClearChat,
  onToggleSidebar,
}: ChatHeaderProps) {
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [titleInput, setTitleInput] = useState(chat.title);
  const [showDocSelector, setShowDocSelector] = useState(false);
  useEffect(() => {
    setTitleInput(chat.title);
    setIsEditingTitle(false);

  }, [chat.id, chat.title]);
  const handleSaveTitle = () => {
    const trimmed = titleInput.trim();
    if (trimmed && trimmed !== chat.title) {
      onRenameChat(chat.id, trimmed);

    }
    setIsEditingTitle(false);
  };
  const hasAttachedDocs = chat.documentIds && chat.documentIds.length > 0;
  const attachedDocNames = allIndexedDocs.filter((d) =>
    chat.documentIds.includes(d.id)
  );
  return (

    <div className="px-3 sm:px-6 py-2.5 sm:py-3.5 border-b border-slate-800 bg-slate-900/90 flex items-center justify-between gap-2 sm:gap-3 shrink-0">
      <div className="flex items-center space-x-2 sm:space-x-3 min-w-0">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}

            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition lg:hidden cursor-pointer shrink-0"
            title="Abrir panel de chats y documentos"
            aria-label="Abrir panel de navegación"
          >
            <Menu className="w-4 h-4 text-indigo-400" />
          </button>
        )}
        <div className="p-1.5 sm:p-2 bg-indigo-500/10 text-indigo-400 rounded-lg border border-indigo-500/20 shrink-0">
          <Sparkles className="w-4 h-4 sm:w-5 sm:h-5" />
        </div>
        <div className="min-w-0">
          {isEditingTitle ? (
            <div className="flex items-center space-x-1.5">
              <input

                type="text"
                value={titleInput}
                onChange={(e) => setTitleInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSaveTitle()}
                autoFocus
                className="bg-slate-950 border border-indigo-500 text-xs sm:text-sm font-semibold text-white px-2 py-0.5 rounded outline-none max-w-[140px] sm:max-w-xs"
              />
              <button
                onClick={handleSaveTitle}
                className="p-1 text-emerald-400 hover:text-emerald-300 cursor-pointer"
                title="Guardar nombre"
              >
                <Check className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </button>
              <button
                onClick={() => {
                  setTitleInput(chat.title);
                  setIsEditingTitle(false);
                }}
                className="p-1 text-slate-400 hover:text-rose-400 cursor-pointer"
                title="Cancelar"
              >
                <X className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center space-x-1.5 sm:space-x-2 min-w-0">
              <h2 className="font-semibold text-slate-100 text-xs sm:text-sm truncate max-w-[130px] xs:max-w-[180px] sm:max-w-xs md:max-w-md">
                {chat.title}
              </h2>
              <button
                onClick={() => setIsEditingTitle(true)}
                className="text-slate-500 hover:text-slate-300 transition cursor-pointer shrink-0"
                title="Renombrar este chat"
              >
                <Edit2 className="w-3 h-3 sm:w-3.5 sm:h-3.5" />
              </button>
            </div>
          )}
          <p className="text-[10px] sm:text-xs text-slate-400 truncate">
            {hasAttachedDocs
              ? `Contexto: ${attachedDocNames.length} doc${
                  attachedDocNames.length > 1 ? "s" : ""
                } vinculado${attachedDocNames.length > 1 ? "s" : ""}`
              : "Sin documentos vinculados"}
          </p>
        </div>
      </div>
      {/* Right Action Bar */}
      <div className="flex items-center space-x-1.5 sm:space-x-2.5 shrink-0">
        {/* Document Management Button */}
        <div className="relative">
          <button
            onClick={() => setShowDocSelector(!showDocSelector)}
            className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 px-2 sm:px-2.5 py-1.5 rounded-lg transition flex items-center space-x-1 sm:space-x-1.5 cursor-pointer"
            title="Gestionar documentos asociados a este chat"

          >
            <FileText className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
            <span className="hidden sm:inline">Documentos</span>
            <span>({chat.documentIds.length})</span>
          </button>
          {/* Doc Selector Popover */}
          {showDocSelector && (
            <div className="absolute right-0 mt-2 w-[calc(100vw-2rem)] sm:w-72 max-w-sm bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-3 z-50">
              <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-2">
                <span className="text-xs font-semibold text-slate-200">
                  Documentos para este chat
                </span>
                <button
                  onClick={() => setShowDocSelector(false)}

                  className="text-slate-400 hover:text-slate-200 cursor-pointer p-1"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
              {allIndexedDocs.length === 0 ? (
                <p className="text-xs text-slate-500 py-2 text-center">
                  No hay documentos cargados en el sistema.
                </p>
              ) : (
                <div className="max-h-52 overflow-y-auto space-y-1.5">
                  {allIndexedDocs.map((doc) => {
                    const isLinked = chat.documentIds.includes(doc.id);
                    return (
                      <button
                        key={doc.id}
                        onClick={() => onToggleDoc(chat.id, doc.id)}
                        className={`w-full text-left p-2 rounded-lg text-xs flex items-center justify-between transition cursor-pointer ${
                          isLinked
                            ? "bg-indigo-600/20 border border-indigo-500/40 text-indigo-200"
                            : "bg-slate-950/60 border border-slate-800 text-slate-400 hover:border-slate-700"
                        }`}
                      >
                        <div className="truncate pr-2 min-w-0">
                          <span className="truncate block font-medium">{doc.name}</span>
                          {doc.createdAt && (
                            <span className="text-[10px] text-slate-500 flex items-center space-x-1 mt-0.5">
                              <Clock className="w-2.5 h-2.5 text-slate-600 shrink-0" />
                              <span>{formatProcessedDate(doc.createdAt)}</span>
                            </span>
                          )}
                        </div>
                        <span
                          className={`w-3.5 h-3.5 rounded flex items-center justify-center shrink-0 border ${
                            isLinked
                              ? "bg-indigo-600 border-indigo-500 text-white"
                              : "border-slate-600"
                          }`}
                        >
                          {isLinked && <Check className="w-2.5 h-2.5" />}
                        </span>
                      </button>
                    );
                  })}
                </div>
              )}
            </div>
          )}
        </div>
        {/* Clear Messages */}
        {chat.messages.length > 1 && (
          <button
            onClick={() => onClearChat(chat.id)}
            title="Limpiar mensajes de este chat"
            className="text-[11px] text-slate-400 hover:text-rose-400 bg-slate-800/80 hover:bg-rose-500/10 border border-slate-700 hover:border-rose-500/30 px-2 sm:px-2.5 py-1.5 rounded-lg transition flex items-center space-x-1 sm:space-x-1.5 cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5 shrink-0" />
            <span className="hidden sm:inline">Limpiar</span>
          </button>

        )}
        {/* Status Badge */}
        {!hasAttachedDocs ? (
          <span className="text-[10px] sm:text-[11px] bg-amber-500/10 border border-amber-500/20 text-amber-400 px-2 sm:px-2.5 py-1.5 rounded-full flex items-center space-x-1 font-medium">
            <Lock className="w-3 h-3 sm:w-3.5 sm:h-3.5 shrink-0" />
            <span className="hidden sm:inline">Sin Documentos</span>
            <span className="sm:hidden">Bloqueado</span>
          </span>
        ) : (
          <span className="text-[10px] sm:text-[11px] bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-2 sm:px-2.5 py-1.5 rounded-full flex items-center space-x-1 sm:space-x-1.5 font-medium">
            <span className="w-1.5 h-1.5 sm:w-2 sm:h-2 rounded-full bg-emerald-400 animate-pulse shrink-0"></span>
            <span className="hidden sm:inline">Contexto Activo</span>

            <span className="sm:hidden">Activo</span>
          </span>
        )}
      </div>
    </div>
  );
}
