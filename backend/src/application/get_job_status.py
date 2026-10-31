from typing import Optional
from src.domain.exceptions import JobNotFoundError
from src.domain.models import IngestionJob
from src.ports.job_repository_port import JobRepositoryPort


# Clase: GetJobStatusUseCase.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class GetJobStatusUseCase:
    # Objetivo: Init.
    # Entradas: self, job_repo.
    # Salida: Resultado de la operación o None si no retorna un valor..
    def __init__(self, job_repo: JobRepositoryPort):
        self.job_repo = job_repo

    # Objetivo: Execute.
    # Entradas: self, job_id.
    # Salida: IngestionJob.
    def execute(self, job_id: str) -> IngestionJob:
        job = self.job_repo.get_job(job_id)
        if not job:
            raise JobNotFoundError(f"Job with ID '{job_id}' not found.")
        return job
