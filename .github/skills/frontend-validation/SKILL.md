---
name: frontend-validation
description: "Use when validating or reviewing the multimodal-rag frontend: Next.js production builds, TypeScript errors, ESLint, configured Playwright E2E tests, upload and polling flows, chat interactions, responsive behavior, accessibility, or regression checks."
argument-hint: "Specify the frontend flow or files to validate."
---

# Frontend Validation

## Procedure

1. Identify the changed component and its API/state dependencies.
2. Run the smallest relevant check first:
   - `cd frontend && npm run build` for TypeScript and production compilation.
   - `cd frontend && npm run lint` for ESLint-sensitive changes.
   - Run the configured Playwright command only when Playwright and its config exist.
3. For upload or chat changes, verify the full state transition and error paths, not only the rendered success state.
4. Check timeout cleanup, polling interval cleanup, localStorage synchronization, and disabled controls during requests.
5. Report warnings separately from failures and never mask failed API responses with success-shaped UI state.

## Regression checklist

- Upload: PDF validation, large-file timeout, accepted response, job polling, cancellation, failure, and retry.
- Chat: no documents, sending state, timeout, backend error, fallback answer, citations, images, and scroll behavior.
- State: active chat changes, document deletion, reload/restore, empty collections, and duplicate submissions.
- UI: keyboard access, visible focus, responsive layout, readable progress text, and accessible status updates.

## Coverage limits

The current frontend scripts provide build and lint validation. They are not a
replacement for browser tests. Do not report upload, polling, chat, or accessibility
behavior as tested unless a configured browser or component test actually ran.
