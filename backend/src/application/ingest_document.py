import gc
import logging
import re
import resource
import threading
import time
from src.infrastructure.config import settings
from src.domain.models import JobStatusEnum
from src.ports.document_parser_port import DocumentParserPort
from src.ports.job_repository_port import JobRepositoryPort
from src.ports.llm_port import LLMPort
from src.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)

# Serialize background ingestion tasks to protect instances with tight RAM limits (e.g. Render 512MB)
_INGESTION_SEMAPHORE = threading.Semaphore(1)


def _process_memory_mb() -> int:
    """Return the worker's peak resident memory when the platform exposes it."""
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(usage / 1024) if usage > 1024 else int(usage)


class IngestDocumentUseCase:
    def __init__(
        self,
        parser: DocumentParserPort,
        vector_store: VectorStorePort,
        llm: LLMPort,
        job_repo: JobRepositoryPort,
    ):
        self.parser = parser
        self.vector_store = vector_store
        self.llm = llm
        self.job_repo = job_repo

    def _is_cancelled(self, job_id: str) -> bool:
        """Checks if the user requested cancellation of this job."""
        job = self.job_repo.get_job(job_id)
        return job is not None and job.status == JobStatusEnum.CANCELLED

    def _is_quota_error(self, exc: Exception) -> bool:
        """Detects rate limits, quota exhaustion or 429 from LLM providers."""
        err = str(exc).lower()
        return any(
            k in err
            for k in [
                "429",
                "resource_exhausted",
                "quota",
                "rate limit",
                "rate_limit",
                "too many requests",
            ]
        )

    def _extract_retry_delay(self, exc: Exception, default_seconds: int = 40) -> int:
        """Parses the recommended retry delay from error messages if present."""
        match = re.search(
            r"retry(?:\s+in\s+|Delay['\":\s]+)(\d+(?:\.\d+)?)",
            str(exc),
            re.IGNORECASE,
        )
        if match:
            try:
                return max(10, int(float(match.group(1))) + 3)
            except Exception:
                pass
        return default_seconds

    def _wait_for_quota_recovery(self, job_id: str, wait_seconds: int, progress: float) -> bool:
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
                message=f"Límite de cuota alcanzado. Esperando restablecimiento para continuar ({remaining}s restantes)...",
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

    def execute_async(self, job_id: str, file_path: str, document_id: str) -> None:
        """
        Background worker method for processing PDF ingestion.
        Guarantees updating job status on every stage and handling failures gracefully.
        Serializes execution with _INGESTION_SEMAPHORE to prevent concurrent RAM spikes.
        """
        if self._is_cancelled(job_id):
            logger.info(f"[IngestDocumentUseCase:execute_async] Job {job_id} was cancelled before starting.")
            return

        with _INGESTION_SEMAPHORE:
            try:
                if self._is_cancelled(job_id):
                    logger.info(f"[IngestDocumentUseCase:execute_async] Job {job_id} was cancelled before acquisition.")
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
                def report_extraction_progress(fraction: float, detail: str) -> None:
                    progress = 0.05 + 0.25 * max(0.0, min(1.0, fraction))
                    self.job_repo.update_job_status(
                        job_id=job_id,
                        status=JobStatusEnum.EXTRACTING,
                        progress=round(progress, 2),
                        message=detail,
                    )

                chunks, images = self.parser.parse_pdf(
                    file_path=file_path,
                    document_id=document_id,
                    progress_callback=report_extraction_progress,
                )
                logger.info(
                    "[IngestDocumentUseCase:execute_async] extraction_complete "
                    f"job_id={job_id} document_id={document_id} chunks={len(chunks)} "
                    f"images={len(images)} duration_ms={int((time.monotonic() - ingestion_started) * 1000)} "
                    f"peak_rss_mb={_process_memory_mb()}"
                )

                if self._is_cancelled(job_id):
                    logger.info(f"[IngestDocumentUseCase:execute_async] Job {job_id} was cancelled after extraction.")
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

                # Ensure document_name and created_at are populated across all chunks
                job_obj = self.job_repo.get_job(job_id)
                doc_name = job_obj.filename if job_obj else document_id
                created_at_iso = (
                    job_obj.created_at.isoformat()
                    if job_obj and hasattr(job_obj, "created_at")
                    else None
                )
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
                        logger.info(f"[IngestDocumentUseCase:execute_async] Job {job_id} cancelled during batch {i}.")
                        return

                    batch_chunks = chunks[i : i + batch_size]
                    batch_texts = [c.text for c in batch_chunks]
                    batch_embeddings = None
                    max_quota_retries = 6
                    quota_attempts = 0

                    while batch_embeddings is None:
                        try:
                            batch_embeddings = self.llm.generate_embeddings(batch_texts)
                        except Exception as batch_err:
                            if self._is_quota_error(batch_err) and quota_attempts < max_quota_retries:
                                quota_attempts += 1
                                delay = self._extract_retry_delay(batch_err, default_seconds=38)
                                logger.warning(
                                    f"[IngestDocumentUseCase:execute_async] Job {job_id}: Quota limit encountered on batch {i} "
                                    f"(attempt {quota_attempts}/{max_quota_retries}). Waiting {delay}s for quota window reset."
                                )
                                ratio = i / total_chunks
                                cur_prog = round(0.35 + 0.35 * ratio, 2)
                                can_continue = self._wait_for_quota_recovery(job_id, delay, cur_prog)
                                if not can_continue:
                                    logger.info(f"[IngestDocumentUseCase:execute_async] Job {job_id} cancelled while waiting for quota.")
                                    return
                                continue
                            raise

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

                logger.info(
                    "[IngestDocumentUseCase:execute_async] embeddings_complete "
                    f"job_id={job_id} document_id={document_id} chunks={total_chunks} "
                    f"duration_ms={int((time.monotonic() - embeddings_started) * 1000)} "
                    f"peak_rss_mb={_process_memory_mb()}"
                )

                if self._is_cancelled(job_id):
                    logger.info(f"[IngestDocumentUseCase:execute_async] Job {job_id} cancelled before indexing.")
                    return

                # Step 3: Indexing in Vector Store (Qdrant + BM25)
                def report_indexing_progress(fraction: float, detail: str) -> None:
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
                gc.collect()

                # Step 4: Completion
                self.job_repo.update_job_status(
                    job_id=job_id,
                    status=JobStatusEnum.COMPLETED,
                    progress=1.0,
                    message=f"¡Documento listo! {indexed_count} fragmentos preparados para consulta.",
                )
                logger.info(
                    "[IngestDocumentUseCase:execute_async] ingestion_complete "
                    f"job_id={job_id} document_id={document_id} "
                    f"duration_ms={int((time.monotonic() - ingestion_started) * 1000)} "
                    f"peak_rss_mb={_process_memory_mb()}"
                )

            except Exception as exc:
                err_raw = str(exc)
                logger.error(
                    f"[IngestDocumentUseCase:execute_async] Error executing ingestion job {job_id}: {err_raw}",
                    exc_info=True,
                )

                # Map technical errors to user-friendly Spanish explanations
                err_lower = err_raw.lower()
                if "429" in err_lower or "resource_exhausted" in err_lower or "quota" in err_lower:
                    user_msg = "El servicio de IA ha alcanzado temporalmente su límite de solicitudes por minuto. Por favor espera unos momentos y vuelve a intentarlo."
                elif "timeout" in err_lower or "timed out" in err_lower:
                    user_msg = "El tiempo de respuesta del servicio de IA se agotó. Por favor intenta nuevamente."
                elif "connection" in err_lower or "api_connection" in err_lower:
                    user_msg = "No se pudo conectar con el servicio de IA. Verifica tu conexión a internet o el estado del proveedor."
                elif "unauthenticated" in err_lower or "invalid_api_key" in err_lower or "api_key" in err_lower:
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
