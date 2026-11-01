from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models import IngestionJob, JobStatusEnum


# Class: JobRepositoryPort.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class JobRepositoryPort(ABC):
    # Purpose: Create job.
    # Inputs: self, document_id, filename.
    # Output: IngestionJob.
    @abstractmethod
    def create_job(
        self, document_id: str, filename: str, upload_id: Optional[str] = None
    ) -> IngestionJob:
        pass

    @abstractmethod
    def get_job_by_upload_id(self, upload_id: str) -> Optional[IngestionJob]:
        pass

    # Purpose: Get job.
    # Inputs: self, job_id.
    # Output: Optional[IngestionJob].
    @abstractmethod
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        pass

    @abstractmethod
    def list_jobs(self) -> List[IngestionJob]:
        """Lists persisted jobs so interrupted work can be recovered after restart."""
        pass

    # Purpose: Update job status.
    # Inputs: self, job_id, status, progress, message, error.
    # Output: IngestionJob.
    @abstractmethod
    def update_job_status(
        self,
        job_id: str,
        status: JobStatusEnum,
        progress: float,
        message: str,
        error: Optional[str] = None,
    ) -> IngestionJob:
        pass
