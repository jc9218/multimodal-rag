# Clase: DomainError.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class DomainError(Exception):
    """Base exception for domain layer."""
    pass


# Clase: DocumentNotFoundError.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class DocumentNotFoundError(DomainError):
    pass


# Clase: JobNotFoundError.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class JobNotFoundError(DomainError):
    pass


# Clase: JobCancelledError.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class JobCancelledError(DomainError):
    pass


# Clase: IngestionError.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class IngestionError(DomainError):
    pass


# Clase: LLMServiceError.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class LLMServiceError(DomainError):
    pass


# Clase: VectorStoreError.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class VectorStoreError(DomainError):
    pass
