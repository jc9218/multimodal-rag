---
name: fullstack-performance
description: "Use when profiling or optimizing multimodal-rag performance: PDF extraction, OCR, memory, embeddings, BM25, Qdrant, LLM tokens, frontend bundles, polling, Web Vitals, and request latency."
argument-hint: "Describe the slow flow, measurable target, or production metric."
---

# Full-Stack Performance

## Procedure

1. Define a measurable target and capture a baseline for the same document, query,
   environment, and concurrency.
2. Profile one boundary at a time:
   - parser page, image decode/save, table extraction, OCR, and chunking;
   - embedding batches, token counts, quota waits, and retries;
   - BM25 construction and Qdrant payload/vector batches;
   - frontend upload/network timing, polling requests, renders, and bundle size.
3. Optimize the dominant measured stage, then repeat the same benchmark. Preserve
   cancellation, progress monotonicity, document filtering, and answer quality.
4. For LLM calls, bound history, context, and output using environment-backed
   settings. Reuse embeddings where safe and avoid duplicate serialization or copies.
5. For frontend work, avoid duplicate polling, abort stale requests, virtualize only
   measured large lists, and check Web Vitals and network timing in a production-like
   build.
6. Record memory peak and release behavior for large PDFs; do not trade correctness
   for an arbitrary timeout increase.

## Required validation

- Compare p50/p95 latency, peak RSS, request count, and provider token usage.
- Test text PDFs, image-heavy PDFs, scanned PDFs, tables, and multi-document chats.
- Verify progress remains monotonic and terminal jobs stop all timers/work.
- Run the smallest configured build, lint, test, or profiling command and state
  which measurements were unavailable.
