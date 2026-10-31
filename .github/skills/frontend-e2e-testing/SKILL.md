---
name: frontend-e2e-testing
description: "Use when validating browser behavior in the multimodal-rag frontend: Playwright E2E tests for PDF uploads, ingestion polling, cancellation, chat, error states, accessibility, and responsive flows."
argument-hint: "Describe the browser flow or regression to cover."
---

# Frontend E2E Testing

## Scope

Use this workflow for behavior that cannot be proven reliably with a build or lint
check, especially upload, polling, cancellation, and chat interactions.

## Procedure

1. Confirm that Playwright is installed and that a browser/server configuration exists
   before running E2E tests. Do not claim E2E coverage when only lint or build ran.
2. Prefer deterministic API interception for upload, job polling, deletion, and chat
   responses. Do not call production APIs or consume provider quota from tests.
3. Cover the complete state transition, including loading, retry, failure, cancellation,
   timeout, and unmount cleanup.
4. Assert user-visible Spanish messages, progress values, disabled controls, citations,
   and accessible names rather than implementation details.
5. Run the smallest project-configured Playwright selector first, then the full suite
   when shared fixtures or API contracts change.

## Required scenarios

- Upload a valid PDF and advance through `PENDING`, `EXTRACTING`, `INDEXING`, and
  `COMPLETED`.
- Show a failed and cancelled job without leaving a polling timer active.
- Restore an active job after reload and stop polling at a terminal state.
- Prevent duplicate upload and chat submissions.
- Submit a question with selected document IDs and render answer sources/images.
- Display timeout, API error, empty-document, and no-answer states.
- Verify keyboard access, focus visibility, `aria-live` progress updates, and responsive
  layout for the upload and chat surfaces.

## Safety

- Mock provider and backend calls; never expose keys or use real Render, Qdrant, Redis,
  or LLM services in tests.
- Keep fixtures small and synthetic.
- If Playwright is not configured, report that limitation explicitly and run the
  configured build/lint checks instead.
