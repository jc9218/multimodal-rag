import json
import logging
from typing import Dict, List, Optional
import redis
from src.domain.exceptions import JobNotFoundError
from src.domain.models import IngestionJob, JobStatusEnum
from src.ports.job_repository_port import JobRepositoryPort

logger = logging.getLogger(__name__)


# Clase: RedisJobRepository.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class RedisJobRepository(JobRepositoryPort):
    """
    Persistent Job Repository backed by Redis.
    Guarantees job persistence across server restarts and horizontal scaling.
    Falls back to in-memory dictionary if Redis is unreachable (e.g. in standalone unit tests).
    """

    # Objetivo: Init.
    # Entradas: self, redis_url, ttl_seconds.
    # Salida: Resultado de la operación o None si no retorna un valor..
    def __init__(self, redis_url: str = "redis://localhost:6379/0", ttl_seconds: int = 86400):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._memory_fallback: Dict[str, IngestionJob] = {}
        self._redis_client: Optional[redis.Redis] = None

        try:
            client = redis.from_url(redis_url, decode_responses=True, socket_timeout=2.0)
            client.ping()
            self._redis_client = client
            logger.info(f"Connected to Redis at {redis_url} for persistent ingestion jobs.")
        except Exception as e:
            logger.warning(
                f"Could not connect to Redis at {redis_url} ({e}). Using in-memory fallback for jobs."
            )
            self._redis_client = None

    # Objetivo: Job key.
    # Entradas: self, job_id.
    # Salida: str.
    def _job_key(self, job_id: str) -> str:
        return f"multimodal_rag:job:{job_id}"

    # Objetivo: Is persistent.
    # Entradas: self.
    # Salida: bool.
    @property
    def is_persistent(self) -> bool:
        return self._redis_client is not None

    # Objetivo: Create job.
    # Entradas: self, document_id, filename.
    # Salida: IngestionJob.
    def create_job(
        self, document_id: str, filename: str, upload_id: Optional[str] = None
    ) -> IngestionJob:
        import uuid
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        job = IngestionJob(
            job_id=job_id,
            document_id=document_id,
            filename=filename,
            upload_id=upload_id,
            status=JobStatusEnum.PENDING,
            progress=0.0,
            message="Documento en cola para procesamiento...",
        )

        if self._redis_client:
            try:
                key = self._job_key(job_id)
                self._redis_client.set(key, job.model_dump_json(), ex=self.ttl_seconds)
                if upload_id:
                    self._redis_client.set(
                        self._upload_key(upload_id), job_id, ex=self.ttl_seconds
                    )
                return job
            except Exception as e:
                logger.error(f"Redis error creating job {job_id}: {e}")

        self._memory_fallback[job_id] = job
        return job

    def _upload_key(self, upload_id: str) -> str:
        return f"multimodal_rag:upload:{upload_id}"

    def get_job_by_upload_id(self, upload_id: str) -> Optional[IngestionJob]:
        if self._redis_client:
            try:
                job_id = self._redis_client.get(self._upload_key(upload_id))
                if job_id:
                    return self.get_job(job_id)
            except Exception as e:
                logger.error(f"Redis error getting upload id {upload_id}: {e}")
        return next(
            (job for job in self._memory_fallback.values() if job.upload_id == upload_id),
            None,
        )

    # Objetivo: Get job.
    # Entradas: self, job_id.
    # Salida: IngestionJob.
    def get_job(self, job_id: str) -> IngestionJob:
        if self._redis_client:
            try:
                data = self._redis_client.get(self._job_key(job_id))
                if data:
                    return IngestionJob(**json.loads(data))
            except Exception as e:
                logger.error(f"Redis error getting job {job_id}: {e}")

        if job_id in self._memory_fallback:
            return self._memory_fallback[job_id]

        raise JobNotFoundError(f"Job '{job_id}' not found.")

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
        from datetime import datetime, timezone

        job = self.get_job(job_id)
        job.status = status
        job.progress = max(0.0, min(1.0, progress))
        job.message = message
        job.error = error
        job.updated_at = datetime.now(timezone.utc)

        if self._redis_client:
            try:
                key = self._job_key(job_id)
                self._redis_client.set(key, job.model_dump_json(), ex=self.ttl_seconds)
                return job
            except Exception as e:
                logger.error(f"Redis error updating job {job_id}: {e}")

        self._memory_fallback[job_id] = job
        return job

    # Objetivo: List jobs.
    # Entradas: self.
    # Salida: List[IngestionJob].
    def list_jobs(self) -> List[IngestionJob]:
        jobs = []
        if self._redis_client:
            try:
                keys = self._redis_client.keys("multimodal_rag:job:*")
                for k in keys:
                    data = self._redis_client.get(k)
                    if data:
                        jobs.append(IngestionJob(**json.loads(data)))
                return jobs
            except Exception as e:
                logger.error(f"Redis error listing jobs: {e}")

        return list(self._memory_fallback.values())
