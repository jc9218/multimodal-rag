import threading
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid
from src.domain.models import IngestionJob, JobStatusEnum
from src.ports.job_repository_port import JobRepositoryPort


# Clase: MemoryJobRepository.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class MemoryJobRepository(JobRepositoryPort):
    # Objetivo: Init.
    # Entradas: self.
    # Salida: Resultado de la operación o None si no retorna un valor..
    def __init__(self):
        self._jobs: Dict[str, IngestionJob] = {}
        self._lock = threading.Lock()

    # Objetivo: Create job.
    # Entradas: self, document_id, filename.
    # Salida: IngestionJob.
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

    # Objetivo: Get job.
    # Entradas: self, job_id.
    # Salida: Optional[IngestionJob].
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        with self._lock:
            return self._jobs.get(job_id)

    # Objetivo: Update job status.
    # Entradas: self, job_id, status, progress, message, error.
    # Salida: IngestionJob.
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

    # Objetivo: List jobs.
    # Entradas: self.
    # Salida: Resultado de la operación o None si no retorna un valor..
    def list_jobs(self):
        with self._lock:
            return list(self._jobs.values())
