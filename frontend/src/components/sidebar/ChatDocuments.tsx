"use client";

import React from "react";
import { Layers, Link as LinkIcon, X, Plus, Clock, FileText, BookOpen, Trash2 } from "lucide-react";
import { IndexedDoc } from "@/types/chat";
import { formatProcessedDate } from "@/lib/formatters";

// Data contract ChatDocumentsProps.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
interface ChatDocumentsProps {
  activeChatTitle: string;
  activeChatId: string;
  activeChatDocs: IndexedDoc[];
  otherAvailableDocs: IndexedDoc[];
  showAttachMenu: boolean;
  onToggleAttachMenu: () => void;
  onAttachDoc: (chatId: string, docId: string) => void;
  onDetachDoc: (chatId: string, docId: string) => void;
  onDeleteDoc: (docId: string, docName: string) => void;
}

export default function ChatDocuments({
  activeChatTitle,
  activeChatId,
  activeChatDocs,
  otherAvailableDocs,
  showAttachMenu,
  onToggleAttachMenu,
  onAttachDoc,
  onDetachDoc,
  onDeleteDoc,
}: ChatDocumentsProps) {
  return (
    <div className="flex-1 bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col overflow-hidden relative">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
          <Layers className="w-3.5 h-3.5 text-indigo-400" />
          <span>Documentos del Chat ({activeChatDocs.length})</span>
        </span>

        {otherAvailableDocs.length > 0 && (
          <button
            onClick={onToggleAttachMenu}
            className="text-[11px] text-indigo-300 hover:text-indigo-200 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/30 px-2 py-0.5 rounded transition flex items-center space-x-1 cursor-pointer"
            title="Vincular otros documentos ya subidos a este chat"
          >
            <LinkIcon className="w-3 h-3" />
            <span>+ Vincular</span>
          </button>
        )}
      </div>

      {/* Menú flotante para vincular documentos existentes a este chat */}
      {showAttachMenu && otherAvailableDocs.length > 0 && (
        <div className="absolute top-12 left-4 right-4 bg-slate-900 border border-indigo-500/40 rounded-xl shadow-2xl p-3 z-30 space-y-1.5">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-800 text-xs">
            <span className="font-semibold text-slate-200 truncate pr-2">
              Vincular a &quot;{activeChatTitle}&quot;
            </span>
            <button
              onClick={onToggleAttachMenu}
              className="text-slate-400 hover:text-slate-200 cursor-pointer"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="max-h-40 overflow-y-auto space-y-1">
            {otherAvailableDocs.map((doc) => (
              <button
                key={doc.id}
                onClick={() => {
                  onAttachDoc(activeChatId, doc.id);
                  onToggleAttachMenu();
                }}
                className="w-full text-left p-2 rounded-lg text-xs bg-slate-950/80 hover:bg-indigo-600/20 border border-slate-800 hover:border-indigo-500/40 text-slate-300 flex items-center justify-between transition cursor-pointer"
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
                <Plus className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
              </button>
            ))}
          </div>
        </div>
      )}

      <p className="text-[11px] text-slate-400 mb-2">
        Documentos asociados exclusivamente a este espacio:
      </p>

      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
        {activeChatDocs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-4 text-slate-500 text-xs">
            <FileText className="w-8 h-8 mb-2 stroke-[1.5]" />
            <p>No hay documentos en este chat.</p>
            <p className="text-[11px] mt-1 text-slate-600">
              Sube un documento PDF arriba para agregarlo a este espacio.
            </p>
          </div>
        ) : (
          activeChatDocs.map((doc) => (
            <div
              key={doc.id}
              className="w-full p-2.5 rounded-lg text-xs transition border flex items-center justify-between bg-indigo-600/15 border-indigo-500/40 text-indigo-200"
            >
              <div className="flex items-center space-x-2 truncate pr-2 min-w-0">
                <BookOpen className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <div className="truncate min-w-0">
                  <span className="truncate block font-medium">{doc.name}</span>
                  {doc.createdAt && (
                    <span className="text-[10px] text-slate-400 flex items-center space-x-1 mt-0.5">
                      <Clock className="w-2.5 h-2.5 text-indigo-300 shrink-0" />
                      <span>{formatProcessedDate(doc.createdAt)}</span>
                    </span>
                  )}
                </div>
              </div>
              <div className="flex items-center space-x-1 shrink-0">
                <button
                  onClick={() => onDetachDoc(activeChatId, doc.id)}
                  title="Desvincular de este chat"
                  className="text-slate-400 hover:text-amber-400 transition p-1 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => onDeleteDoc(doc.id, doc.name)}
                  title="Eliminar permanentemente de la base de datos"
                  className="text-slate-400 hover:text-rose-400 transition p-1 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
