import json
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


# Clase: Settings.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Vector DB (Generic Provider: qdrant)
    VECTOR_STORE_PROVIDER: str = "qdrant"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION_NAME: str = "technical_documents"

    # LLM & Embeddings (Loaded strictly from .env / environment variables)
    LLM_PROVIDER: str
    LLM_PROVIDER_API_KEY: str = ""
    LLM_BASE_URL: str = ""  # e.g. http://localhost:11434 for Ollama or custom local model

    LLM_MODEL: str
    EMBEDDING_MODEL: str
    EMBEDDING_DIMENSION: int
    LLM_MAX_CONTEXT_CHARS: int = 12000
    LLM_MAX_HISTORY_CHARS: int = 2400
    LLM_MAX_OUTPUT_TOKENS: int = 512
    LLM_THINKING_BUDGET: int = 0
    OCR_DPI: int = 96
    MAX_EXTRACTED_IMAGE_MB: int = 2
    MAX_IMAGES_PER_DOCUMENT: int = 80
    # Free Render instances and low-quota models need a conservative upload
    # limit to avoid exhausting web-process memory during PDF parsing.
    RESOURCE_PROFILE: str = "free"
    MAX_UPLOAD_SIZE_MB: int = 10
    EMBEDDING_BATCH_SIZE: int = 24
    QDRANT_UPSERT_BATCH_SIZE: int = 6
    BM25_MAX_CHUNKS_IN_MEMORY: int = 800
    RECOVER_INTERRUPTED_JOBS: bool = True

    # Storage & Cache (Auxiliary Services)
    STORAGE_PATH: str = "./storage"
    STORAGE_PROVIDER: str = "local"
    MAX_LOCAL_STORAGE_MB: int = 400
    MIN_FREE_STORAGE_MB: int = 64
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "documents"
    REDIS_URL: str = "redis://redis:6379/0"

    # CORS
    CORS_ORIGINS: str = '["http://localhost:3000", "http://127.0.0.1:3000", "https://*.vercel.app"]'

    @property
    def api_key(self) -> str:
        """Returns LLM_PROVIDER_API_KEY configured for the active LLM provider."""
        return self.LLM_PROVIDER_API_KEY

    # Objetivo: Cors origins list.
    # Entradas: self.
    # Salida: List[str].
    @property
    def cors_origins_list(self) -> List[str]:
        raw = self.CORS_ORIGINS.strip()
        if raw.startswith("["):
            try:
                return json.loads(raw)
            except Exception:
                pass
        if "," in raw:
            return [origin.strip() for origin in raw.split(",") if origin.strip()]
        if raw:
            return [raw]
        return ["*"]

    # Objetivo: Max upload size bytes.
    # Entradas: self.
    # Salida: int.
    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
