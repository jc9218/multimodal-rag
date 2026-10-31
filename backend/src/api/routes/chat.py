import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from src.domain.exceptions import LLMServiceError, VectorStoreError
from src.domain.models import QueryResponse
from src.infrastructure.container import Container, get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Multimodal RAG Chat"])


# Clase: ChatHistoryItem.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class ChatHistoryItem(BaseModel):
    role: str = Field(default="user", description="'user' o 'assistant'")
    content: str = Field(..., max_length=4000, description="Contenido textual del mensaje")


# Clase: QueryRequest.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000, description="Pregunta en lenguaje natural")
    top_k: int = Field(default=4, ge=1, le=10, description="Cantidad de fragmentos a recuperar")
    document_id: Optional[str] = Field(
        default=None, description="Filtro opcional por ID de documento individual"
    )
    document_ids: Optional[List[str]] = Field(
        default=None, description="Filtro opcional por lista de IDs de documentos del chat"
    )
    chat_history: Optional[List[ChatHistoryItem]] = Field(
        default=None, max_length=20, description="Historial previo de la conversación para mantener contexto"
    )


# Objetivo: Query rag.
# Entradas: request, app_container.
# Salida: Resultado de la operación o None si no retorna un valor..
@router.post(
    "/query",
    response_model=QueryResponse,
    status_code=status.HTTP_200_OK,
    summary="Query RAG engine with hybrid search, multi-doc filter, and conversational memory",
)
def query_rag(
    request: QueryRequest,
    app_container: Container = Depends(get_container),
):
    try:
        history_dicts = None
        if request.chat_history:
            history_dicts = [item.model_dump() for item in request.chat_history]

        response = app_container.query_use_case.execute(
            query=request.query,
            top_k=request.top_k,
            document_id=request.document_id,
            document_ids=request.document_ids,
            chat_history=history_dicts,
        )
        return response
    except LLMServiceError as e:
        logger.error(f"[ChatRoute:query_rag] LLM service failure for query '{request.query}': {e}", exc_info=True)
        return QueryResponse(
            query=request.query,
            answer="El servicio de inteligencia artificial no pudo completar la respuesta en este momento (posible límite de tasa temporal). Por favor intenta nuevamente en unos instantes.",
            sources=[],
            images=[],
            is_defensive=True,
        )
    except VectorStoreError as e:
        logger.error(f"[ChatRoute:query_rag] Vector store failure for query '{request.query}': {e}", exc_info=True)
        return QueryResponse(
            query=request.query,
            answer="Hubo un problema al consultar el índice de los documentos. Por favor intenta nuevamente en unos momentos.",
            sources=[],
            images=[],
            is_defensive=True,
        )
    except Exception as e:
        logger.error(f"[ChatRoute:query_rag] Unhandled error for query '{request.query}': {e}", exc_info=True)
        return QueryResponse(
            query=request.query,
            answer="Ocurrió un error inesperado al procesar tu consulta técnica. Por favor formula nuevamente tu pregunta o reintenta en unos instantes.",
            sources=[],
            images=[],
            is_defensive=True,
        )
