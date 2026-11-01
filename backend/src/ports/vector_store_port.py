from abc import ABC, abstractmethod

from typing import Callable, List, Optional

from src.domain.models import Chunk, ExtractedImage, RetrievedChunk

# Class: VectorStorePort.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class VectorStorePort(ABC):
    @abstractmethod
    def initialize(self) -> None:
        """Create collections/indexes if they do not exist."""

        pass

    @abstractmethod
    def index_chunks(
        self,
        chunks: List[Chunk],
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> int:
        """Stores dense embeddings and metadata for a batch of chunks."""

        pass

    @abstractmethod
    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        """

        Executes hybrid retrieval (Dense Semantic + Sparse Keyword)

        fused with Reciprocal Rank Fusion (RRF).

        Supports filtering by a single document_id or a list of document_ids.

        """

        pass

    @abstractmethod
    def list_documents(self) -> List[dict]:
        """Returns a list of unique indexed documents [{"id": doc_id, "name": doc_name}]."""

        pass

    @abstractmethod
    def delete_document(self, document_id: str) -> int:
        """Deletes all vectors and metadata associated with document_id."""

        pass

    def get_images_for_page(self, document_id: str, page: int) -> List[ExtractedImage]:
        """Returns images associated with a document page."""

        return []
