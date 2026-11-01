import logging

import re

import threading

import time

from typing import Optional

from src.infrastructure.config import settings

from src.infrastructure.memory import get_process_memory_mb, release_memory

from src.domain.models import JobStatusEnum

from src.domain.exceptions import JobCancelledError

from src.ports.document_parser_port import DocumentParserPort

from src.ports.job_repository_port import JobRepositoryPort

from src.ports.llm_port import LLMPort

from src.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)

# Serialize background ingestion tasks to protect instances with tight RAM limits (e.g. Render 512MB)

_INGESTION_SEMAPHORE = threading.Semaphore(1)


def _process_memory_mb() -> int:
    """Return the worker's peak resident memory when the platform exposes it."""

    return get_process_memory_mb()


# Class: IngestDocumentUseCase.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class IngestDocumentUseCase:
    # Purpose: Init.

    # Inputs: self, parser, vector_store, llm, job_repo.

    # Output: Operation result, or None when no value is returned.

    def __init__(
        self,
        parser: DocumentParserPort,
        vector_store: VectorStorePort,
        llm: LLMPort,
        job_repo: JobRepositoryPort,
    ):
        """init.

        Args:

            parser: DocumentParserPort, vector_store: VectorStorePort, llm: LLMPort, job_repo: JobRepositoryPort.

        Returns:

            unspecified..

        """

        self.parser = parser

        self.vector_store = vector_store

        self.llm = llm

        self.job_repo = job_repo

    def _is_cancelled(self, job_id: str) -> bool:
        """Checks if the user requested cancellation of this job."""

        job = self.job_repo.get_job(job_id)

        return job is not None and job.status == JobStatusEnum.CANCELLED

    def _cleanup_failed_ingestion(self, document_id: str) -> None:
        """Remove partial vectors, source files, and derived images after failure."""

        try:
            self.vector_store.delete_document(document_id)

        except Exception:
            logger.exception(
                "[IngestDocumentUseCase] Failed to remove partial vectors document_id=%s",
                document_id,
            )

        try:
            self.parser.storage.delete_document_files(document_id)

        except Exception:
            logger.exception(
                "[IngestDocumentUseCase] Failed to remove source artifacts document_id=%s",
                document_id,
            )

    # Purpose: Cleanup local cache.

    # Inputs: self, document_id.

    # Output: None.

    def _cleanup_local_cache(self, document_id: str) -> None:
        """cleanup local cache.

        Args:

            document_id: str.

        Returns:

            None..

        """

        cleanup = getattr(self.parser.storage, "cleanup_local_cache", None)

        if cleanup:
            try:
                cleanup(document_id)

            except Exception:
                logger.exception(
                    "[IngestDocumentUseCase] Failed to clean local cache document_id=%s",
                    document_id,
                )

    # Purpose: Cancel and cleanup.

    # Inputs: self, job_id, document_id.

    # Output: bool.

    def _cancel_and_cleanup(self, job_id: str, document_id: str) -> bool:
        """cancel and cleanup.

        Args:

            job_id: str, document_id: str.

        Returns:

            bool..

        """

        if not self._is_cancelled(job_id):
            return False

        self._cleanup_failed_ingestion(document_id)

        return True

    def _is_quota_error(self, exc: Exception) -> bool:
        """Detects rate limits, quota exhaustion or 429 from LLM providers."""

        err = f"{exc} {getattr(exc, '__cause__', '')}".lower()

        return any(
            k in err
            for k in [
                "429",
                "resource_exhausted",
                "quota",
                "rate limit",
                "rate_limit",
                "ratelimit",
                "too many requests",
                "exhausted",
            ]
        )

    def _is_daily_quota_error(self, exc: Exception) -> bool:
        """Detects if quota exhaustion is daily or plan-wide and cannot be resolved by waiting 30-45s."""

        text = f"{exc} {getattr(exc, '__cause__', '')}".lower()

        if any(
            pattern in text
            for pattern in (
                "per day",
                "requests per day",
                "daily",
                "free_tier_requests",
                "exceeded your current quota",
                "check your plan and billing",
                "billing",
                "insufficient_quota",
            )
        ):
            return True

        raw_delay = self._extract_retry_delay(exc, default_seconds=0)

        return raw_delay > 90

    def _extract_retry_delay(self, exc: Exception, default_seconds: int = 35) -> int:
        """Parses the recommended retry delay from error messages if present."""

        text = f"{exc} {getattr(exc, '__cause__', '')}"

        match = re.search(
            r"(?:retry(?:\s+in\s+|\s+after\s+|Delay['\":\s]+)|seconds:\s*)(\d+(?:\.\d+)?)",
            text,
            re.IGNORECASE,
        )

        if match:
            try:
                return max(5, int(float(match.group(1))) + 2)

            except Exception:
                pass

        return default_seconds

    def _wait_for_quota_recovery(
        self, job_id: str, wait_seconds: int, progress: float
    ) -> bool:
        """

        Pauses processing while the API quota resets, updating countdown in real-time.

        Allows immediate user cancellation at any point during the wait.

        """

        for remaining in range(wait_seconds, 0, -2):
            if self._is_cancelled(job_id):
                return False

            self.job_repo.update_job_status(
                job_id=job_id,
                status=JobStatusEnum.WAITING_QUOTA,
                progress=progress,
                message=f"El procesamiento está en pausa temporal. Continuará automáticamente ({remaining}s restantes)...",
            )

            time.sleep(2)

        if self._is_cancelled(job_id):
            return False

        self.job_repo.update_job_status(
            job_id=job_id,
            status=JobStatusEnum.INDEXING,
            progress=progress,
            message="Cuota restablecida. Reanudando procesamiento...",
        )

        return True

    def _generate_embeddings_with_quota_retry(
        self,
        job_id: str,
        texts: list,
        progress: float,
        incremental_state: Optional[dict] = None,
        max_quota_retries: int = 3,
    ) -> list:
        """

        Generates dense embeddings for a batch of texts with resilient quota backoff.

        If a transient rate limit occurs (HTTP 429 RPM), pauses in WAITING_QUOTA and retries.

        If a daily limit is reached or retries are exhausted, automatically degrades to

        zero-vectors for BM25 lexical indexing so the document upload never fails.

        Raises JobCancelledError if the user cancels during wait.

        """

        quota_attempts = 0

        while True:
            if self._is_cancelled(job_id):
                raise JobCancelledError(f"Job {job_id} was cancelled by user.")

            try:
                return self.llm.generate_embeddings(texts)

            except Exception as exc:
                if self._is_quota_error(exc):
                    # Check if it's daily or non-transient quota

                    if self._is_daily_quota_error(exc):
                        logger.warning(
                            f"[IngestDocumentUseCase] Job {job_id}: Daily embedding quota exceeded for provider. "
                            "Gracefully falling back to BM25 lexical indexing."
                        )

                        if incremental_state is not None:
                            incremental_state["degraded"] = True

                        self.job_repo.update_job_status(
                            job_id=job_id,
                            status=JobStatusEnum.INDEXING,
                            progress=progress,
                            message="Cuota de embeddings agotada por hoy. Continuando con índice léxico BM25...",
                        )

                        dim = getattr(
                            self.llm, "embedding_dim", settings.EMBEDDING_DIMENSION
                        )

                        return [[0.0] * dim for _ in texts]

                    if quota_attempts < max_quota_retries:
                        quota_attempts += 1

                        raw_delay = self._extract_retry_delay(exc, default_seconds=30)

                        delay = min(raw_delay, 40)

                        logger.warning(
                            f"[IngestDocumentUseCase] Job {job_id}: Quota limit encountered "
                            f"(attempt {quota_attempts}/{max_quota_retries}). Waiting {delay}s for quota window reset."
                        )

                        can_continue = self._wait_for_quota_recovery(
                            job_id, delay, progress
                        )

                        if not can_continue:
                            logger.info(
                                f"[IngestDocumentUseCase] Job {job_id} cancelled while waiting for quota."
                            )

                            raise JobCancelledError(
                                f"Job {job_id} was cancelled by user."
                            )

                        continue

                    # If all retries exhausted, degrade to BM25 rather than failing the upload!

                    logger.warning(
                        f"[IngestDocumentUseCase] Job {job_id}: Quota retries exhausted ({max_quota_retries}). "
                        "Gracefully falling back to BM25 lexical indexing."
                    )

                    if incremental_state is not None:
                        incremental_state["degraded"] = True

                    self.job_repo.update_job_status(
                        job_id=job_id,
                        status=JobStatusEnum.INDEXING,
                        progress=progress,
                        message="La respuesta automática no está disponible temporalmente. Continuando con un método alternativo...",
                    )

                    dim = getattr(
                        self.llm, "embedding_dim", settings.EMBEDDING_DIMENSION
                    )

                    return [[0.0] * dim for _ in texts]

                raise

    def execute_async(self, job_id: str, file_path: str, document_id: str) -> None:
        """

        Background worker method for processing PDF ingestion.

        Guarantees updating job status on every stage and handling failures gracefully.

        Serializes execution with _INGESTION_SEMAPHORE to prevent concurrent RAM spikes.

        """

        if self._is_cancelled(job_id):
            logger.info(
                f"[IngestDocumentUseCase:execute_async] Job {job_id} was cancelled before starting."
            )

            self._cleanup_failed_ingestion(document_id)

            return

        with _INGESTION_SEMAPHORE:
            try:
                if self._is_cancelled(job_id):
                    logger.info(
                        f"[IngestDocumentUseCase:execute_async] Job {job_id} was cancelled before acquisition."
                    )

                    self._cleanup_failed_ingestion(document_id)

                    return

                ingestion_started = time.monotonic()

                logger.info(
                    "[IngestDocumentUseCase:execute_async] ingestion_started "
                    f"job_id={job_id} document_id={document_id}"
                )

                self.job_repo.update_job_status(
                    job_id=job_id,
                    status=JobStatusEnum.EXTRACTING,
                    progress=0.05,
                    message="Leyendo texto, tablas y diagramas del documento...",
                )

                # Step 1: Multimodal Extraction and Spatial Correlation

                # Purpose: Report extraction progress.

                # Inputs: fraction, detail.

                # Output: None.

                def report_extraction_progress(fraction: float, detail: str) -> None:
                    """Report extraction progress.

                    Args:

                        fraction: float, detail: str.

                    Returns:

                        None..

                    """

                    progress = 0.05 + 0.25 * max(0.0, min(1.0, fraction))

                    self.job_repo.update_job_status(
                        job_id=job_id,
                        status=JobStatusEnum.EXTRACTING,
                        progress=round(progress, 2),
                        message=detail,
                    )

                incremental_state = {"called": False, "indexed": 0}

                job_obj = self.job_repo.get_job(job_id)

                doc_name = job_obj.filename if job_obj else document_id

                created_at_iso = (
                    job_obj.created_at.isoformat()
                    if job_obj and hasattr(job_obj, "created_at")
                    else None
                )

                # Purpose: Index page.

                # Inputs: page_num, total_pages, page_chunks, page_images.

                # Output: None.

                def index_page(
                    page_num: int,
                    total_pages: int,
                    page_chunks: list,
                    page_images: list,
                ) -> None:
                    """Index page.

                    Args:

                        page_num: int, total_pages: int, page_chunks: list, page_images: list.

                    Returns:

                        None..

                    """

                    if self._is_cancelled(job_id):
                        raise JobCancelledError(f"Job {job_id} was cancelled by user.")

                    incremental_state["called"] = True

                    for chunk in page_chunks:
                        chunk.metadata["document_name"] = doc_name

                        if created_at_iso:
                            chunk.metadata["created_at"] = created_at_iso

                    if hasattr(self.vector_store, "register_images"):
                        self.vector_store.register_images(page_images)

                    current_job = self.job_repo.get_job(job_id)

                    cur_progress = max(
                        float(current_job.progress) if current_job else 0.0,
                        round(0.05 + 0.25 * page_num / max(total_pages, 1), 2),
                    )

                    for start in range(
                        0, len(page_chunks), settings.EMBEDDING_BATCH_SIZE
                    ):
                        batch = page_chunks[
                            start : start + settings.EMBEDDING_BATCH_SIZE
                        ]

                        batch_texts = [c.text for c in batch]

                        embeddings = self._generate_embeddings_with_quota_retry(
                            job_id=job_id,
                            texts=batch_texts,
                            progress=cur_progress,
                            incremental_state=incremental_state,
                        )

                        for chunk, embedding in zip(batch, embeddings):
                            chunk.embedding = embedding

                    indexed = self.vector_store.index_chunks(page_chunks)

                    incremental_state["indexed"] += indexed

                    release_memory()

                    self.job_repo.update_job_status(
                        job_id=job_id,
                        status=JobStatusEnum.INDEXING,
                        progress=round(0.35 + 0.63 * page_num / max(total_pages, 1), 2),
                        message=(
                            f"Página {page_num} de {total_pages} procesada; "
                            f"{incremental_state['indexed']} fragmentos guardados."
                        ),
                    )

                chunks, images = self.parser.parse_pdf(
                    file_path=file_path,
                    document_id=document_id,
                    progress_callback=report_extraction_progress,
                    page_callback=index_page,
                )

                logger.info(
                    "[IngestDocumentUseCase:execute_async] extraction_complete "
                    f"job_id={job_id} document_id={document_id} chunks={len(chunks)} "
                    f"images={len(images)} duration_ms={int((time.monotonic() - ingestion_started) * 1000)} "
                    f"peak_rss_mb={_process_memory_mb()}"
                )

                if self._is_cancelled(job_id):
                    logger.info(
                        f"[IngestDocumentUseCase:execute_async] Job {job_id} was cancelled after extraction."
                    )

                    self._cleanup_failed_ingestion(document_id)

                    return

                if incremental_state["called"]:
                    del chunks

                    del images

                    release_memory()

                    if incremental_state.get("degraded"):
                        msg = f"¡Documento listo! {incremental_state['indexed']} fragmentos preparados con un método alternativo."

                    else:
                        msg = (
                            f"¡Documento listo! {incremental_state['indexed']} fragmentos preparados para consulta."
                            if incremental_state["indexed"] > 0
                            else "Documento procesado (no se detectó texto para indexar)."
                        )

                    self.job_repo.update_job_status(
                        job_id=job_id,
                        status=JobStatusEnum.COMPLETED,
                        progress=1.0,
                        message=msg,
                    )

                    self._cleanup_local_cache(document_id)

                    return

                if not chunks:
                    self.job_repo.update_job_status(
                        job_id=job_id,
                        status=JobStatusEnum.COMPLETED,
                        progress=1.0,
                        message="Documento procesado (no se detectó texto para indexar).",
                    )

                    return

                self.job_repo.update_job_status(
                    job_id=job_id,
                    status=JobStatusEnum.EXTRACTING,
                    progress=0.30,
                    message=f"Estructura analizada ({len(chunks)} fragmentos, {len(images)} imágenes). Iniciando procesamiento...",
                )

                # Ensure document_name and created_at are populated across all chunks.

                for c in chunks:
                    c.metadata["document_name"] = doc_name

                    if created_at_iso:
                        c.metadata["created_at"] = created_at_iso

                self.job_repo.update_job_status(
                    job_id=job_id,
                    status=JobStatusEnum.INDEXING,
                    progress=0.33,
                    message=f"Metadatos preparados para {len(chunks)} fragmentos.",
                )

                # Also register extracted images in vector store adapter for hydration

                if hasattr(self.vector_store, "register_images"):
                    self.vector_store.register_images(images)

                self.job_repo.update_job_status(
                    job_id=job_id,
                    status=JobStatusEnum.INDEXING,
                    progress=0.35,
                    message=f"Imágenes registradas ({len(images)}). Preparando embeddings...",
                )

                # Step 2: Dense Embeddings Generation (Batched with quota recovery & direct assignment)

                total_chunks = len(chunks)

                batch_size = settings.EMBEDDING_BATCH_SIZE

                embeddings_started = time.monotonic()

                for i in range(0, total_chunks, batch_size):
                    if self._is_cancelled(job_id):
                        logger.info(
                            f"[IngestDocumentUseCase:execute_async] Job {job_id} cancelled during batch {i}."
                        )

                        self._cleanup_failed_ingestion(document_id)

                        return

                    batch_chunks = chunks[i : i + batch_size]

                    batch_texts = [c.text for c in batch_chunks]

                    ratio = i / total_chunks

                    cur_prog = round(0.35 + 0.35 * ratio, 2)

                    batch_embeddings = self._generate_embeddings_with_quota_retry(
                        job_id=job_id,
                        texts=batch_texts,
                        progress=cur_prog,
                        incremental_state=incremental_state,
                    )

                    for chunk, embedding in zip(batch_chunks, batch_embeddings):
                        chunk.embedding = embedding

                    del batch_texts

                    del batch_embeddings

                    processed = min(i + len(batch_chunks), total_chunks)

                    pct = int((processed / total_chunks) * 100)

                    progress_val = 0.35 + 0.35 * (processed / total_chunks)

                    self.job_repo.update_job_status(
                        job_id=job_id,
                        status=JobStatusEnum.INDEXING,
                        progress=round(progress_val, 2),
                        message=f"Generando embeddings ({processed} de {total_chunks} fragmentos · {pct}%)...",
                    )

                    time.sleep(0.15)  # Pace batch requests smoothly

                    release_memory()

                logger.info(
                    "[IngestDocumentUseCase:execute_async] embeddings_complete "
                    f"job_id={job_id} document_id={document_id} chunks={total_chunks} "
                    f"duration_ms={int((time.monotonic() - embeddings_started) * 1000)} "
                    f"peak_rss_mb={_process_memory_mb()}"
                )

                if self._is_cancelled(job_id):
                    logger.info(
                        f"[IngestDocumentUseCase:execute_async] Job {job_id} cancelled before indexing."
                    )

                    self._cleanup_failed_ingestion(document_id)

                    return

                # Step 3: Indexing in Vector Store (Qdrant + BM25)

                # Purpose: Report indexing progress.

                # Inputs: fraction, detail.

                # Output: None.

                def report_indexing_progress(fraction: float, detail: str) -> None:
                    """Report indexing progress.

                    Args:

                        fraction: float, detail: str.

                    Returns:

                        None..

                    """

                    progress = 0.70 + 0.28 * max(0.0, min(1.0, fraction))

                    self.job_repo.update_job_status(
                        job_id=job_id,
                        status=JobStatusEnum.INDEXING,
                        progress=round(progress, 2),
                        message=detail,
                    )

                report_indexing_progress(0.0, "Preparando índices de búsqueda...")

                indexing_started = time.monotonic()

                indexed_count = self.vector_store.index_chunks(
                    chunks,
                    progress_callback=report_indexing_progress,
                )

                logger.info(
                    "[IngestDocumentUseCase:execute_async] indexing_complete "
                    f"job_id={job_id} document_id={document_id} chunks={indexed_count} "
                    f"duration_ms={int((time.monotonic() - indexing_started) * 1000)} "
                    f"peak_rss_mb={_process_memory_mb()}"
                )

                # Free chunks and images from worker scope and force GC

                del chunks

                del images

                release_memory()

                # Step 4: Completion

                msg = (
                    f"¡Documento listo! {indexed_count} fragmentos preparados con un método alternativo."
                    if incremental_state.get("degraded")
                    else f"¡Documento listo! {indexed_count} fragmentos preparados para consulta."
                )

                self.job_repo.update_job_status(
                    job_id=job_id,
                    status=JobStatusEnum.COMPLETED,
                    progress=1.0,
                    message=msg,
                )

                self._cleanup_local_cache(document_id)

                logger.info(
                    "[IngestDocumentUseCase:execute_async] ingestion_complete "
                    f"job_id={job_id} document_id={document_id} "
                    f"duration_ms={int((time.monotonic() - ingestion_started) * 1000)} "
                    f"peak_rss_mb={_process_memory_mb()}"
                )

            except JobCancelledError:
                logger.info(
                    f"[IngestDocumentUseCase:execute_async] Job {job_id} was cancelled by user."
                )

                self._cleanup_failed_ingestion(document_id)

                return

            except Exception as exc:
                err_raw = str(exc)

                logger.error(
                    f"[IngestDocumentUseCase:execute_async] Error executing ingestion job {job_id}: {err_raw}",
                    exc_info=True,
                )

                # Map technical errors to user-friendly Spanish explanations

                err_lower = err_raw.lower()

                if (
                    "429" in err_lower
                    or "resource_exhausted" in err_lower
                    or "quota" in err_lower
                ):
                    user_msg = "El servicio de IA ha alcanzado temporalmente su límite de solicitudes por minuto. Por favor espera unos momentos y vuelve a intentarlo."

                elif "timeout" in err_lower or "timed out" in err_lower:
                    user_msg = "El tiempo de respuesta del servicio de IA se agotó. Por favor intenta nuevamente."

                elif "connection" in err_lower or "api_connection" in err_lower:
                    user_msg = "No se pudo completar una parte del procesamiento. Intenta nuevamente."

                elif (
                    "unauthenticated" in err_lower
                    or "invalid_api_key" in err_lower
                    or "api_key" in err_lower
                ):
                    user_msg = "La clave de acceso del proveedor de IA no es válida o ha expirado."

                else:
                    user_msg = "Ocurrió un error al procesar el archivo. El reporte técnico quedó registrado en el servidor."

                self.job_repo.update_job_status(
                    job_id=job_id,
                    status=JobStatusEnum.FAILED,
                    progress=1.0,
                    message=user_msg,
                    error=user_msg,
                )

                self._cleanup_failed_ingestion(document_id)
