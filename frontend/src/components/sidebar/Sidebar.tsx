"use client";

import React from "react";
import { ChatSession, IndexedDoc } from "@/types/chat";
import UploadModal from "../UploadModal";
import ChatList from "./ChatList";
import ChatDocuments from "./ChatDocuments";

// Clase: contrato de datos SidebarProps.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
interface SidebarProps {
  chats: ChatSession[];
  activeChat: ChatSession;
  activeChatId: string;
  activeChatDocs: IndexedDoc[];
  otherAvailableDocs: IndexedDoc[];
  showAttachMenu: boolean;
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
  onDocumentIndexed,
  onSelectChat,
  onCreateChat,
  onDeleteChat,
  onToggleAttachMenu,
  onAttachDoc,
  onDetachDoc,
  onDeleteDoc,
}: SidebarProps) {
  return (
    <aside className="w-[22rem] flex flex-col space-y-4 shrink-0 overflow-hidden">
      {/* Upload PDF Section */}
      <UploadModal
        onDocumentIndexed={onDocumentIndexed}
        activeChatTitle={activeChat ? activeChat.title : undefined}
        activeChatId={activeChat ? activeChat.id : activeChatId}
      />

      {/* Mis Chats Section */}
      <ChatList
        chats={chats}
        activeChatId={activeChatId}
        onSelectChat={onSelectChat}
        onCreateChat={onCreateChat}
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
    </aside>
  );
}
