import logging
import os
import time
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from src.adapters.storage.local_storage import (
    StorageCapacityExceededError,
    UploadSizeExceededError,
)
from src.domain.exceptions import JobNotFoundError
from src.domain.models import IngestionJob, JobStatusEnum
from src.infrastructure.container import Container, get_container
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Documents & Ingestion"])

MAX_FILE_SIZE = settings.max_upload_size_bytes


class UploadResponse(BaseModel):
    job_id: str
    document_id: str
    filename: str
    message: str


@router.post(
    "/documents/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload technical PDF for asynchronous ingestion",
)
async def upload_document(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    app_container: Container = Depends(get_container),
):
    filename = os.path.basename(file.filename or "")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se admiten documentos en formato PDF.",
        )

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_FILE_SIZE + 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=(
                        f"El archivo excede el tamaño máximo permitido de "
                        f"{MAX_FILE_SIZE // (1024 * 1024)} MB para este despliegue."
                    ),
                )
        except ValueError:
            logger.warning(
                "[DocumentsRoute:upload_document] Ignoring invalid Content-Length header."
            )

    # Validate PDF signature from header (first 1024 bytes) without loading entire 50MB into RAM
    header = await file.read(1024)
    if not header.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo proporcionado no tiene una estructura PDF válida.",
        )
    await file.seek(0)

    # 1. Stream upload directly to disk asynchronously using await file.read()
    # This prevents blocking the asyncio event loop or deadlocking with the client on cloud proxies like Render
    document_id = str(uuid.uuid4())
    total_bytes = 0
    upload_started = time.monotonic()
    try:
        await file.seek(0)
        document_id = str(uuid.uuid4())
        safe_filename = f"{document_id}_{filename}"
        dest_path = app_container.storage.save_upload(safe_filename, file.file)
        total_bytes = os.path.getsize(dest_path)
    except UploadSizeExceededError:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo excede el tamaño máximo permitido de {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        ) from None
    except StorageCapacityExceededError:
        try:
            app_container.storage.delete_document_files(document_id)
        except Exception:
            logger.exception("[DocumentsRoute:upload_document] Storage cleanup failed after capacity rejection.")
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="El almacenamiento local no tiene espacio suficiente para conservar este archivo.",
        ) from None
    except Exception as exc:
        logger.error("[DocumentsRoute:upload_document] Could not persist uploaded file.", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible guardar el archivo en el almacenamiento del servidor.",
        ) from exc

    try:
        job = app_container.job_repo.create_job(
            document_id=document_id,
            filename=filename,
        )
    except Exception as exc:
        logger.error(
            "[DocumentsRoute:upload_document] Job creation failed; cleaning uploaded artifacts.",
            exc_info=True,
        )
        try:
            app_container.storage.delete_document_files(document_id)
        except Exception:
            logger.exception(
                "[DocumentsRoute:upload_document] Failed to clean upload after job creation failure."
            )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible registrar el procesamiento. El archivo no fue conservado.",
        ) from exc

    logger.info(
        "[DocumentsRoute:upload_document] upload_complete "
        f"job_id={job.job_id} document_id={document_id} filename={filename!r} "
        f"bytes={total_bytes} duration_ms={int((time.monotonic() - upload_started) * 1000)}"
    )

    # 2. Queue asynchronous background processing
    background_tasks.add_task(
        app_container.ingest_use_case.execute_async,
        job_id=job.job_id,
        file_path=dest_path,
        document_id=document_id,
    )

    return UploadResponse(
        job_id=job.job_id,
        document_id=job.document_id,
        filename=filename,
        message="Archivo recibido. Ingesta asíncrona iniciada.",
    )


@router.get(
    "/jobs/{job_id}",
    response_model=IngestionJob,
    summary="Poll status and progress of an ingestion job",
)
def get_job_status(
    job_id: str,
    app_container: Container = Depends(get_container),
):
    try:
        return app_container.get_job_use_case.execute(job_id)
    except JobNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/jobs/{job_id}/cancel",
    summary="Cancel an ongoing ingestion job and delete any associated files and vectors",
)
@router.delete(
    "/jobs/{job_id}",
    summary="Cancel an ongoing ingestion job and delete any associated files and vectors",
)
def cancel_job(
    job_id: str,
    app_container: Container = Depends(get_container),
):
    try:
        job = app_container.get_job_use_case.execute(job_id)
    except JobNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trabajo no encontrado")

    # 1. Mark job as CANCELLED in repository so background worker halts immediately
    app_container.job_repo.update_job_status(
        job_id=job_id,
        status=JobStatusEnum.CANCELLED,
        progress=1.0,
        message="Carga y procesamiento cancelados por el usuario.",
    )

    # 2. Cascade delete document files and any indexed vectors
    if job.document_id:
        try:
            app_container.delete_use_case.execute(job.document_id)
            logger.info(f"[cancel_job] Purged document data for document_id '{job.document_id}'")
        except Exception as e:
            logger.warning(f"[cancel_job] Failed to purge partial data for document_id '{job.document_id}': {e}")

    return {
        "status": "success",
        "message": "Trabajo de procesamiento detenido y eliminado correctamente.",
        "job_id": job_id,
    }


@router.get(
    "/images/{document_id}/{filename}",
    summary="Serve extracted multimodal diagrams and images",
)
def get_extracted_image(
    document_id: str,
    filename: str,
    app_container: Container = Depends(get_container),
):
    image_path = app_container.storage.get_image_path(document_id, filename)
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imagen no encontrada")
    return FileResponse(image_path)


@router.get(
    "/documents",
    summary="List all indexed documents in the vector store",
)
def list_documents(app_container: Container = Depends(get_container)):
    try:
        # 1. Documents in storage on disk
        storage_docs = (
            app_container.storage.list_uploaded_documents()
            if hasattr(app_container.storage, "list_uploaded_documents")
            else []
        )
        docs_map = {d["id"]: d for d in storage_docs}

        # 2. Enrich with records from vector store
        vector_docs = app_container.vector_store.list_documents()
        for vd in vector_docs:
            did = vd.get("id")
            if not did:
                continue
            if did in docs_map:
                vname = vd.get("name")
                if vname and vname != did:
                    docs_map[did]["name"] = vname
                if vd.get("created_at"):
                    docs_map[did]["created_at"] = vd["created_at"]
            else:
                docs_map[did] = vd

        return list(docs_map.values())
    except Exception as e:
        logger.error(f"[DocumentsRoute:list_documents] Error listing documents: {e}", exc_info=True)
        return []


@router.delete(
    "/documents/{document_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a document and all related vectors, images, and files from DB and disk",
)
def delete_document(
    document_id: str,
    app_container: Container = Depends(get_container),
):
    try:
        deleted_chunks = app_container.delete_use_case.execute(document_id)
        return {
            "status": "success",
            "message": f"Documento '{document_id}' eliminado de la base de datos.",
            "deleted_chunks": deleted_chunks,
        }
    except Exception as e:
        logger.error(f"[DocumentsRoute:delete_document] Error deleting document '{document_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible eliminar el documento debido a un error interno del servidor.",
        )
