"use client";

import React, { useState } from "react";
import { queryRAG } from "@/lib/api";
import { ChatSession, IndexedDoc, Message } from "@/types/chat";
import ChatHeader from "./chat/ChatHeader";
import ChatMessageList from "./chat/ChatMessageList";
import ChatInput from "./chat/ChatInput";

// Data contract: ChatInterfaceProps.
// Inputs: active chat, indexed documents, message and chat manipulation callbacks, optional sidebar toggle.
// Output: Main chat viewport component.
interface ChatInterfaceProps {
  chat: ChatSession;
  allIndexedDocs: IndexedDoc[];
  onUpdateMessages: (chatId: string, messages: Message[]) => void;
  onRenameChat: (chatId: string, newTitle: string) => void;
  onToggleDoc: (chatId: string, docId: string) => void;
  onClearChat: (chatId: string) => void;
  onDeleteDoc?: (docId: string, docName: string) => void;
  onToggleSidebar?: () => void;
}

export default function ChatInterface({
  chat,
  allIndexedDocs,
  onUpdateMessages,
  onRenameChat,
  onToggleDoc,
  onClearChat,
  onToggleSidebar,
}: ChatInterfaceProps) {
  const [loading, setLoading] = useState(false);

  const hasAttachedDocs = Boolean(chat.documentIds && chat.documentIds.length > 0);

  // Purpose: handleSendMessage.
  // Inputs: userQuery: string.
  // Output: Value specified by the signature or operation effect.
  const handleSendMessage = async (userQuery: string) => {
    if (!hasAttachedDocs || loading) return;

    const targetChatId = chat.id;
    const userMessage: Message = {
      id: Date.now().toString(),
      sender: "user",
      text: userQuery,
    };

    const updatedWithUser = [...chat.messages, userMessage];
    onUpdateMessages(targetChatId, updatedWithUser);
    setLoading(true);
    let assistantMessage: Message | null = null;

    try {
      // Build conversational context history (last 6 turns, omitting welcome message)
      const chatHistory = updatedWithUser
        .filter((m) => m.id !== "initial-welcome")
        .slice(-6)
        .map((m) => ({
          role: m.sender,
          content: m.text,
        }));

      const result = await queryRAG(
        userQuery,
        undefined,
        chat.documentIds,
        chatHistory,
        120000 // 120s timeout allowing for Render cold start (~50s) + inference
      );

      const rawAnswer = result?.answer?.trim();
      const finalText =
        rawAnswer ||
        "No se pudo generar una respuesta detallada con los documentos actuales. Por favor intenta reformular tu pregunta.";

      assistantMessage = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        text: finalText,
        responseMeta: result,
      };
    } catch (err: any) {
      console.error(
        "🚨 [ChatInterface:handleSendMessage] Error al procesar consulta RAG:",
        {
          chatId: targetChatId,
          chatTitle: chat.title,
          documentIds: chat.documentIds,
          query: userQuery,
          error: err,
        }
      );
      const raw = err?.message || "";
      let friendlyText =
        "No fue posible procesar tu consulta técnica en este momento. Por favor, intenta de nuevo en unos momentos.";

      if (raw.includes("tardó") || raw.includes("timeout") || raw.includes("TIMEOUT")) {
        friendlyText =
          "La respuesta está tardando más de lo esperado. Por favor, intenta nuevamente en unos momentos.";
      } else if (
        raw.includes("404") ||
        raw.includes("not found") ||
        raw.includes("gemini") ||
        raw.includes("inteligencia artificial") ||
        raw.includes("LLM") ||
        raw.includes("completion")
      ) {
        friendlyText =
          "No fue posible generar la respuesta en este momento. Por favor, intenta nuevamente.";
      } else if (raw.includes("vector") || raw.includes("base de datos")) {
        friendlyText =
          "No fue posible consultar el documento en este momento. Por favor, intenta nuevamente.";
      } else if (
        raw &&
        !raw.includes("HTTP") &&
        !raw.includes("{") &&
        !raw.includes("Traceback")
      ) {
        friendlyText = "No fue posible completar la consulta. Por favor, intenta nuevamente.";
      }

      assistantMessage = {
        id: (Date.now() + 1).toString(),
        sender: "assistant",
        text: friendlyText,
        isError: true,
      };
    } finally {
      if (!assistantMessage) {
        assistantMessage = {
          id: (Date.now() + 1).toString(),
          sender: "assistant",
          text: "Hubo una pausa temporal en el procesamiento. Por favor reintenta tu pregunta.",
          isError: true,
        };
      }
      onUpdateMessages(targetChatId, [...updatedWithUser, assistantMessage]);
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden shadow-2xl">
      <ChatHeader
        chat={chat}
        allIndexedDocs={allIndexedDocs}
        onRenameChat={onRenameChat}
        onToggleDoc={onToggleDoc}
        onClearChat={onClearChat}
        onToggleSidebar={onToggleSidebar}
      />
      <ChatMessageList messages={chat.messages} loading={loading} />
      <ChatInput
        chatTitle={chat.title}
        hasAttachedDocs={hasAttachedDocs}
        loading={loading}
        onSendMessage={handleSendMessage}
      />
    </div>
  );
}
