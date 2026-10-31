import logging
from src.ports.storage_port import StoragePort
from src.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)


# Clase: DeleteDocumentUseCase.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class DeleteDocumentUseCase:
    """Encapsulates deleting all vector points and storage assets related to a document."""

    # Objetivo: Init.
    # Entradas: self, vector_store, storage.
    # Salida: Resultado de la operación o None si no retorna un valor..
    def __init__(self, vector_store: VectorStorePort, storage: StoragePort):
        self.vector_store = vector_store
        self.storage = storage

    # Objetivo: Execute.
    # Entradas: self, document_id.
    # Salida: int.
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
