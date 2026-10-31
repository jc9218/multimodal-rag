import { QueryResponse } from "@/lib/api";

// Clase: contrato de datos Message.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
export interface Message {
  id: string;
  sender: "user" | "assistant";
  text: string;
  responseMeta?: QueryResponse;
  isError?: boolean;
}

// Clase: contrato de datos ChatSession.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
export interface ChatSession {
  id: string;
  title: string;
  documentIds: string[]; // IDs of documents attached to this chat session
  documents?: IndexedDoc[]; // Cached metadata of documents attached to this chat session
  messages: Message[];
  createdAt: number;
  isCustomTitle?: boolean;
}

// Clase: contrato de datos IndexedDoc.
// Entradas: propiedades, callbacks o dependencias declaradas por el contrato.
// Salida: estructura tipada consumida por la interfaz correspondiente.
export interface IndexedDoc {
  id: string;
  name: string;
  createdAt?: string;
}
