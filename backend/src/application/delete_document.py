import logging
from src.ports.storage_port import StoragePort
from src.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)


# Class: DeleteDocumentUseCase.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class DeleteDocumentUseCase:
    """Encapsulates deleting all vector points and storage assets related to a document."""

    # Purpose: Init.
    # Inputs: self, vector_store, storage.
    # Output: Operation result, or None when no value is returned.
    def __init__(self, vector_store: VectorStorePort, storage: StoragePort):
        self.vector_store = vector_store
        self.storage = storage

    # Purpose: Execute.
    # Inputs: self, document_id.
    # Output: int.
    def execute(self, document_id: str) -> int:
        logger.info(f"[DeleteDocumentUseCase:execute] Deleting document '{document_id}'")
        deleted_chunks = 0
        vector_error = None
        try:
            deleted_chunks = self.vector_store.delete_document(document_id)
        except Exception as exc:
            vector_error = exc
            logger.exception(
                "[DeleteDocumentUseCase:execute] Vector cleanup failed for document '%s'.",
                document_id,
            )
        try:
            self.storage.delete_document_files(document_id)
        except Exception:
            logger.exception(
                "[DeleteDocumentUseCase:execute] Storage cleanup failed for document '%s'.",
                document_id,
            )
            if vector_error is not None:
                raise vector_error
            raise
        if vector_error is not None:
            raise vector_error
        return deleted_chunks
