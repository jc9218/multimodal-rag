import { QueryResponse } from "@/lib/api";

export interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  responseMeta?: QueryResponse;
  isError?: boolean;
}

export interface ChatSession {
  id: string;
  title: string;
  documentIds: string[]; // IDs of documents attached to this chat session
  documents?: IndexedDoc[]; // Cached metadata of documents attached to this chat session
  messages: Message[];
  createdAt: number;
  isCustomTitle?: boolean;
}

export interface IndexedDoc {
  id: string;
  name: string;
  createdAt?: string;
}
