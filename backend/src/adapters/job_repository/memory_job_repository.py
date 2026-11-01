import threading
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid
from src.domain.models import IngestionJob, JobStatusEnum
from src.ports.job_repository_port import JobRepositoryPort


# Class: MemoryJobRepository.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class MemoryJobRepository(JobRepositoryPort):
    # Purpose: Init.
    # Inputs: self.
    # Output: Operation result, or None when no value is returned.
    def __init__(self):
        self._jobs: Dict[str, IngestionJob] = {}
        self._lock = threading.Lock()

    # Purpose: Create job.
    # Inputs: self, document_id, filename.
    # Output: IngestionJob.
    def create_job(
        self, document_id: str, filename: str, upload_id: Optional[str] = None
    ) -> IngestionJob:
        job_id = str(uuid.uuid4())
        job = IngestionJob(
            job_id=job_id,
            document_id=document_id,
            filename=filename,
            upload_id=upload_id,
            status=JobStatusEnum.PENDING,
            progress=0.0,
            message="Documento en cola para procesamiento...",
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get_job_by_upload_id(self, upload_id: str) -> Optional[IngestionJob]:
        with self._lock:
            return next(
                (job for job in self._jobs.values() if job.upload_id == upload_id),
                None,
            )

    # Purpose: Get job.
    # Inputs: self, job_id.
    # Output: Optional[IngestionJob].
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        with self._lock:
            return self._jobs.get(job_id)

    # Purpose: Update job status.
    # Inputs: self, job_id, status, progress, message, error.
    # Output: IngestionJob.
    def update_job_status(
        self,
        job_id: str,
        status: JobStatusEnum,
        progress: float,
        message: str,
        error: Optional[str] = None,
    ) -> IngestionJob:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                raise KeyError(f"Job {job_id} does not exist.")
            job.status = status
            job.progress = progress
            job.message = message
            job.error = error
            job.updated_at = datetime.now(timezone.utc)
            return job

    # Purpose: List jobs.
    # Inputs: self.
    # Output: Operation result, or None when no value is returned.
    def list_jobs(self):
        with self._lock:
            return list(self._jobs.values())
