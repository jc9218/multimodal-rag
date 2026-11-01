import { QueryResponse } from "@/lib/api";

// Data contract Message.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
export interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  responseMeta?: QueryResponse;
  isError?: boolean;
}

// Data contract ChatSession.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
export interface ChatSession {
  id: string;
  title: string;
  documentIds: string[]; // IDs of documents attached to this chat session
  documents?: IndexedDoc[]; // Cached metadata of documents attached to this chat session
  messages: Message[];
  createdAt: number;
  isCustomTitle?: boolean;
}

// Data contract IndexedDoc.
// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
export interface IndexedDoc {
  id: string;
  name: string;
  createdAt?: string;
}
