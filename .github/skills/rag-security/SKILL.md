---
name: rag-security
description: "Use when reviewing or changing security-sensitive multimodal-rag behavior: PDF uploads, filenames, path traversal, document access, prompt injection, API errors, secrets, Redis jobs, Qdrant filters, and deletion endpoints."
argument-hint: "Describe the security boundary, endpoint, or data flow to review."
---

# RAG Security

## Review procedure

1. Trace untrusted input from HTTP request through validation, storage, parsing,
   retrieval, prompting, and response serialization.
2. Validate PDF type and size, normalize filenames, prevent path traversal, use
   safe temporary paths, and remove partial artifacts on failure or cancellation.
3. Enforce document ownership/scope at every retrieval, hydration, image, and delete
   boundary. Never trust a client-supplied document ID by itself. If authentication
   is not configured, report ownership authorization as an explicit remaining risk
   rather than implying document IDs provide access control.
4. Treat document text and images as untrusted prompt content. Keep system
   instructions separate and require grounded answers without allowing document text
   to override application policy.
5. Redact credentials, provider headers, signed URLs, prompts, and sensitive document
   content from logs and error responses.
6. Check rate limits, request timeouts, upload concurrency, job cancellation, and
   resource exhaustion from decompression, OCR, image dimensions, and large payloads.

## Required validation

- Test traversal-like filenames, invalid extensions/content, oversized uploads, and
  malformed PDFs.
- Test cross-document retrieval, image access, deletion, and chat authorization.
- Confirm provider model and embedding names come only from environment-backed settings.
- Confirm failures are explicit and do not become empty successful responses.
