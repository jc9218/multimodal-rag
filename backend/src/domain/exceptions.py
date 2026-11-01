# Class: DomainError.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class DomainError(Exception):
    """Base exception for domain layer."""
    pass


# Class: DocumentNotFoundError.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class DocumentNotFoundError(DomainError):
    pass


# Class: JobNotFoundError.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class JobNotFoundError(DomainError):
    pass


# Class: JobCancelledError.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class JobCancelledError(DomainError):
    pass


# Class: IngestionError.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class IngestionError(DomainError):
    pass


# Class: LLMServiceError.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class LLMServiceError(DomainError):
    pass


# Class: VectorStoreError.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class VectorStoreError(DomainError):
    pass
