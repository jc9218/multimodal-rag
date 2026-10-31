import logging
from src.ports.storage_port import StoragePort
from src.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)


class DeleteDocumentUseCase:
    """Encapsulates deleting all vector points and storage assets related to a document."""

    def __init__(self, vector_store: VectorStorePort, storage: StoragePort):
        self.vector_store = vector_store
        self.storage = storage

    def execute(self, document_id: str) -> int:
        logger.info(f"[DeleteDocumentUseCase:execute] Deleting document '{document_id}'")
        deleted_chunks = self.vector_store.delete_document(document_id)
        self.storage.delete_document_files(document_id)
        return deleted_chunks
