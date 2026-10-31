---
name: "Multimodal RAG Backend"
description: "Use when editing Python backend code for FastAPI, PDF parsing, OCR, embeddings, LLMs, Qdrant, BM25, Redis jobs, ingestion progress, or backend tests."
applyTo: "backend/**/*.py"
---

# Backend Instructions

- Preserve the application/ports/adapters boundaries.
- Load model names, embedding names, URLs, limits, and credentials from environment-backed settings.
- Keep errors explicit and preserve job status transitions and cancellation behavior.
- For ingestion changes, account for memory, quota waits, retries, progress callbacks, and cleanup.
- Keep progress monotonic and bounded; measure stage durations and peak memory for large PDFs.
- Keep logs diagnostic but never log credentials or full sensitive document contents.
- Add focused tests and run `cd backend && .venv/bin/pytest -q`.
