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
from src.adapters.storage.supabase_storage import SupabaseStorageError
from src.domain.exceptions import JobNotFoundError
from src.domain.models import IngestionJob, JobStatusEnum
from src.infrastructure.container import Container, get_container
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Documents & Ingestion"])

MAX_FILE_SIZE = settings.max_upload_size_bytes


# Clase: UploadResponse.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class UploadResponse(BaseModel):
    job_id: str
    document_id: str
    filename: str
    message: str


# Objetivo: Upload document.
# Entradas: background_tasks, request, file, app_container.
# Salida: Resultado de la operación o None si no retorna un valor..
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
    upload_id = request.headers.get("X-Upload-Id", "").strip()
    if upload_id:
        existing_job = app_container.job_repo.get_job_by_upload_id(upload_id)
        if existing_job:
            return UploadResponse(
                job_id=existing_job.job_id,
                document_id=existing_job.document_id,
                filename=existing_job.filename,
                message="La subida ya estaba registrada; se reutiliza el procesamiento existente.",
            )

    filename = os.path.basename(file.filename or "")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo no es válido. Selecciona un documento PDF.",
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
            detail="El archivo no se puede leer. Selecciona otro documento PDF.",
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
        try:
            app_container.storage.delete_document_files(document_id)
        except Exception:
            logger.exception(
                "[DocumentsRoute:upload_document] Failed to clean storage after upload size rejection."
            )
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite permitido de {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        ) from None
    except StorageCapacityExceededError:
        try:
            app_container.storage.delete_document_files(document_id)
        except Exception:
            logger.exception("[DocumentsRoute:upload_document] Storage cleanup failed after capacity rejection.")
        raise HTTPException(
            status_code=status.HTTP_507_INSUFFICIENT_STORAGE,
            detail="No hay espacio suficiente para guardar el archivo. Intenta con otro archivo.",
        ) from None
    except SupabaseStorageError as exc:
        logger.error(
            "[DocumentsRoute:upload_document] Supabase rejected uploaded file.",
            exc_info=True,
        )
        try:
            app_container.storage.delete_document_files(document_id)
        except Exception:
            logger.exception(
                "[DocumentsRoute:upload_document] Failed to clean storage after Supabase rejection."
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "No se pudo subir el archivo al almacenamiento. "
                "El archivo no fue conservado; intenta nuevamente."
            ),
        ) from exc
    except Exception as exc:
        logger.error("[DocumentsRoute:upload_document] Could not persist uploaded file.", exc_info=True)
        try:
            app_container.storage.delete_document_files(document_id)
        except Exception:
            logger.exception(
                "[DocumentsRoute:upload_document] Failed to clean storage after upload failure."
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo guardar el archivo. Intenta nuevamente.",
        ) from exc

    try:
        job = app_container.job_repo.create_job(
            document_id=document_id,
            filename=filename,
            upload_id=upload_id or None,
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


# Objetivo: Get job status.
# Entradas: job_id, app_container.
# Salida: Resultado de la operación o None si no retorna un valor..
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el archivo solicitado.")


# Objetivo: Cancel job.
# Entradas: job_id, app_container.
# Salida: Resultado de la operación o None si no retorna un valor..
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No se encontró el procesamiento solicitado.")

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


# Objetivo: Get extracted image.
# Entradas: document_id, filename, app_container.
# Salida: Resultado de la operación o None si no retorna un valor..
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,         detail="No se encontró la imagen solicitada.")
    return FileResponse(image_path)


# Objetivo: List documents.
# Entradas: app_container.
# Salida: Resultado de la operación o None si no retorna un valor..
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


# Objetivo: Delete document.
# Entradas: document_id, app_container.
# Salida: Resultado de la operación o None si no retorna un valor..
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
            detail="No se pudo eliminar el archivo. Intenta nuevamente.",
        )
