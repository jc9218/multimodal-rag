import logging

import os

import threading

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse

from src.api.routes.chat import router as chat_router

from src.api.routes.documents import router as documents_router

from src.infrastructure.config import settings

# Enriched log format including module, function name, and line number for rapid debugging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s:%(funcName)s:%(lineno)d] %(message)s",
)

logger = logging.getLogger("multimodal-rag")

# Purpose: Recover interrupted jobs.

# Inputs: None.

# Output: None.


def _recover_interrupted_jobs() -> None:
    """recover interrupted jobs.

    Args:

        None.

    Returns:

        None..

    """

    from src.infrastructure.container import get_container

    from src.domain.models import JobStatusEnum

    app_container = get_container()

    logger.info(
        "[startup] Job recovery storage_path=%s uploads_dir=%s",
        app_container.storage.base_path,
        app_container.storage.uploads_dir,
    )

    recoverable_statuses = {
        JobStatusEnum.PENDING,
        JobStatusEnum.EXTRACTING,
        JobStatusEnum.INDEXING,
        JobStatusEnum.WAITING_QUOTA,
    }

    try:
        jobs = app_container.job_repo.list_jobs()

    except Exception:
        logger.exception(
            "[startup] Could not list persisted ingestion jobs for recovery."
        )

        return

    def _run_sequential_recovery() -> None:
        """run sequential recovery.

        Args:

            None.

        Returns:

            None..

        """

        import time

        time.sleep(3)  # Allow FastAPI to initialize and serve initial health probes

        for job in jobs:
            if job.status not in recoverable_statuses:
                continue

            file_path = app_container.storage.get_upload_path(
                job.document_id, job.filename
            )

            if not file_path:
                logger.error(
                    "[startup] Cannot recover job: upload is missing "
                    f"job_id={job.job_id} document_id={job.document_id} "
                    f"filename={job.filename!r} uploads_dir={app_container.storage.uploads_dir}"
                )

                app_container.job_repo.update_job_status(
                    job_id=job.job_id,
                    status=JobStatusEnum.FAILED,
                    progress=1.0,
                    message="El procesamiento se interrumpió durante un despliegue y el archivo ya no está disponible.",
                    error="Persisted upload missing during restart recovery.",
                )

                try:
                    app_container.storage.delete_document_files(job.document_id)

                except Exception:
                    logger.exception(
                        "[startup] Failed to purge remote artifacts for unrecoverable job "
                        f"job_id={job.job_id} document_id={job.document_id}"
                    )

                continue

            logger.info(
                "[startup] Recovering interrupted ingestion sequentially "
                f"job_id={job.job_id} document_id={job.document_id}"
            )

            try:
                app_container.ingest_use_case.execute_async(
                    job_id=job.job_id,
                    file_path=file_path,
                    document_id=job.document_id,
                )

            except Exception as e:
                logger.error(f"[startup] Failed recovering job {job.job_id}: {e}")

    threading.Thread(
        target=_run_sequential_recovery,
        daemon=True,
        name="job-recovery-worker",
    ).start()


# Purpose: Lifespan.

# Inputs: _.

# Output: Operation result, or None when no value is returned.


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Lifespan.

    Args:

        _: FastAPI.

    Returns:

        unspecified..

    """

    if settings.RECOVER_INTERRUPTED_JOBS:
        threading.Thread(
            target=_recover_interrupted_jobs,
            daemon=True,
            name="job-recovery",
        ).start()

    yield


app = FastAPI(
    title="Multimodal RAG API",
    version="1.0.0",
    description="Sistema RAG Multimodal con extracción espacial de diagramas y búsqueda híbrida.",
    lifespan=lifespan,
)

# Global exception handler to log any unhandled error with full stack trace and location

# Purpose: Global exception handler.

# Inputs: request, exc.

# Output: Operation result, or None when no value is returned.


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler.

    Args:

        request: Request, exc: Exception.

    Returns:

        unspecified..

    """

    logger.error(
        f"[FastAPI:GlobalHandler] Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True,
    )

    return JSONResponse(
        status_code=500,
        content={"detail": "No se pudo completar la solicitud. Intenta nuevamente."},
    )


# Robust CORS configuration for local development and Vercel domains

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app",  # Matches local dev on any port & all Vercel previews/production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers

app.include_router(documents_router)

app.include_router(chat_router)

# Purpose: Health check.

# Inputs: None.

# Output: Operation result, or None when no value is returned.


@app.get("/health", tags=["Health"])
def health_check():
    """Health check.

    Args:

        None.

    Returns:

        unspecified..

    """

    return {
        "status": "healthy",
        "service": "multimodal-rag-backend",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }


@app.get("/ready", tags=["Health"])
def readiness_check():
    """Reports whether persistent job recovery is available for this instance."""

    app_container = __import__(
        "src.infrastructure.container", fromlist=["container"]
    ).container

    persistent_jobs = getattr(app_container.job_repo, "is_persistent", False)

    storage_path = app_container.storage.base_path

    remote_storage = settings.STORAGE_PROVIDER.lower() == "supabase"

    storage_ready = remote_storage or (
        os.path.isabs(settings.STORAGE_PATH)
        and os.path.isdir(app_container.storage.uploads_dir)
        and os.path.isdir(app_container.storage.images_dir)
        and os.access(app_container.storage.uploads_dir, os.W_OK)
    )

    if settings.ENVIRONMENT == "production" and not persistent_jobs:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": "Persistent Redis job storage is unavailable.",
            },
        )

    if settings.ENVIRONMENT == "production" and not storage_ready:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": (
                    "Persistent storage is unavailable or STORAGE_PATH is not an "
                    "absolute writable mount."
                ),
                "storage_path": storage_path,
                "uploads_dir": app_container.storage.uploads_dir,
            },
        )

    return {
        "status": "ready",
        "persistent_jobs": persistent_jobs,
        "storage_path": storage_path,
        "storage_ready": storage_ready,
    }
