---
name: rag-backend
description: "Use when changing or debugging the Python FastAPI RAG backend: PDF parsing, PyMuPDF/OCR, embeddings, Gemini/OpenAI/Ollama, Qdrant, BM25, Redis jobs, ingestion progress, memory, quotas, retries, or backend tests."
argument-hint: "Describe the backend RAG flow, failure, or performance issue."
---

# RAG Backend

## Use for

- Ingestion of technical PDFs, images, tables, OCR, and spatial correlation.
- Embedding generation, LLM prompts, token budgets, quotas, and retries.
- Qdrant dense retrieval, BM25 sparse retrieval, RRF, hydration, and document filters.
- Redis-backed job status, in-memory fallback, progress reporting, and cancellation.
- FastAPI routes, application use cases, ports/adapters, and Python unit tests.

## Procedure

1. Trace the request through the route, use case, port, and adapter before editing.
2. Verify configuration values come from `Settings` and environment variables; do not hardcode provider model names, embedding names, URLs, credentials, or deployment-specific limits.
3. Keep provider failures explicit and preserve the repository's documented fallback behavior.
4. For ingestion changes, cover extraction, embeddings, sparse indexing, dense indexing, cancellation, quota waits, memory release, and job progress.
5. Add or update a focused test for the observed failure, then run `cd backend && .venv/bin/pytest -q`.
6. Validate Python syntax and `git diff --check` before reporting completion.
7. Verify progress callbacks are monotonic, bounded, and not written more often than
   the job store can sustain. Test cancellation and terminal cleanup at every stage.
8. For large documents, measure peak memory and stage duration separately; cover
   native-text, image-heavy, scanned, and table-rich PDFs.

## Invariants

- Respect the hexagonal boundaries between application use cases, ports, and adapters.
- Keep document filtering scoped to the active chat's document IDs.
- Never expose API keys or sensitive environment values in logs.
- Preserve the user-facing Spanish error and progress messages unless the task explicitly changes UX.
