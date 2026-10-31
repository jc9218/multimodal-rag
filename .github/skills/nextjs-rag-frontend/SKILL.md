---
name: nextjs-rag-frontend
description: "Use when changing or debugging the Next.js/React frontend: chat UI, PDF upload, ingestion progress, polling, document selection, RAG requests, Markdown answers, source/image rendering, responsive Tailwind styling, accessibility, or client timeouts."
argument-hint: "Describe the frontend flow, component, or user experience to change."
---

# Next.js RAG Frontend

## Use for

- Next.js 16 App Router and React 19 client components under `frontend/src`.
- Chat sessions, attached document state, localStorage persistence, and document deletion.
- PDF upload UX, ingestion polling, progress/status messages, cancellation, and retry behavior.
- RAG API payloads, `AbortController` timeouts, error normalization, and source metadata.
- Markdown rendering, technical citations, diagrams, responsive Tailwind UI, and accessibility.

## Procedure

1. Trace the UI event through the component, `frontend/src/lib/api.ts`, and the backend response type.
2. Preserve strict TypeScript types and keep API interfaces synchronized with backend schemas.
3. Treat polling as a state machine: handle `PENDING`, `EXTRACTING`, `INDEXING`, `WAITING_QUOTA`, `COMPLETED`, `FAILED`, and `CANCELLED`.
4. Prevent duplicate requests, stale intervals, state updates after unmount, and accidental loss of persisted chat/document state.
5. Keep loading, error, cancellation, and empty states visible and actionable; preserve Spanish user-facing copy.
6. Use accessible controls, labels, keyboard behavior, readable contrast, and responsive layouts.
7. Validate with `cd frontend && npm run build`; run `npm run lint` when the change affects lintable source.
8. For polling, make terminal states stop all timers and abort in-flight requests; make
   progress/status updates accessible with `aria-live` without announcing every
   implementation detail.
9. For upload and chat submissions, guard against duplicate actions and preserve the
   selected document IDs across reload, cancellation, and failure.

## Project conventions

- Import workspace modules through the `@/*` alias.
- Reuse existing Lucide icons, Tailwind utilities, and API logging helpers.
- Keep client-only behavior in components marked `"use client"`.
- Do not put provider model names, backend URLs, credentials, or deployment values in client code.
