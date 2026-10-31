"use client";

import React, { useState, useEffect, useRef } from "react";
import Navbar from "@/components/common/Navbar";
import Sidebar from "@/components/sidebar/Sidebar";
import ChatInterface from "@/components/ChatInterface";
import SkillsModal from "@/components/SkillsModal";
import { getDocuments, deleteDocument } from "@/lib/api";
import { cleanDocumentTitle } from "@/lib/formatters";
import { ChatSession, IndexedDoc, Message } from "@/types/chat";

const STORAGE_KEY = "multimodal_rag_chat_workspaces_v4";
const INDEXED_DOCS_KEY = "multimodal_rag_indexed_docs_v1";

const createChatSession = (
  id: string,
  title: string = "Nuevo Chat",
  docIds: string[] = [],
  isCustomTitle: boolean = false,
  docs: IndexedDoc[] = []
): ChatSession => ({
  id,
  title,
  documentIds: docIds,
  documents: docs,
  isCustomTitle,
  messages: [
    {
      id: "initial-welcome",
      sender: "assistant",
      text: `👋 ¡Hola! Este es tu espacio de chat para **${title}**.\n\nPuedes hacerme preguntas técnicas sobre los documentos asociados. Las respuestas mantendrán el contexto de la conversación y consultarán únicamente los documentos vinculados a este espacio.`,
    },
  ],
  createdAt: Date.now(),
});

export default function Home() {
  const [indexedDocs, setIndexedDocs] = useState<IndexedDoc[]>(() => {
    if (typeof window === "undefined") return [];
    try {
      const saved = localStorage.getItem(INDEXED_DOCS_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      }
    } catch (e) {
      console.warn("Could not load initial indexedDocs from localStorage:", e);
    }
    return [];
  });

  const [chats, setChats] = useState<ChatSession[]>([]);
  const [activeChatId, setActiveChatId] = useState<string>("");
  const [showAttachMenu, setShowAttachMenu] = useState(false);
  const [showSkillsModal, setShowSkillsModal] = useState(false);

  const activeChatIdRef = useRef(activeChatId);
  useEffect(() => {
    activeChatIdRef.current = activeChatId;
  }, [activeChatId]);

  // Persist indexedDocs to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(INDEXED_DOCS_KEY, JSON.stringify(indexedDocs));
    } catch (e) {
      console.warn("Could not save indexedDocs to localStorage:", e);
    }
  }, [indexedDocs]);

  // 1. Load indexed documents from backend and merge with cache
  useEffect(() => {
    getDocuments()
      .then((docs) => {
        const mapped: IndexedDoc[] = (docs || []).map((d) => ({
          id: d.id,
          name: d.name,
          createdAt: d.created_at,
        }));
        setIndexedDocs((prev) => {
          const map = new Map<string, IndexedDoc>();
          for (const d of prev) map.set(d.id, d);
          for (const d of mapped) map.set(d.id, d);
          return Array.from(map.values()).filter((d) =>
            mapped.some((backendDoc) => backendDoc.id === d.id)
          );
        });

        // Heal existing chats that might reference valid documents
        setChats((prevChats) =>
          prevChats.map((c) => {
            const docMap = new Map(mapped.map((d) => [d.id, d]));
            const validDocumentIds = c.documentIds.filter((did) => docMap.has(did));
            const healedDocs: IndexedDoc[] = validDocumentIds.map((did) => docMap.get(did)!);
            return { ...c, documentIds: validDocumentIds, documents: healedDocs };
          })
        );
      })
      .catch((err) => {
        console.warn("Could not fetch documents from backend:", err);
      });
  }, []);

  // 2. Load chats from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          const sanitizedChats: ChatSession[] = parsed.map((c) => {
            if (!Array.isArray(c.documentIds) || c.documentIds.length === 0) return c;
            const fixedDocs = c.documentIds.map((did: string) => {
              const existing = Array.isArray(c.documents)
                ? c.documents.find((d: any) => d.id === did)
                : null;
              if (existing && existing.name && existing.name !== did) {
                return existing;
              }
              const friendly =
                c.title && !c.title.startsWith("Nuevo Chat")
                  ? c.title.endsWith(".pdf")
                    ? c.title
                    : `${c.title}.pdf`
                  : `Documento_${did.slice(0, 8)}.pdf`;
              return { id: did, name: friendly, createdAt: existing?.createdAt };
            });
            return { ...c, documents: fixedDocs };
          });

          setChats(sanitizedChats);
          setActiveChatId(sanitizedChats[0].id);

          const harvested: IndexedDoc[] = [];
          for (const c of sanitizedChats) {
            if (Array.isArray(c.documents)) {
              for (const d of c.documents) {
                if (d && d.id && d.name && d.name !== d.id) {
                  harvested.push(d);
                }
              }
            }
          }
          if (harvested.length > 0) {
            setIndexedDocs((prev) => {
              const map = new Map<string, IndexedDoc>();
              for (const d of prev) map.set(d.id, d);
              for (const d of harvested) map.set(d.id, d);
              return Array.from(map.values());
            });
          }
          return;
        }
      }
    } catch (e) {
      console.warn("Could not load chats from localStorage:", e);
    }

    const initialChat = createChatSession("chat_default", "Nuevo Chat", [], false);
    setChats([initialChat]);
    setActiveChatId(initialChat.id);
  }, []);

  // 3. Persist chats to localStorage whenever they change
  useEffect(() => {
    if (chats.length > 0) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(chats));
      } catch (e) {
        console.warn("Could not save chats to localStorage:", e);
      }
    }
  }, [chats]);

  const activeChat =
    chats.find((c) => c.id === activeChatId) ||
    chats[0] ||
    createChatSession("fallback", "Nuevo Chat", [], false);

  // Documents that belong strictly to the active chat
  const activeChatDocs: IndexedDoc[] = React.useMemo(() => {
    const docMap = new Map<string, IndexedDoc>();
    for (const d of indexedDocs) {
      if (d.name && d.name !== d.id) {
        docMap.set(d.id, d);
      }
    }
    if (activeChat.documents) {
      for (const d of activeChat.documents) {
        if (d.name && d.name !== d.id) {
          docMap.set(d.id, d);
        }
      }
    }

    return activeChat.documentIds
      .map((id) => {
        const found = docMap.get(id);
        if (found && found.name && found.name !== id) {
          return found;
        }

        let friendlyName = "";
        if (activeChat.title && !activeChat.title.startsWith("Nuevo Chat")) {
          friendlyName = activeChat.title.endsWith(".pdf")
            ? activeChat.title
            : `${activeChat.title}.pdf`;
        } else {
          friendlyName = `Documento_${id.slice(0, 8)}.pdf`;
        }

        return {
          id,
          name: friendlyName,
          createdAt: found?.createdAt,
        };
      })
      .filter(Boolean) as IndexedDoc[];
  }, [activeChat.documentIds, activeChat.documents, activeChat.title, indexedDocs]);

  // Other documents available in system that are not yet in this chat
  const otherAvailableDocs = indexedDocs.filter(
    (doc) => !activeChat.documentIds.includes(doc.id)
  );

  const handleCreateChat = () => {
    const newId = `chat_${Date.now()}`;
    const newTitle = `Nuevo Chat ${chats.length + 1}`;
    const newChat = createChatSession(newId, newTitle, [], false);
    setChats((prev) => [...prev, newChat]);
    setActiveChatId(newId);
  };

  const handleDeleteChat = async (chatId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const chatToDelete = chats.find((c) => c.id === chatId);
    const chatTitle = chatToDelete ? chatToDelete.title : "este chat";
    const docCount = chatToDelete?.documentIds?.length || 0;

    const confirmMsg =
      docCount > 0
        ? `¿Estás seguro de que deseas eliminar el chat "${chatTitle}", su historial y sus ${docCount} documento(s) asociado(s) de la base de datos y disco?`
        : `¿Estás seguro de que deseas eliminar el chat "${chatTitle}" y todo su historial de mensajes?`;

    if (!confirm(confirmMsg)) {
      return;
    }

    const docIdsToDelete = chatToDelete?.documentIds || [];

    if (docIdsToDelete.length > 0) {
      await Promise.allSettled(
        docIdsToDelete.map(async (docId) => {
          try {
            await deleteDocument(docId);
          } catch (err) {
            console.error(`🚨 [handleDeleteChat] Error al eliminar documento ${docId}:`, err);
          }
        })
      );

      setIndexedDocs((prev) => {
        const filtered = prev.filter((d) => !docIdsToDelete.includes(d.id));
        try {
          localStorage.setItem(INDEXED_DOCS_KEY, JSON.stringify(filtered));
        } catch {}
        return filtered;
      });
    }

    if (chats.length <= 1) {
      const resetChat = createChatSession(`chat_${Date.now()}`, "Nuevo Chat", [], false);
      setChats([resetChat]);
      setActiveChatId(resetChat.id);
      return;
    }

    const remaining = chats
      .filter((c) => c.id !== chatId)
      .map((c) => ({
        ...c,
        documentIds: c.documentIds.filter((id) => !docIdsToDelete.includes(id)),
        documents: (c.documents || []).filter((d) => !docIdsToDelete.includes(d.id)),
      }));

    setChats(remaining);
    if (activeChatId === chatId) {
      setActiveChatId(remaining[0].id);
    }
  };

  const handleRenameChat = (chatId: string, newTitle: string) => {
    setChats((prev) =>
      prev.map((c) =>
        c.id === chatId
          ? {
              ...c,
              title: newTitle,
              isCustomTitle: true,
              messages: c.messages.map((m) =>
                m.id === "initial-welcome"
                  ? {
                      ...m,
                      text: `👋 ¡Hola! Este es tu espacio de chat para **${newTitle}**.\n\nPuedes hacerme preguntas técnicas sobre los documentos asociados. Las respuestas mantendrán el contexto de la conversación y consultarán únicamente los documentos vinculados a este espacio.`,
                    }
                  : m
              ),
            }
          : c
      )
    );
  };

  const handleUpdateMessages = (chatId: string, messages: Message[]) => {
    setChats((prev) =>
      prev.map((c) => (c.id === chatId ? { ...c, messages } : c))
    );
  };

  const handleClearChat = (chatId: string) => {
    setChats((prev) =>
      prev.map((c) => {
        if (c.id === chatId) {
          return {
            ...c,
            messages: [
              {
                id: "initial-welcome",
                sender: "assistant",
                text: `🧹 Historial limpiado. Puedes continuar consultando sobre **${c.title}**.`,
              },
            ],
          };
        }
        return c;
      })
    );
  };

  const handleToggleDocForActiveChat = (chatId: string, docId: string) => {
    setChats((prev) =>
      prev.map((c) => {
        if (c.id === chatId) {
          const exists = c.documentIds.includes(docId);
          const newDocIds = exists
            ? c.documentIds.filter((id) => id !== docId)
            : [...c.documentIds, docId];

          const matchedDoc =
            indexedDocs.find((d) => d.id === docId) ||
            c.documents?.find((d) => d.id === docId) ||
            { id: docId, name: docId };

          const currentDocs = c.documents || [];
          const updatedDocs = exists
            ? currentDocs.filter((d) => d.id !== docId)
            : [...currentDocs.filter((d) => d.id !== docId), matchedDoc];

          let updatedTitle = c.title;
          if (
            !exists &&
            !c.isCustomTitle &&
            (c.title.startsWith("Nuevo Chat") || c.documentIds.length === 0)
          ) {
            if (matchedDoc && matchedDoc.name) {
              updatedTitle = cleanDocumentTitle(matchedDoc.name);
            }
          }

          return {
            ...c,
            documentIds: newDocIds,
            documents: updatedDocs,
            title: updatedTitle,
            messages: c.messages.map((m) =>
              m.id === "initial-welcome"
                ? {
                    ...m,
                    text: `👋 ¡Hola! Este es tu espacio de chat para **${updatedTitle}**.\n\nPuedes hacerme preguntas técnicas sobre los documentos asociados. Las respuestas mantendrán el contexto de la conversación y consultarán únicamente los documentos vinculados a este espacio.`,
                  }
                : m
            ),
          };
        }
        return c;
      })
    );
  };

  const handleDeleteDocument = async (docId: string, docName: string) => {
    if (
      !confirm(
        `¿Eliminar "${docName}" permanentemente de la base de datos vectorial y disco? Esta acción borrará todos sus fragmentos indexados.`
      )
    ) {
      return;
    }

    try {
      await deleteDocument(docId);

      setIndexedDocs((prev) => {
        const filtered = prev.filter((d) => d.id !== docId);
        try {
          localStorage.setItem(INDEXED_DOCS_KEY, JSON.stringify(filtered));
        } catch {}
        return filtered;
      });

      setChats((prev) =>
        prev.map((c) => ({
          ...c,
          documentIds: c.documentIds.filter((id) => id !== docId),
          documents: (c.documents || []).filter((d) => d.id !== docId),
        }))
      );
    } catch (err: any) {
      alert(`Error eliminando documento: ${err.message}`);
    }
  };

  const handleDocumentIndexed = (
    docId: string,
    filename: string,
    createdAt?: string,
    targetChatId?: string
  ) => {
    const newDoc: IndexedDoc = {
      id: docId,
      name: filename,
      createdAt: createdAt || new Date().toISOString(),
    };
    setIndexedDocs((prev) => {
      const filtered = prev.filter((d) => d.id !== docId);
      const updated = [newDoc, ...filtered];
      try {
        localStorage.setItem(INDEXED_DOCS_KEY, JSON.stringify(updated));
      } catch {}
      return updated;
    });

    // Exact filename preservation without altering casing or spaces
    const docTitle = cleanDocumentTitle(filename);
    const resolvedChatId =
      targetChatId || activeChatIdRef.current || activeChatId;

    setChats((prev) => {
      if (prev.length === 0) {
        const firstChat = createChatSession(
          `chat_${Date.now()}`,
          docTitle,
          [docId],
          false,
          [newDoc]
        );
        setActiveChatId(firstChat.id);
        return [firstChat];
      }

      const targetChat =
        prev.find((c) => c.id === resolvedChatId) || prev[0];

      if (targetChat) {
        setActiveChatId(targetChat.id);
      }

      return prev.map((c) => {
        if (c.id === targetChat.id) {
          const newDocIds = c.documentIds.includes(docId)
            ? c.documentIds
            : [...c.documentIds, docId];

          const currentDocs = c.documents || [];
          const updatedDocs = currentDocs.some((d) => d.id === docId)
            ? currentDocs.map((d) => (d.id === docId ? newDoc : d))
            : [...currentDocs, newDoc];

          const shouldAdoptTitle =
            !c.isCustomTitle &&
            (c.title.startsWith("Nuevo Chat") || c.documentIds.length === 0);

          const finalTitle = shouldAdoptTitle ? docTitle : c.title;

          return {
            ...c,
            title: finalTitle,
            documentIds: newDocIds,
            documents: updatedDocs,
            messages: c.messages.map((m) =>
              m.id === "initial-welcome"
                ? {
                    ...m,
                    text: `👋 ¡Hola! Este es tu espacio de chat para **${finalTitle}**.\n\nPuedes hacerme preguntas técnicas sobre los documentos asociados. Las respuestas mantendrán el contexto de la conversación y consultarán únicamente los documentos vinculados a este espacio.`,
                  }
                : m
            ),
          };
        }
        return c;
      });
    });
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100">
      {/* Top Navbar */}
      <Navbar onOpenSkills={() => setShowSkillsModal(true)} />

      {/* Main Content Body */}
      <div className="flex-1 flex overflow-hidden p-6 gap-6">
        {/* Left Modular Sidebar */}
        <Sidebar
          chats={chats}
          activeChat={activeChat}
          activeChatId={activeChatId}
          activeChatDocs={activeChatDocs}
          otherAvailableDocs={otherAvailableDocs}
          showAttachMenu={showAttachMenu}
          onDocumentIndexed={handleDocumentIndexed}
          onSelectChat={(id) => setActiveChatId(id)}
          onCreateChat={handleCreateChat}
          onDeleteChat={handleDeleteChat}
          onToggleAttachMenu={() => setShowAttachMenu((prev) => !prev)}
          onAttachDoc={(chatId, docId) => handleToggleDocForActiveChat(chatId, docId)}
          onDetachDoc={(chatId, docId) => handleToggleDocForActiveChat(chatId, docId)}
          onDeleteDoc={handleDeleteDocument}
        />

        {/* Right Main Chat Panel */}
        <main className="flex-1 h-full overflow-hidden">
          <ChatInterface
            chat={activeChat}
            allIndexedDocs={indexedDocs}
            onUpdateMessages={handleUpdateMessages}
            onRenameChat={handleRenameChat}
            onToggleDoc={handleToggleDocForActiveChat}
            onClearChat={handleClearChat}
            onDeleteDoc={handleDeleteDocument}
          />
        </main>
      </div>

      {/* Modal de Habilidades y Capacidades del Sistema */}
      <SkillsModal
        isOpen={showSkillsModal}
        onClose={() => setShowSkillsModal(false)}
      />
    </div>
  );
}
