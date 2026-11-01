import logging
import uuid
from typing import BinaryIO, Tuple, Union
from src.domain.models import IngestionJob
from src.ports.job_repository_port import JobRepositoryPort
from src.ports.storage_port import StoragePort

logger = logging.getLogger(__name__)


# Class: UploadDocumentUseCase.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class UploadDocumentUseCase:
    """Encapsulates document upload handling and job registration."""

    # Purpose: Init.
    # Inputs: self, storage, job_repo.
    # Output: Operation result, or None when no value is returned.
    def __init__(self, storage: StoragePort, job_repo: JobRepositoryPort):
        self.storage = storage
        self.job_repo = job_repo

    # Purpose: Execute.
    # Inputs: self, filename, content.
    # Output: Tuple[IngestionJob, str].
    def execute(self, filename: str, content: Union[bytes, BinaryIO]) -> Tuple[IngestionJob, str]:
        document_id = str(uuid.uuid4())
        safe_filename = f"{document_id}_{filename}"

        file_path = self.storage.save_upload(
            filename=safe_filename,
            content=content,
        )

        job = self.job_repo.create_job(
            document_id=document_id,
            filename=filename,
        )

        logger.info(
            f"[UploadDocumentUseCase:execute] Saved upload '{filename}' to '{file_path}', created job {job.job_id}"
        )
        return job, file_path
