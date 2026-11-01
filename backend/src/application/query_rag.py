import logging

from collections import OrderedDict

from typing import List, Optional

from src.domain.models import ExtractedImage, QueryResponse, RetrievedChunk

from src.ports.llm_port import LLMPort

from src.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)

# Class: QueryRAGUseCase.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class QueryRAGUseCase:
    # Purpose: Init.

    # Inputs: self, vector_store, llm.

    # Output: Operation result, or None when no value is returned.

    def __init__(self, vector_store: VectorStorePort, llm: LLMPort):
        """init.

        Args:

            vector_store: VectorStorePort, llm: LLMPort.

        Returns:

            unspecified..

        """

        self.vector_store = vector_store

        self.llm = llm

        self._query_embedding_cache: OrderedDict[str, List[float]] = OrderedDict()

        self._query_embedding_cache_size = 256

    # Purpose: Get query embedding.

    # Inputs: self, query.

    # Output: List[float].

    def _get_query_embedding(self, query: str) -> List[float]:
        """get query embedding.

        Args:

            query: str.

        Returns:

            List[float]..

        """

        cache_key = " ".join(query.lower().split())

        cached = self._query_embedding_cache.get(cache_key)

        if cached is not None:
            self._query_embedding_cache.move_to_end(cache_key)

            return list(cached)

        embedding = self.llm.generate_query_embedding(query)

        self._query_embedding_cache[cache_key] = list(embedding)

        self._query_embedding_cache.move_to_end(cache_key)

        if len(self._query_embedding_cache) > self._query_embedding_cache_size:
            self._query_embedding_cache.popitem(last=False)

        return embedding

    # Purpose: Execute.

    # Inputs: self, query, top_k, document_id, document_ids, chat_history.

    # Output: QueryResponse.

    def execute(
        self,
        query: str,
        top_k: int = 4,
        document_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        chat_history: Optional[List[dict]] = None,
    ) -> QueryResponse:
        """Execute.

        Args:

            query: str, top_k: int, document_id: Optional[str], document_ids: Optional[List[str]], chat_history: Optional[List[dict]].

        Returns:

            QueryResponse..

        """

        logger.info(
            f"[QueryRAGUseCase:execute] Query: '{query}' | doc_ids={document_ids} | doc_id={document_id} | history_len={len(chat_history) if chat_history else 0}"
        )

        # Guard: If a chat has an explicit empty list of documents, no documents are linked yet

        if document_ids is not None and len(document_ids) == 0:
            logger.info("[QueryRAGUseCase:execute] Chat has no linked documents.")

            return QueryResponse(
                query=query,
                answer="Este chat no tiene documentos técnicos asociados. Por favor asocia o sube un documento PDF para comenzar.",
                sources=[],
                images=[],
                is_defensive=True,
            )

        # Contextual search expansion:

        # If the user asks a short follow-up (e.g. "And the needle?", "How is it calibrated?"),

        # anchor the retrieval query with recent conversational context.

        search_query = query

        broad_document_query = any(
            phrase in query.lower()
            for phrase in (
                "de qué habla",
                "sobre qué trata",
                "qué contiene",
                "resumen",
                "marca",
                "fabricante",
                "modelo",
                "nombre del documento",
            )
        )

        if chat_history and len(query.split()) < 6 and not broad_document_query:
            for item in reversed(chat_history):
                role = item.get("role", "")

                text = item.get("content", item.get("text", "")).strip()

                if role in ["user", "human"] and text != query and len(text) > 3:
                    search_query = f"{query} (contexto: {text[:80]})"

                    logger.info(
                        f"[QueryRAGUseCase:execute] Expanded short query to: '{search_query}'"
                    )

                    break

        # Step 1: Query embedding (with resilient fallback to lexical BM25 search)

        try:
            query_emb = self._get_query_embedding(search_query)

        except Exception as emb_err:
            logger.warning(
                f"[QueryRAGUseCase:execute] Query embedding failed ({emb_err}), continuing with lexical BM25 search."
            )

            query_emb = []

        # Step 2: Hybrid search (Dense + Sparse BM25)

        try:
            retrieved_chunks: List[RetrievedChunk] = self.vector_store.hybrid_search(
                query=search_query,
                query_embedding=query_emb,
                top_k=top_k,
                document_id=document_id,
                document_ids=document_ids,
            )

            logger.info(
                f"[QueryRAGUseCase:execute] Hybrid search returned {len(retrieved_chunks)} chunks."
            )

        except Exception as search_err:
            logger.error(
                f"[QueryRAGUseCase:execute] Hybrid search failed ({search_err}). Returning defensive fallback answer.",
                exc_info=True,
            )

            return QueryResponse(
                query=query,
                answer="Hubo una dificultad momentánea al consultar la base de datos de documentos. Por favor intenta de nuevo en unos instantes.",
                sources=[],
                images=[],
                is_defensive=True,
            )

        logger.info(
            f"[QueryRAGUseCase:execute] Retrieved Chunks: {[chunk.chunk_id for chunk in retrieved_chunks]}"
        )

        if not retrieved_chunks:
            logger.info("[QueryRAGUseCase:execute] No chunks retrieved for query.")

            return QueryResponse(
                query=query,
                answer="No se encontró información relevante en los documentos indexados para responder a tu consulta.",
                sources=[],
                images=[],
                is_defensive=True,
            )

        # Step 3: Defensive generation with chat history (resilient to LLM rate limits / downtime)

        try:
            answer, is_defensive = self.llm.generate_defensive_answer(
                query=query, context_chunks=retrieved_chunks, chat_history=chat_history
            )

            logger.info(
                f"[QueryRAGUseCase:execute] LLM response received (is_defensive={is_defensive})."
            )

        except Exception as gen_err:
            logger.error(
                f"[QueryRAGUseCase:execute] LLM generation failed ({gen_err}). Returning retrieved context fallback.",
                exc_info=True,
            )

            first_chunk = retrieved_chunks[0]

            preview = first_chunk.text[:280].strip()

            answer = (
                f"El servicio de generación del modelo no pudo procesar la respuesta en este momento.\n\n"
                f"Sin embargo, se localizó el siguiente fragmento relevante en la documentación:\n\n"
                f'> "{preview}..."\n\n'
                f"[Fuente: {first_chunk.document_name}, Pág. {first_chunk.page}]\n\n"
                f"Por favor formula nuevamente tu pregunta o reintenta en unos instantes."
            )

            is_defensive = True

        # Step 4: Collect distinct nearest images from retrieved chunks.

        # Retrieved visual evidence remains useful even when the answer is defensive:

        # the model may be cautious while the document still contains the diagram.

        matched_images: List[ExtractedImage] = []

        seen_img_ids = set()

        for chunk in retrieved_chunks:
            for img in chunk.associated_images:
                if img.id not in seen_img_ids:
                    seen_img_ids.add(img.id)

                    matched_images.append(img)

                    if len(matched_images) >= 2:
                        break

            if len(matched_images) >= 2:
                break

        # Resilient fallback: If no images were directly attached in chunk metadata,

        # but the retrieved chunks came from pages that have extracted images,

        # retrieve the images from those exact pages so the user sees the visual diagram.

        if not matched_images and hasattr(self.vector_store, "get_images_for_page"):
            for chunk in retrieved_chunks:
                page_imgs = self.vector_store.get_images_for_page(
                    chunk.document_id, chunk.page
                )

                for img in page_imgs:
                    if img.id not in seen_img_ids:
                        seen_img_ids.add(img.id)

                        matched_images.append(img)

                        if len(matched_images) >= 2:
                            break

                if len(matched_images) >= 2:
                    break

        return QueryResponse(
            query=query,
            answer=answer,
            sources=retrieved_chunks,
            images=matched_images,
            is_defensive=is_defensive,
        )
