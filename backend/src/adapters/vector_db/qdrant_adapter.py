from collections import defaultdict

import logging

import re

from typing import Callable, Dict, List, Optional

import uuid

from qdrant_client import QdrantClient

from qdrant_client.http import models as qmodels

from rank_bm25 import BM25Okapi

from src.domain.exceptions import VectorStoreError

from src.domain.models import BoundingBox, Chunk, ExtractedImage, RetrievedChunk

from src.infrastructure.memory import release_memory

from src.ports.vector_store_port import VectorStorePort

logger = logging.getLogger(__name__)

_BM25_STOPWORDS = {
    "a",
    "al",
    "con",
    "cual",
    "cuál",
    "cómo",
    "como",
    "de",
    "del",
    "el",
    "en",
    "es",
    "habla",
    "la",
    "las",
    "lo",
    "los",
    "me",
    "para",
    "por",
    "qué",
    "que",
    "se",
    "sobre",
    "un",
    "una",
    "y",
}


def _tokenize_bm25(text: str) -> List[str]:
    """Tokenize technical terms while ignoring common question words."""

    return [
        token
        for token in re.findall(r"[^\W_]+", text.lower())
        if token not in _BM25_STOPWORDS
    ]


def _chunk_search_text(chunk: Chunk) -> str:
    """Include stable document metadata so identity queries can retrieve the document."""

    document_name = chunk.metadata.get("document_name", "")

    return f"{document_name} {chunk.text}"


# Purpose: Is document identity query.

# Inputs: query.

# Output: bool.


def _is_document_identity_query(query: str) -> bool:
    """is document identity query.

    Args:

        query: str.

    Returns:

        bool..

    """

    tokens = set(_tokenize_bm25(query))

    return bool(
        tokens
        & {
            "marca",
            "fabricante",
            "brand",
            "manufacturer",
            "modelo",
            "model",
            "documento",
            "manual",
            "nombre",
            "título",
            "titulo",
        }
    )


# Purpose: Is broad query.

# Inputs: query.

# Output: bool.


def _is_broad_query(query: str) -> bool:
    """is broad query.

    Args:

        query: str.

    Returns:

        bool..

    """

    normalized = " ".join(query.lower().split())

    return any(
        phrase in normalized
        for phrase in (
            "de qué habla",
            "de que habla",
            "sobre qué trata",
            "sobre que trata",
            "qué contiene",
            "que contiene",
            "resumen",
            "cuál es el tema",
            "cual es el tema",
        )
    )


# Class: QdrantAdapter.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class QdrantAdapter(VectorStorePort):
    # Purpose: Init.

    # Inputs: self, url, api_key, collection_name, vector_dim, upsert_batch_size, bm25_max_chunks.

    # Output: Operation result, or None when no value is returned.

    def __init__(
        self,
        url: str = "http://localhost:6333",
        api_key: Optional[str] = None,
        collection_name: str = "technical_documents",
        vector_dim: int = 1536,
        upsert_batch_size: int = 25,
        bm25_max_chunks: int = 5000,
    ):
        """init.

        Args:

            url: str, api_key: Optional[str], collection_name: str, vector_dim: int, upsert_batch_size: int, bm25_max_chunks: int.

        Returns:

            unspecified..

        """

        self.url = url

        self.api_key = api_key if api_key else None

        self.collection_name = collection_name

        self.vector_dim = vector_dim

        self.upsert_batch_size = max(1, upsert_batch_size)

        self.bm25_max_chunks = max(1, bm25_max_chunks)

        # In-memory corpus registry for BM25 sparse keyword retrieval

        self._corpus_chunks: Dict[str, Chunk] = {}

        self._bm25_tokenized_corpus: List[List[str]] = []

        self._bm25_chunk_ids: List[str] = []

        self._bm25_index: Optional[BM25Okapi] = None

        # Images registry for fallback hydration

        self._images_registry: Dict[str, ExtractedImage] = {}

        try:
            self.client = QdrantClient(url=self.url, api_key=self.api_key, timeout=10.0)

            self.initialize()

        except Exception as e:
            logger.warning(
                f"Could not connect to Qdrant at {self.url} during startup ({e}). Running in fallback mode."
            )

            self.client = None

    def register_images(self, images: List[ExtractedImage]) -> None:
        """Stores image metadata to hydrate retrieved chunks."""

        for img in images:
            self._images_registry[img.id] = img

    def get_images_for_page(self, document_id: str, page: int) -> List[ExtractedImage]:
        """Returns page images from memory and persisted Qdrant payloads."""

        matched: Dict[str, ExtractedImage] = {}

        for img in self._images_registry.values():
            if img.document_id == document_id and img.page == page:
                matched[img.id] = img

        if self.client:
            page_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    ),
                    qmodels.FieldCondition(
                        key="page",
                        match=qmodels.MatchValue(value=page),
                    ),
                ]
            )

            try:
                points, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=page_filter,
                    limit=100,
                    with_payload=True,
                )

                for point in points or []:
                    payload = getattr(point, "payload", None) or {}

                    for raw_image in payload.get("associated_images", []):
                        try:
                            image = (
                                ExtractedImage(**raw_image)
                                if isinstance(raw_image, dict)
                                else raw_image
                            )

                            if (
                                isinstance(image, ExtractedImage)
                                and image.document_id == document_id
                                and image.page == page
                            ):
                                matched[image.id] = image

                                self._images_registry[image.id] = image

                        except Exception:
                            logger.warning(
                                "[QdrantAdapter:get_images_for_page] Ignoring invalid image payload "
                                "document_id=%s page=%s",
                                document_id,
                                page,
                            )

            except Exception:
                logger.exception(
                    "[QdrantAdapter:get_images_for_page] Failed to load persisted images "
                    "document_id=%s page=%s",
                    document_id,
                    page,
                )

        return list(matched.values())

    # Purpose: Document scoped fallback.

    # Inputs: self, top_k, document_id, document_ids.

    # Output: List[RetrievedChunk].

    def _document_scoped_fallback(
        self,
        top_k: int,
        document_id: Optional[str],
        document_ids: Optional[List[str]],
    ) -> List[RetrievedChunk]:
        """document scoped fallback.

        Args:

            top_k: int, document_id: Optional[str], document_ids: Optional[List[str]].

        Returns:

            List[RetrievedChunk]..

        """

        if not self.client or (not document_id and not document_ids):
            return []

        if document_ids:
            fallback_filter = qmodels.Filter(
                should=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=did),
                    )
                    for did in document_ids
                ]
            )

        else:
            fallback_filter = qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    )
                ]
            )

        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=fallback_filter,
            limit=top_k,
            with_payload=True,
        )

        retrieved: List[RetrievedChunk] = []

        for rank, point in enumerate(points or [], 1):
            payload = (
                getattr(point, "payload", None)
                or (point.get("payload") if isinstance(point, dict) else {})
                or {}
            )

            cid = payload.get("chunk_id")

            doc_id = payload.get("document_id")

            text = payload.get("text", "")

            if not cid or not doc_id or not text:
                continue

            if document_ids is not None and doc_id not in document_ids:
                continue

            if document_id and doc_id != document_id:
                continue

            raw_bbox = payload.get("bbox", {})

            bbox = (
                BoundingBox(**raw_bbox)
                if isinstance(raw_bbox, dict) and raw_bbox
                else BoundingBox(page=payload.get("page", 1), x0=0, y0=0, x1=0, y1=0)
            )

            hydrated_images: List[ExtractedImage] = []

            for item in payload.get("associated_images", []):
                try:
                    if isinstance(item, dict):
                        hydrated_images.append(ExtractedImage(**item))

                    elif isinstance(item, ExtractedImage):
                        hydrated_images.append(item)

                except Exception:
                    logger.warning(
                        "[QdrantAdapter:_document_scoped_fallback] Ignoring invalid image payload "
                        "for chunk_id=%s",
                        cid,
                    )

            retrieved.append(
                RetrievedChunk(
                    chunk_id=cid,
                    document_id=doc_id,
                    document_name=payload.get("document_name", doc_id),
                    text=text,
                    page=payload.get("page", 1),
                    bbox=bbox,
                    score=round(1.0 / (60 + rank), 4),
                    associated_images=hydrated_images,
                )
            )

        return retrieved

    # Purpose: Initialize.

    # Inputs: self.

    # Output: None.

    def initialize(self) -> None:
        """Initialize.

        Args:

            None.

        Returns:

            None..

        """

        if not self.client:
            return

        try:
            collections = self.client.get_collections().collections

            exists = any(c.name == self.collection_name for c in collections)

            if exists:
                # Check existing collection vector dimension

                c_info = self.client.get_collection(self.collection_name)

                params = getattr(c_info.config, "params", None)

                vectors_cfg = getattr(params, "vectors", None) if params else None

                existing_dim = None

                if hasattr(vectors_cfg, "size"):
                    existing_dim = vectors_cfg.size

                elif isinstance(vectors_cfg, dict):
                    existing_dim = vectors_cfg.get("size")

                if existing_dim and existing_dim != self.vector_dim:
                    legacy_collection = self.collection_name

                    self.collection_name = f"{legacy_collection}_{self.vector_dim}d"

                    logger.warning(
                        "Collection '%s' has dimension %s; using isolated collection '%s' "
                        "for configured dimension %s. Existing data is preserved and must be re-indexed.",
                        legacy_collection,
                        existing_dim,
                        self.collection_name,
                        self.vector_dim,
                    )

                    isolated_exists = any(
                        c.name == self.collection_name for c in collections
                    )

                    if not isolated_exists:
                        self.client.create_collection(
                            collection_name=self.collection_name,
                            vectors_config=qmodels.VectorParams(
                                size=self.vector_dim,
                                distance=qmodels.Distance.COSINE,
                            ),
                        )

                    self._ensure_payload_indexes()

                    self._rehydrate_bm25_from_qdrant()

                    return

            else:
                logger.info(
                    f"[QdrantAdapter:initialize] Creating collection '{self.collection_name}' (dim={self.vector_dim})"
                )

                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.vector_dim,
                        distance=qmodels.Distance.COSINE,
                    ),
                )

            # Ensure payload indexes exist for filtering

            self._ensure_payload_indexes()

            # Rehydrate BM25 index from persistent Qdrant points if corpus is empty

            self._rehydrate_bm25_from_qdrant()

        except Exception as e:
            if isinstance(e, VectorStoreError):
                raise

            logger.error(
                f"[QdrantAdapter:initialize] Failed to initialize Qdrant collection: {e}",
                exc_info=True,
            )

            raise VectorStoreError(f"Qdrant init error: {e}") from e

    def _ensure_payload_indexes(self) -> None:
        """Creates required keyword payload indexes for fast and valid filtered queries."""

        if not self.client:
            return

        schema = (
            getattr(qmodels.PayloadSchemaType, "KEYWORD", "keyword")
            if hasattr(qmodels, "PayloadSchemaType")
            else "keyword"
        )

        for field in ["document_id", "chunk_id"]:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field,
                    field_schema=schema,
                )

            except Exception as pe:
                logger.debug(
                    f"[QdrantAdapter:_ensure_payload_indexes] Index for '{field}' info: {pe}"
                )

    def _rehydrate_bm25_from_qdrant(self) -> None:
        """Rebuilds BM25 index from persistent Qdrant points after server restart."""

        if not self.client:
            return

        try:
            offset = None

            total_recovered = 0

            while len(self._bm25_chunk_ids) < self.bm25_max_chunks:
                scroll_res = self.client.scroll(
                    collection_name=self.collection_name,
                    limit=250,
                    offset=offset,
                    with_payload=True,
                )

                points, next_offset = scroll_res

                for pt in points:
                    p = (
                        getattr(pt, "payload", None)
                        or (pt.get("payload") if isinstance(pt, dict) else {})
                        or {}
                    )

                    cid = p.get("chunk_id")

                    text = p.get("text", "")

                    if cid and cid not in self._corpus_chunks:
                        raw_bbox = p.get("bbox", {})

                        bbox = (
                            BoundingBox(**raw_bbox)
                            if isinstance(raw_bbox, dict) and raw_bbox
                            else BoundingBox(
                                page=p.get("page", 1), x0=0, y0=0, x1=0, y1=0
                            )
                        )

                        chunk = Chunk(
                            id=cid,
                            document_id=p.get("document_id", ""),
                            text=text,
                            page=p.get("page", 1),
                            bbox=bbox,
                            associated_images=[
                                img.get("id") if isinstance(img, dict) else str(img)
                                for img in p.get("associated_images", [])
                            ],
                            metadata={
                                "document_name": p.get("document_name", ""),
                                "created_at": p.get("created_at"),
                            },
                        )

                        # Rehydrate ExtractedImage objects into _images_registry

                        for raw_img in p.get("associated_images", []):
                            if isinstance(raw_img, dict) and "id" in raw_img:
                                try:
                                    img_obj = ExtractedImage(**raw_img)

                                    self._images_registry[img_obj.id] = img_obj

                                except Exception:
                                    pass

                        self._corpus_chunks[cid] = chunk

                        self._bm25_chunk_ids.append(cid)

                        self._bm25_tokenized_corpus.append(
                            _tokenize_bm25(_chunk_search_text(chunk))
                        )

                        self._trim_bm25_memory()

                        total_recovered += 1

                if next_offset is None:
                    break

                offset = next_offset

            if self._bm25_tokenized_corpus:
                self._bm25_index = BM25Okapi(self._bm25_tokenized_corpus)

                logger.info(
                    f"[QdrantAdapter:_rehydrate_bm25_from_qdrant] Rehydrated BM25 index with {total_recovered} chunks from Qdrant."
                )

            release_memory()

        except Exception as e:
            logger.warning(f"Could not rehydrate BM25 index from Qdrant: {e}")

    # Purpose: Index chunks.

    # Inputs: self, chunks, progress_callback.

    # Output: int.

    def index_chunks(
        self,
        chunks: List[Chunk],
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> int:
        """Index chunks.

        Args:

            chunks: List[Chunk], progress_callback: Optional[Callable[[float, str], None]].

        Returns:

            int..

        """

        if not chunks:
            return 0

        # Update in-memory registry & BM25 index (strip embeddings to save memory on 512MB instances)

        total_chunks = len(chunks)

        for index, c in enumerate(chunks, 1):
            c_mem = c.model_copy()

            c_mem.embedding = None

            self._corpus_chunks[c.id] = c_mem

            if c.id not in self._bm25_chunk_ids:
                self._bm25_chunk_ids.append(c.id)

                self._bm25_tokenized_corpus.append(
                    _tokenize_bm25(_chunk_search_text(c))
                )

            self._trim_bm25_memory()

            if progress_callback and (index == total_chunks or index % 25 == 0):
                progress_callback(
                    0.05 + 0.10 * (index / total_chunks),
                    f"Construyendo índice de palabras clave ({index} de {total_chunks} fragmentos)...",
                )

        if self._bm25_tokenized_corpus:
            self._bm25_index = BM25Okapi(self._bm25_tokenized_corpus)

        if progress_callback:
            progress_callback(0.15, "Índice de palabras clave preparado.")

        # Upload to Qdrant if available

        if self.client:
            try:
                points = []

                total_chunks = len(chunks)

                for index, c in enumerate(chunks, 1):
                    vector = c.embedding if c.embedding else [0.0] * self.vector_dim

                    # Store full ExtractedImage metadata inside Qdrant payload

                    # so chunks can hydrate completely after restart

                    images_payload = []

                    for item in c.associated_images:
                        if isinstance(item, ExtractedImage):
                            images_payload.append(item.model_dump())

                        elif isinstance(item, dict):
                            images_payload.append(item)

                        elif isinstance(item, str) and item in self._images_registry:
                            images_payload.append(
                                self._images_registry[item].model_dump()
                            )

                    payload = {
                        "chunk_id": c.id,
                        "document_id": c.document_id,
                        "document_name": c.metadata.get("document_name", c.document_id),
                        "created_at": c.metadata.get("created_at"),
                        "text": c.text,
                        "page": c.page,
                        "bbox": c.bbox.model_dump(),
                        "associated_images": images_payload,
                    }

                    # Deterministic, collision-free UUID5 based on chunk id

                    point_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, c.id))

                    points.append(
                        qmodels.PointStruct(
                            id=point_uuid,
                            vector=vector,
                            payload=payload,
                        )
                    )

                    c.embedding = None

                    if progress_callback and (index == total_chunks or index % 25 == 0):
                        progress_callback(
                            0.15 + 0.65 * (index / total_chunks),
                            f"Preparando índice vectorial ({index} de {total_chunks} fragmentos)...",
                        )

                    if len(points) >= self.upsert_batch_size:
                        self._upsert_points_batch(
                            points, index, total_chunks, progress_callback
                        )

                        points.clear()

                if points:
                    self._upsert_points_batch(
                        points, total_chunks, total_chunks, progress_callback
                    )

                    points.clear()

            except Exception as e:
                logger.error(
                    f"[QdrantAdapter:index_chunks] Error upserting points to Qdrant: {e}",
                    exc_info=True,
                )

                raise VectorStoreError(f"Failed to index points in Qdrant: {e}") from e

        release_memory()

        return len(chunks)

    # Purpose: Trim bm25 memory.

    # Inputs: self.

    # Output: None.

    def _trim_bm25_memory(self) -> None:
        """trim bm25 memory.

        Args:

            None.

        Returns:

            None..

        """

        overflow = len(self._bm25_chunk_ids) - self.bm25_max_chunks

        if overflow <= 0:
            return

        evicted_ids = self._bm25_chunk_ids[:overflow]

        del self._bm25_chunk_ids[:overflow]

        del self._bm25_tokenized_corpus[:overflow]

        for chunk_id in evicted_ids:
            self._corpus_chunks.pop(chunk_id, None)

    # Purpose: Upsert points batch.

    # Inputs: self, points, processed, total, progress_callback.

    # Output: None.

    def _upsert_points_batch(
        self,
        points: List[qmodels.PointStruct],
        processed: int,
        total: int,
        progress_callback: Optional[Callable[[float, str], None]],
    ) -> None:
        """upsert points batch.

        Args:

            points: List[qmodels.PointStruct], processed: int, total: int, progress_callback: Optional[Callable[[float, str], None]].

        Returns:

            None..

        """

        if progress_callback:
            progress_callback(
                0.85 * (processed / total),
                f"Enviando fragmentos al índice vectorial ({processed} de {total})...",
            )

        self.client.upsert(collection_name=self.collection_name, points=points)

    def hybrid_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> List[RetrievedChunk]:
        """

        Reciprocal Rank Fusion (RRF) between Dense (Vector) and Sparse (BM25).

        RRF_score(d) = sum(1.0 / (60 + rank))

        """

        if document_ids is not None and len(document_ids) == 0:
            return []

        # If BM25 is not loaded, attempt lazy rehydration from Qdrant

        if self._bm25_index is None and self.client:
            self._rehydrate_bm25_from_qdrant()

        dense_ranks: Dict[str, int] = {}

        sparse_ranks: Dict[str, int] = {}

        qdrant_payloads: Dict[str, dict] = {}

        # 1. Dense retrieval via Qdrant

        if self.client:
            try:
                search_filter = None

                if document_ids and len(document_ids) > 0:
                    if len(document_ids) == 1:
                        search_filter = qmodels.Filter(
                            must=[
                                qmodels.FieldCondition(
                                    key="document_id",
                                    match=qmodels.MatchValue(value=document_ids[0]),
                                )
                            ]
                        )

                    else:
                        search_filter = qmodels.Filter(
                            should=[
                                qmodels.FieldCondition(
                                    key="document_id",
                                    match=qmodels.MatchValue(value=did),
                                )
                                for did in document_ids
                            ]
                        )

                elif document_id:
                    search_filter = qmodels.Filter(
                        must=[
                            qmodels.FieldCondition(
                                key="document_id",
                                match=qmodels.MatchValue(value=document_id),
                            )
                        ]
                    )

                # Purpose: Execute qdrant query.

                # Inputs: None.

                # Output: Operation result, or None when no value is returned.

                def _execute_qdrant_query():
                    """execute qdrant query.

                    Args:

                        None.

                    Returns:

                        unspecified..

                    """

                    if hasattr(self.client, "query_points"):
                        try:
                            query_res = self.client.query_points(
                                collection_name=self.collection_name,
                                query=query_embedding,
                                query_filter=search_filter,
                                limit=top_k * 4,
                                with_payload=True,
                            )

                            return getattr(query_res, "points", query_res) or []

                        except (AttributeError, TypeError):
                            pass

                    if hasattr(self.client, "search"):
                        return self.client.search(
                            collection_name=self.collection_name,
                            query_vector=query_embedding,
                            query_filter=search_filter,
                            limit=top_k * 4,
                            with_payload=True,
                        )

                    return []

                results = _execute_qdrant_query()

                for rank, res in enumerate(results, 1):
                    p = (
                        getattr(res, "payload", None)
                        or (res.get("payload") if isinstance(res, dict) else {})
                        or {}
                    )

                    cid = p.get("chunk_id")

                    if cid:
                        dense_ranks[cid] = rank

                        qdrant_payloads[cid] = p

            except Exception as e:
                logger.warning(
                    f"[QdrantAdapter:hybrid_search] Dense search failed ({e}), falling back to pure BM25."
                )

        # 2. Sparse retrieval via BM25

        if self._bm25_index and self._bm25_chunk_ids:
            query_tokens = _tokenize_bm25(query)

            bm25_scores = self._bm25_index.get_scores(query_tokens)

            query_token_set = set(query_tokens)

            sorted_indices = sorted(
                range(len(bm25_scores)),
                key=lambda i: (
                    bm25_scores[i],
                    len(query_token_set.intersection(self._bm25_tokenized_corpus[i])),
                ),
                reverse=True,
            )

            sparse_rank = 1

            for idx in sorted_indices:
                token_overlap = len(
                    query_token_set.intersection(self._bm25_tokenized_corpus[idx])
                )

                if bm25_scores[idx] <= 0.0 and token_overlap == 0:
                    continue

                cid = self._bm25_chunk_ids[idx]

                chunk = self._corpus_chunks.get(cid)

                if chunk:
                    if (
                        document_ids is not None
                        and chunk.document_id not in document_ids
                    ):
                        continue

                    if document_id and chunk.document_id != document_id:
                        continue

                sparse_ranks[cid] = sparse_rank

                sparse_rank += 1

                if sparse_rank > top_k * 4:
                    break

        # Identity and broad questions need a document sample even when dense

        # retrieval returns plausible but semantically unrelated chunks.

        identity_query = _is_document_identity_query(query)

        identity_fallback_ids: set[str] = set()

        if (
            self.client
            and (document_ids or document_id)
            and (identity_query or _is_broad_query(query))
        ):
            try:
                fallback_limit = max(top_k * 4, 12) if identity_query else top_k

                fallback_chunks = self._document_scoped_fallback(
                    fallback_limit, document_id, document_ids
                )

                fallback_chunks.sort(key=lambda chunk: (chunk.page, chunk.chunk_id))

                next_rank = (
                    1 if identity_query else max(dense_ranks.values(), default=0) + 1
                )

                for fallback_chunk in fallback_chunks:
                    if (
                        fallback_chunk.chunk_id in dense_ranks
                        or fallback_chunk.chunk_id in sparse_ranks
                    ):
                        continue

                    identity_fallback_ids.add(fallback_chunk.chunk_id)

                    dense_ranks[fallback_chunk.chunk_id] = next_rank

                    next_rank += 1

                    qdrant_payloads[fallback_chunk.chunk_id] = {
                        "chunk_id": fallback_chunk.chunk_id,
                        "document_id": fallback_chunk.document_id,
                        "document_name": fallback_chunk.document_name,
                        "text": fallback_chunk.text,
                        "page": fallback_chunk.page,
                        "bbox": fallback_chunk.bbox.model_dump(),
                        "associated_images": [
                            image.model_dump()
                            for image in fallback_chunk.associated_images
                        ],
                    }

            except Exception as e:
                logger.warning(
                    "[QdrantAdapter:hybrid_search] Metadata fallback failed: %s",
                    e,
                )

        if identity_fallback_ids:
            fallback_rank_count = len(identity_fallback_ids)

            dense_ranks = {
                cid: rank
                if cid in identity_fallback_ids
                else rank + fallback_rank_count
                for cid, rank in dense_ranks.items()
            }

        # Broad questions can have no exact BM25 terms, and an unavailable or

        # stale dense index can return no candidates despite the document existing.

        # Use a small document-scoped sample so the LLM can still answer from source.

        if (
            not dense_ranks
            and not sparse_ranks
            and self.client
            and (document_ids or document_id)
        ):
            try:
                fallback_chunks = self._document_scoped_fallback(
                    top_k, document_id, document_ids
                )

                for rank, fallback_chunk in enumerate(fallback_chunks, 1):
                    dense_ranks[fallback_chunk.chunk_id] = rank

                    qdrant_payloads[fallback_chunk.chunk_id] = {
                        "chunk_id": fallback_chunk.chunk_id,
                        "document_id": fallback_chunk.document_id,
                        "document_name": fallback_chunk.document_name,
                        "text": fallback_chunk.text,
                        "page": fallback_chunk.page,
                        "bbox": fallback_chunk.bbox.model_dump(),
                        "associated_images": [],
                    }

                logger.info(
                    "[QdrantAdapter:hybrid_search] Used document-scoped fallback with %d chunks.",
                    len(fallback_chunks),
                )

            except Exception as e:
                logger.warning(
                    "[QdrantAdapter:hybrid_search] Document-scoped fallback failed: %s",
                    e,
                )

        # 3. Reciprocal Rank Fusion (RRF)

        rrf_constant = 60

        rrf_scores: Dict[str, float] = defaultdict(float)

        all_candidate_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())

        if not all_candidate_ids:
            return []

        for cid in all_candidate_ids:
            score = 0.0

            if cid in dense_ranks:
                score += 1.0 / (rrf_constant + dense_ranks[cid])

            if cid in sparse_ranks:
                score += 1.0 / (rrf_constant + sparse_ranks[cid])

            rrf_scores[cid] = score

        # Sort by RRF score descending

        sorted_candidates = sorted(
            rrf_scores.items(), key=lambda x: x[1], reverse=True
        )[:top_k]

        # Hydrate retrieved chunks

        retrieved: List[RetrievedChunk] = []

        for cid, score in sorted_candidates:
            chunk = self._corpus_chunks.get(cid)

            payload = qdrant_payloads.get(cid, {})

            if not chunk and not payload:
                continue

            doc_id = chunk.document_id if chunk else payload.get("document_id")

            if document_ids is not None and doc_id not in document_ids:
                continue

            if document_id and doc_id != document_id:
                continue

            text = chunk.text if chunk else payload.get("text", "")

            page = chunk.page if chunk else payload.get("page", 1)

            doc_name = (
                chunk.metadata.get("document_name", doc_id)
                if chunk
                else payload.get("document_name", doc_id)
            )

            raw_bbox = chunk.bbox if chunk else payload.get("bbox", {})

            if isinstance(raw_bbox, BoundingBox):
                bbox = raw_bbox

            elif isinstance(raw_bbox, dict) and raw_bbox:
                bbox = BoundingBox(**raw_bbox)

            else:
                bbox = BoundingBox(x0=0.0, y0=0.0, x1=0.0, y1=0.0, page=page)

            # Hydrate associated images from Qdrant payload or memory registry

            associated_images_raw = payload.get("associated_images", []) or (
                chunk.associated_images if chunk else []
            )

            hydrated_images: List[ExtractedImage] = []

            for item in associated_images_raw:
                if isinstance(item, dict):
                    hydrated_images.append(ExtractedImage(**item))

                elif isinstance(item, ExtractedImage):
                    hydrated_images.append(item)

                elif isinstance(item, str) and item in self._images_registry:
                    hydrated_images.append(self._images_registry[item])

            retrieved.append(
                RetrievedChunk(
                    chunk_id=cid,
                    document_id=doc_id,
                    document_name=doc_name,
                    text=text,
                    page=page,
                    bbox=bbox,
                    score=round(score, 4),
                    associated_images=hydrated_images,
                )
            )

        if not retrieved and self.client and (document_ids or document_id):
            retrieved = self._document_scoped_fallback(top_k, document_id, document_ids)

            logger.info(
                "[QdrantAdapter:hybrid_search] Hydration fallback returned %d chunks.",
                len(retrieved),
            )

        logger.info(
            "[QdrantAdapter:hybrid_search] candidates dense=%d sparse=%d hydrated=%d",
            len(dense_ranks),
            len(sparse_ranks),
            len(retrieved),
        )

        return retrieved

    def list_documents(self) -> List[dict]:
        """Returns list of unique documents with full pagination scroll across all points."""

        docs_map = {}

        for c in self._corpus_chunks.values():
            doc_id = c.document_id

            if doc_id not in docs_map:
                doc_name = c.metadata.get("document_name", doc_id)

                created_at = c.metadata.get("created_at")

                docs_map[doc_id] = {
                    "id": doc_id,
                    "name": doc_name,
                    "created_at": created_at,
                }

        if self.client:
            try:
                offset = None

                while True:
                    scroll_result = self.client.scroll(
                        collection_name=self.collection_name,
                        limit=250,
                        offset=offset,
                        with_payload=True,
                    )

                    points, next_offset = scroll_result

                    for pt in points:
                        p = (
                            getattr(pt, "payload", None)
                            or (pt.get("payload") if isinstance(pt, dict) else {})
                            or {}
                        )

                        did = p.get("document_id")

                        if did and did not in docs_map:
                            dname = p.get("document_name", did)

                            created_at = p.get("created_at")

                            docs_map[did] = {
                                "id": did,
                                "name": dname,
                                "created_at": created_at,
                            }

                    if next_offset is None:
                        break

                    offset = next_offset

            except Exception as e:
                logger.warning(f"Failed to scroll documents from Qdrant: {e}")

        return list(docs_map.values())

    def delete_document(self, document_id: str) -> int:
        """Deletes all chunks, images, and points related to a document from Qdrant and memory."""

        deleted_count = 0

        # 1. Delete points from Qdrant if client is connected

        if self.client:
            try:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=qmodels.FilterSelector(
                        filter=qmodels.Filter(
                            must=[
                                qmodels.FieldCondition(
                                    key="document_id",
                                    match=qmodels.MatchValue(value=document_id),
                                )
                            ]
                        )
                    ),
                )

                logger.info(
                    f"Deleted points for document_id '{document_id}' from Qdrant."
                )

            except Exception as e:
                logger.error(
                    f"Error deleting points for document_id '{document_id}' from Qdrant: {e}"
                )

                raise VectorStoreError(
                    f"Failed to delete document from Qdrant: {e}"
                ) from e

        # 2. Delete from in-memory corpus chunks

        cids_to_remove = [
            cid
            for cid, c in self._corpus_chunks.items()
            if c.document_id == document_id
        ]

        for cid in cids_to_remove:
            del self._corpus_chunks[cid]

            deleted_count += 1

        # 3. Delete from images registry

        imgs_to_remove = [
            iid
            for iid, img in self._images_registry.items()
            if img.document_id == document_id
        ]

        for iid in imgs_to_remove:
            del self._images_registry[iid]

        # 4. Rebuild BM25 index with remaining corpus

        self._bm25_tokenized_corpus = []

        self._bm25_chunk_ids = []

        for c in self._corpus_chunks.values():
            self._bm25_chunk_ids.append(c.id)

            self._bm25_tokenized_corpus.append(_tokenize_bm25(_chunk_search_text(c)))

        if self._bm25_tokenized_corpus:
            self._bm25_index = BM25Okapi(self._bm25_tokenized_corpus)

        else:
            self._bm25_index = None

        logger.info(
            f"Document '{document_id}' deleted successfully ({deleted_count} chunks removed)."
        )

        return deleted_count
