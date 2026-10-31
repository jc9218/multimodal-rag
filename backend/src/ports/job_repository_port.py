from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.models import IngestionJob, JobStatusEnum


class JobRepositoryPort(ABC):
    @abstractmethod
    def create_job(self, document_id: str, filename: str) -> IngestionJob:
        pass

    @abstractmethod
    def get_job(self, job_id: str) -> Optional[IngestionJob]:
        pass

    @abstractmethod
    def list_jobs(self) -> List[IngestionJob]:
        """Lists persisted jobs so interrupted work can be recovered after restart."""
        pass

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
