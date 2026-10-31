---
name: "Multimodal RAG Frontend"
description: "Use when editing the Next.js/React frontend, chat, PDF upload, ingestion polling, document state, Markdown answers, Tailwind UI, accessibility, or client API calls."
applyTo: "frontend/src/**/*.{ts,tsx,css}"
---

# Frontend Instructions

- Follow the existing Next.js 16 App Router and React 19 patterns.
- Keep TypeScript strict; update shared API interfaces when backend response shapes change.
- Preserve Spanish status, error, empty, and retry messages.
- Clean up `AbortController`, timers, polling intervals, and subscriptions.
- Stop polling on every terminal job state and guard against duplicate submissions.
- Keep loading and failure states explicit; do not silently return empty success states.
- Reuse the API helpers, `@/*` imports, Lucide icons, Tailwind utilities, and existing component boundaries.
- Treat document IDs and chat state as user-visible data; keep localStorage updates consistent after upload and deletion.
- Validate frontend changes with `npm run build`, and use `npm run lint` when appropriate.
- Do not describe browser behavior as tested unless a configured browser/component test ran.
