"use client";

import React, { useState } from "react";
import { queryRAG } from "@/lib/api";
import { ChatSession, IndexedDoc, Message } from "@/types/chat";
import ChatHeader from "./chat/ChatHeader";
import ChatMessageList from "./chat/ChatMessageList";
import ChatInput from "./chat/ChatInput";

// Clase: contrato de datos ChatInterfaceProps.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
interface ChatInterfaceProps {
  chat: ChatSession;
  allIndexedDocs: IndexedDoc[];
  onUpdateMessages: (chatId: string, messages: Message[]) => void;
  onRenameChat: (chatId: string, newTitle: string) => void;
  onToggleDoc: (chatId: string, docId: string) => void;
  onClearChat: (chatId: string) => void;
  onDeleteDoc?: (docId: string, docName: string) => void;
}

export default function ChatInterface({
  chat,
  allIndexedDocs,
  onUpdateMessages,
  onRenameChat,
  onToggleDoc,
  onClearChat,
}: ChatInterfaceProps) {
  const [loading, setLoading] = useState(false);

  const hasAttachedDocs = Boolean(chat.documentIds && chat.documentIds.length > 0);

  // Objetivo: handleSendMessage.
  // Entradas: userQuery: string.
  // Salida: valor indicado por la firma o efecto de la operación.
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
          "El servidor en la nube tardó más de lo esperado en responder (puede estar despertándose tras inactividad en el plan gratuito de Render). Por favor reintenta tu pregunta en unos momentos.";
      } else if (
        raw.includes("404") ||
        raw.includes("not found") ||
        raw.includes("gemini") ||
        raw.includes("inteligencia artificial") ||
        raw.includes("LLM") ||
        raw.includes("completion")
      ) {
        friendlyText =
          "El servicio de inteligencia artificial no se encuentra disponible temporalmente o la solicitud no pudo completarse. Por favor, formula nuevamente tu pregunta o reintenta en unos instantes.";
      } else if (raw.includes("vector") || raw.includes("base de datos")) {
        friendlyText =
          "Hubo una dificultad momentánea al consultar los fragmentos del documento en el repositorio vectorial. Por favor, reintenta tu pregunta.";
      } else if (
        raw &&
        !raw.includes("HTTP") &&
        !raw.includes("{") &&
        !raw.includes("Traceback")
      ) {
        friendlyText = raw;
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
