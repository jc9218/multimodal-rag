import logging

from typing import Dict, Type

from src.adapters.vector_db.qdrant_adapter import QdrantAdapter

from src.infrastructure.config import Settings

from src.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)

# Class: VectorStoreFactory.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class VectorStoreFactory:
    """

    Factory for dynamically creating VectorStorePort implementations.

    Allows swapping vector databases (e.g. Qdrant, Chroma, Milvus) via configuration.

    """

    _registry: Dict[str, Type[VectorStorePort]] = {
        "qdrant": QdrantAdapter,
    }

    # Purpose: Register provider.

    # Inputs: cls, name, adapter_cls.

    # Output: None.

    @classmethod
    def register_provider(cls, name: str, adapter_cls: Type[VectorStorePort]) -> None:
        """Register provider.

        Args:

            cls: unspecified, name: str, adapter_cls: Type[VectorStorePort].

        Returns:

            None..

        """

        cls._registry[name.lower()] = adapter_cls

        logger.info(f"Registered custom VectorStore provider: {name}")

    # Purpose: Create.

    # Inputs: cls, settings.

    # Output: VectorStorePort.

    @classmethod
    def create(cls, settings: Settings) -> VectorStorePort:
        """Create.

        Args:

            cls: unspecified, settings: Settings.

        Returns:

            VectorStorePort..

        """

        provider = settings.VECTOR_STORE_PROVIDER.lower().strip()

        logger.info(
            f"VectorStoreFactory: Creating adapter for provider '{provider}'..."
        )

        if provider == "qdrant":
            return QdrantAdapter(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vector_dim=settings.EMBEDDING_DIMENSION,
                upsert_batch_size=settings.QDRANT_UPSERT_BATCH_SIZE,
                bm25_max_chunks=settings.BM25_MAX_CHUNKS_IN_MEMORY,
            )

        elif provider in cls._registry:
            adapter_cls = cls._registry[provider]

            return adapter_cls(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY,
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vector_dim=settings.EMBEDDING_DIMENSION,
            )

        else:
            supported = list(cls._registry.keys())

            raise ValueError(
                f"Unsupported VectorStore provider '{provider}'. Supported providers are: {supported}"
            )
