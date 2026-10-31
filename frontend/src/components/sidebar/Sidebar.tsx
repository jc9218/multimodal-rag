"use client";

import React from "react";
import { FolderKanban, X } from "lucide-react";
import { ChatSession, IndexedDoc } from "@/types/chat";
import UploadModal from "../UploadModal";
import ChatList from "./ChatList";
import ChatDocuments from "./ChatDocuments";

// Data contract: SidebarProps.
// Inputs: sessions, documents, selection and attachment callbacks, mobile drawer state.
// Output: Dual-mode responsive component (persistent desktop sidebar + sliding mobile drawer).
interface SidebarProps {
  chats: ChatSession[];
  activeChat: ChatSession;
  activeChatId: string;
  activeChatDocs: IndexedDoc[];
  otherAvailableDocs: IndexedDoc[];
  showAttachMenu: boolean;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
  onDocumentIndexed: (
    docId: string,
    filename: string,
    createdAt?: string,
    targetChatId?: string
  ) => void;
  onSelectChat: (chatId: string) => void;
  onCreateChat: () => void;
  onDeleteChat: (chatId: string, e: React.MouseEvent) => void;
  onToggleAttachMenu: () => void;
  onAttachDoc: (chatId: string, docId: string) => void;
  onDetachDoc: (chatId: string, docId: string) => void;
  onDeleteDoc: (docId: string, docName: string) => void;
}

export default function Sidebar({
  chats,
  activeChat,
  activeChatId,
  activeChatDocs,
  otherAvailableDocs,
  showAttachMenu,
  isMobileOpen = false,
  onCloseMobile,
  onDocumentIndexed,
  onSelectChat,
  onCreateChat,
  onDeleteChat,
  onToggleAttachMenu,
  onAttachDoc,
  onDetachDoc,
  onDeleteDoc,
}: SidebarProps) {
  const handleSelectChat = (chatId: string) => {
    onSelectChat(chatId);
    onCloseMobile?.();
  };

  const handleCreateChat = () => {
    onCreateChat();
    onCloseMobile?.();
  };

  const sidebarContent = (
    <>
      {/* Upload PDF Section */}
      <UploadModal
        onDocumentIndexed={(docId, filename, createdAt, targetChatId) => {
          onDocumentIndexed(docId, filename, createdAt, targetChatId);
          onCloseMobile?.();
        }}
        activeChatTitle={activeChat ? activeChat.title : undefined}
        activeChatId={activeChat ? activeChat.id : activeChatId}
      />

      {/* Mis Chats Section */}
      <ChatList
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={handleSelectChat}
        onCreateChat={handleCreateChat}
        onDeleteChat={onDeleteChat}
      />

      {/* Documentos del Chat Activo */}
      <ChatDocuments
        activeChatTitle={activeChat ? activeChat.title : ""}
        activeChatId={activeChatId}
        activeChatDocs={activeChatDocs}
        otherAvailableDocs={otherAvailableDocs}
        showAttachMenu={showAttachMenu}
        onToggleAttachMenu={onToggleAttachMenu}
        onAttachDoc={onAttachDoc}
        onDetachDoc={onDetachDoc}
        onDeleteDoc={onDeleteDoc}
      />
    </>
  );

  return (
    <>
      {/* 1. Desktop Persistent Sidebar */}
      <aside className="hidden lg:flex w-80 xl:w-[22rem] flex-col space-y-4 shrink-0 overflow-hidden">
        {sidebarContent}
      </aside>

      {/* 2. Mobile Responsive Slide-Over Drawer */}
      <div
        className={`fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-40 transition-opacity duration-300 lg:hidden ${
          isMobileOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
        onClick={onCloseMobile}
        aria-hidden="true"
      />

      <aside
        className={`fixed inset-y-0 left-0 z-50 w-[88vw] max-w-sm bg-slate-950 border-r border-slate-800 p-4 flex flex-col shadow-2xl transition-transform duration-300 ease-in-out lg:hidden ${
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        role="dialog"
        aria-modal="true"
        aria-label="Panel de navegación de chats y documentos"
      >
        <div className="flex items-center justify-between pb-3 mb-2 border-b border-slate-800 shrink-0">
          <div className="flex items-center space-x-2">
            <div className="p-1.5 bg-indigo-600/30 text-indigo-400 rounded-lg">
              <FolderKanban className="w-4 h-4" />
            </div>
            <span className="font-semibold text-sm text-slate-100">
              Espacios y Documentos
            </span>
          </div>
          <button
            onClick={onCloseMobile}
            className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition cursor-pointer"
            aria-label="Cerrar panel de navegación"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto space-y-4 pr-1">
          {sidebarContent}
        </div>
      </aside>
    </>
  );
}
