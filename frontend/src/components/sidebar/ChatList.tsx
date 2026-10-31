"use client";

import React from "react";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { ChatSession } from "@/types/chat";

interface ChatListProps {
  chats: ChatSession[];
  activeChatId: string;
  onSelectChat: (chatId: string) => void;
  onCreateChat: () => void;
  onDeleteChat: (chatId: string, e: React.MouseEvent) => void;
}

export default function ChatList({
  chats,
  activeChatId,
  onSelectChat,
  onCreateChat,
  onDeleteChat,
}: ChatListProps) {
  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col max-h-[42%] overflow-hidden">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1.5">
          <MessageSquare className="w-3.5 h-3.5 text-indigo-400" />
          <span>Mis Chats ({chats.length})</span>
        </span>
        <button
          onClick={onCreateChat}
          className="text-[11px] bg-indigo-600/30 hover:bg-indigo-600/60 text-indigo-200 border border-indigo-500/40 px-2.5 py-1 rounded-md transition flex items-center space-x-1 font-medium cursor-pointer"
          title="Crear un nuevo espacio de chat en blanco"
        >
          <Plus className="w-3 h-3" />
          <span>Nuevo Chat</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1">
        {chats.map((c) => {
          const isActive = c.id === activeChatId;
          return (
            <div
              key={c.id}
              onClick={() => onSelectChat(c.id)}
              className={`group w-full text-left p-2.5 rounded-lg text-xs transition border flex items-center justify-between cursor-pointer ${
                isActive
                  ? "bg-indigo-600/20 border-indigo-500/40 text-indigo-200"
                  : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200"
              }`}
            >
              <div className="flex items-center space-x-2.5 min-w-0 pr-2">
                <MessageSquare
                  className={`w-3.5 h-3.5 shrink-0 ${
                    isActive ? "text-indigo-400" : "text-slate-500"
                  }`}
                />
                <div className="truncate">
                  <p className="font-medium truncate">{c.title}</p>
                  <p className="text-[10px] text-slate-500">
                    {c.documentIds.length} doc{c.documentIds.length !== 1 ? "s" : ""} •{" "}
                    {c.messages.length} msgs
                  </p>
                </div>
              </div>

              <button
                onClick={(e) => onDeleteChat(c.id, e)}
                title="Eliminar este espacio"
                className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-rose-400 p-1 rounded transition shrink-0 cursor-pointer"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
