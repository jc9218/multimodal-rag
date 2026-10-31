---
name: production-observability
description: "Use when diagnosing multimodal-rag production behavior on Render: memory limits, cold starts, Redis jobs, Qdrant, Gemini latency, upload progress, timeouts, logs, metrics, and deployment configuration."
argument-hint: "Describe the production symptom, service, job ID, or time window."
---

# Production Observability

## Procedure

1. Establish the deployment, service, commit, UTC time window, and affected
   `job_id`/`document_id` before drawing conclusions.
2. Correlate frontend requests with backend logs using job and document identifiers.
   Include stage and duration fields, but never log credentials, tokens, or full
   document contents.
3. Separate failures by boundary:
   - upload and request body;
   - job repository and Redis connectivity;
   - PDF extraction, OCR, tables, and image persistence;
   - embeddings, quota waits, and LLM calls;
   - BM25/Qdrant indexing and retrieval;
   - frontend polling, timeout, and rendering.
4. For memory incidents, compare concurrent jobs, PDF size/page count, extracted
   image bytes, embedding batch sizes, BM25 state, and process RSS. Distinguish a
   traffic spike from retained objects.
5. Verify Render environment variables and deployed commit without printing secret
   values. A `redis://redis:6379/0` URL is valid only for the Compose network, not
   for an external Render service.
6. Report evidence, impact, likely cause, confidence, and the next measurement or
   surgical fix. Do not treat an in-memory Redis fallback as durable production
   job storage.
7. Record whether the deployment has an identity/authorization layer. Document and
   image IDs provide scoping for retrieval, but they are not user authorization
   without authenticated ownership checks.

## Useful signals

- `job_id`, `document_id`, page number, extraction stage, chunk count, and elapsed
  milliseconds.
- Redis connection errors, job status transitions, and restart timestamps.
- Qdrant request status and collection/vector dimension.
- LLM model from configuration, request duration, retry count, and provider status.
- Upload size, polling interval, request count, abort/timeout reason, and response code.

## Safety

- Redact API keys, authorization headers, signed URLs, and document text.
- Use read-only inspection first; do not restart or scale services without explicit
  approval.
- Do not infer a memory leak from one restart or an LLM issue from a frontend timeout
  alone.
