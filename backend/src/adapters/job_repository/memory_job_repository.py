import threading
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid
from src.domain.models import IngestionJob, JobStatusEnum
from src.ports.job_repository_port import JobRepositoryPort


class MemoryJobRepository(JobRepositoryPort):
    def __init__(self):
        self._jobs: Dict[str, IngestionJob] = {}
        self._lock = threading.Lock()

    def create_job(self, document_id: str, filename: str) -> IngestionJob:
        job_id = str(uuid.uuid4())
        job = IngestionJob(
            job_id=job_id,
            document_id=document_id,
            filename=filename,
            status=JobStatusEnum.PENDING,
            progress=0.0,
            message="Documento en cola para procesamiento...",
        )
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        with self._lock:
            return self._jobs.get(job_id)

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

    def list_jobs(self):
        with self._lock:
            return list(self._jobs.values())
