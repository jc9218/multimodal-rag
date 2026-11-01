"use client";

import React from "react";
import { BookOpen } from "lucide-react";
import { RetrievedChunk } from "@/lib/api";
// Data contract SourcesBadgeListProps.

// Inputs: Properties, callbacks, or dependencies declared by the contract.
// Output: Typed structure consumed by the corresponding interface.
interface SourcesBadgeListProps {
  sources?: RetrievedChunk[];
}
/**
 * SourcesBadgeList function.
 *
 * @param { sources } - SourcesBadgeListProps.
 * @returns void.
 */
export default function SourcesBadgeList({ sources }: SourcesBadgeListProps) {
  if (!sources || sources.length === 0) return null;

  // Group pages by document and sort numerically to eliminate duplicate badges for the same page
  const docMap = new Map<string, { docName: string; pages: Set<number> }>();
  for (const src of sources) {

    const docName = src.document_name || "Documento";
    const key = (src.document_id || docName).trim().toLowerCase();
    if (!docMap.has(key)) {
      docMap.set(key, { docName, pages: new Set() });
    }
    if (typeof src.page === "number") {
      docMap.get(key)!.pages.add(src.page);
    }
  }
  const groupedSources = Array.from(docMap.values()).map((entry) => ({
    docName: entry.docName,
    pages: Array.from(entry.pages).sort((a, b) => a - b),
  }));

  if (groupedSources.length === 0) return null;
  return (
    <div className="mt-4 pt-3 border-t border-slate-700/60 flex flex-wrap gap-2">
      <div className="flex items-center space-x-1 text-[11px] text-slate-400 w-full mb-1">
        <BookOpen className="w-3.5 h-3.5 text-indigo-400" />

        <span>Fuentes recuperadas (Búsqueda Híbrida):</span>
      </div>

      {groupedSources.map((group, idx) => (
        <span
          key={idx}
          className="inline-flex items-center space-x-1.5 text-[11px] bg-slate-900/80 border border-slate-700 text-slate-300 px-2.5 py-1 rounded-md"
        >
          <span className="font-medium truncate max-w-[200px]" title={group.docName}>
            {group.docName}
          </span>
          <span className="text-slate-500">•</span>
          <span className="text-indigo-400 font-mono">
            {group.pages.length > 1
              ? `Págs. ${group.pages.join(", ")}`
              : `Pág. ${group.pages[0] ?? 1}`}
          </span>
        </span>
      ))}
    </div>
  );
}
