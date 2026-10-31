class DomainError(Exception):
    """Base exception for domain layer."""
    pass


class DocumentNotFoundError(DomainError):
    pass


class JobNotFoundError(DomainError):
    pass


class IngestionError(DomainError):
    pass


class LLMServiceError(DomainError):
    pass


class VectorStoreError(DomainError):
    pass
