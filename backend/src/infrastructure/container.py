import logging
from src.adapters.job_repository.redis_job_repository import RedisJobRepository
from src.adapters.llm.llm_factory import LLMFactory
from src.adapters.parsers.pymupdf_parser import PyMuPDFParser
from src.adapters.storage.local_storage import LocalStorageAdapter
from src.adapters.storage.supabase_storage import SupabaseStorageAdapter
from src.adapters.vector_db.vector_store_factory import VectorStoreFactory
from src.application.delete_document import DeleteDocumentUseCase
from src.application.get_job_status import GetJobStatusUseCase
from src.application.ingest_document import IngestDocumentUseCase
from src.application.query_rag import QueryRAGUseCase
from src.application.upload_document import UploadDocumentUseCase
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)


# Clase: Container.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class Container:
    """
    Dependency Injection Container.
    Composes the system by injecting interfaces (Ports) into Use Cases.
    Supports swapping any LLM (Gemini, OpenAI, Ollama) or Vector Database via Factories.
    """

    # Objetivo: Init.
    # Entradas: self.
    # Salida: Resultado de la operación o None si no retorna un valor..
    def __init__(self):
        logger.info(
            f"Initializing Dependency Injection Container [LLM: {settings.LLM_PROVIDER}, VectorStore: {settings.VECTOR_STORE_PROVIDER}]..."
        )

        # 1. Storage & Job Repository (Persistent Redis with in-memory fallback)
        if settings.STORAGE_PROVIDER.lower() == "supabase":
            self.storage = SupabaseStorageAdapter(
                base_storage_path=settings.STORAGE_PATH,
                supabase_url=settings.SUPABASE_URL,
                service_role_key=settings.SUPABASE_SERVICE_ROLE_KEY,
                bucket=settings.SUPABASE_STORAGE_BUCKET,
            )
        else:
            self.storage = LocalStorageAdapter(base_storage_path=settings.STORAGE_PATH)
        self.job_repo = RedisJobRepository(redis_url=settings.REDIS_URL)

        # 2. Document Parser (Multimodal + Spatial)
        self.parser = PyMuPDFParser(storage=self.storage, ocr_dpi=settings.OCR_DPI)

        # 3. LLM Provider (Injected via Factory: Gemini, OpenAI, Ollama)
        self.llm = LLMFactory.create(settings)

        # 4. Vector Store (Injected via Factory: Qdrant, Chroma)
        self.vector_store = VectorStoreFactory.create(settings)

        # 5. Core Application Use Cases (Guaranteed 100% decoupling from 3rd party providers)
        self.ingest_use_case = IngestDocumentUseCase(
            parser=self.parser,
            vector_store=self.vector_store,
            llm=self.llm,
            job_repo=self.job_repo,
        )

        self.upload_use_case = UploadDocumentUseCase(
            storage=self.storage,
            job_repo=self.job_repo,
        )

        self.delete_use_case = DeleteDocumentUseCase(
            vector_store=self.vector_store,
            storage=self.storage,
        )

        self.query_use_case = QueryRAGUseCase(
            vector_store=self.vector_store,
            llm=self.llm,
        )

        self.get_job_use_case = GetJobStatusUseCase(
            job_repo=self.job_repo,
        )


container = Container()


def get_container() -> Container:
    """FastAPI Dependency Injection provider for Container."""
    return container
