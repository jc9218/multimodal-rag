from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models import IngestionJob, JobStatusEnum


# Clase: JobRepositoryPort.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class JobRepositoryPort(ABC):
    # Objetivo: Create job.
    # Entradas: self, document_id, filename.
    # Salida: IngestionJob.
    @abstractmethod
    def create_job(self, document_id: str, filename: str) -> IngestionJob:
        pass

    # Objetivo: Get job.
    # Entradas: self, job_id.
    # Salida: Optional[IngestionJob].
    @abstractmethod
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        pass

    @abstractmethod
    def list_jobs(self) -> List[IngestionJob]:
        """Lists persisted jobs so interrupted work can be recovered after restart."""
        pass

    # Objetivo: Update job status.
    # Entradas: self, job_id, status, progress, message, error.
    # Salida: IngestionJob.
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
