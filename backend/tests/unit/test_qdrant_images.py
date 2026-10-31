from types import SimpleNamespace
from unittest.mock import MagicMock

from src.adapters.vector_db.qdrant_adapter import (
    QdrantAdapter,
    _chunk_search_text,
    _is_document_identity_query,
    _tokenize_bm25,
)
from rank_bm25 import BM25Okapi
from src.domain.models import BoundingBox, Chunk, ExtractedImage, RetrievedChunk


def test_get_images_for_page_hydrates_persisted_qdrant_payload():
    image = ExtractedImage(
        id="img-persisted",
        document_id="doc-1",
        filename="diagram.png",
        page=3,
        bbox=BoundingBox(page=3, x0=1, y0=2, x1=30, y1=40),
        file_path="/storage/images/doc-1/diagram.png",
        url="/api/v1/images/doc-1/diagram.png",
    )
    adapter = QdrantAdapter.__new__(QdrantAdapter)
    adapter._images_registry = {}
    adapter.collection_name = "technical_documents"
    adapter.client = SimpleNamespace(
        scroll=lambda **_: (
            [SimpleNamespace(payload={"associated_images": [image.model_dump()]})],
            None,
        )
    )

    result = adapter.get_images_for_page("doc-1", 3)

    assert [item.id for item in result] == ["img-persisted"]
    assert adapter._images_registry["img-persisted"].filename == "diagram.png"


def test_bm25_search_text_includes_document_name():
    chunk = Chunk(
        id="chunk-1",
        document_id="doc-1",
        text="Manual de instalación.",
        page=1,
        bbox=BoundingBox(page=1, x0=0, y0=0, x1=1, y1=1),
        metadata={"document_name": "Manual_Lavadora_Samsung.pdf"},
    )

    assert "samsung" in _chunk_search_text(chunk).lower()


def test_identity_query_detection_covers_document_questions():
    assert _is_document_identity_query("¿Cuál es la marca de la lavadora?")
    assert _is_document_identity_query("¿Qué modelo indica el manual?")
    assert not _is_document_identity_query("¿Cómo limpio el filtro?")


def test_hybrid_search_retrieves_document_by_filename_token():
    chunk = Chunk(
        id="chunk-1",
        document_id="doc-1",
        text="Manual de instalación y operación.",
        page=1,
        bbox=BoundingBox(page=1, x0=0, y0=0, x1=1, y1=1),
        metadata={"document_name": "Manual_Lavadora_Samsung.pdf"},
    )
    adapter = QdrantAdapter.__new__(QdrantAdapter)
    adapter.client = None
    adapter._corpus_chunks = {chunk.id: chunk}
    adapter._bm25_chunk_ids = [chunk.id]
    adapter._bm25_tokenized_corpus = [_tokenize_bm25(_chunk_search_text(chunk))]
    adapter._bm25_index = BM25Okapi(adapter._bm25_tokenized_corpus)

    result = adapter.hybrid_search(
        query="Samsung",
        query_embedding=[],
        top_k=1,
    )

    assert [item.chunk_id for item in result] == ["chunk-1"]


def test_identity_search_prioritizes_early_document_pages():
    def fallback_chunk(chunk_id: str, page: int) -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id=chunk_id,
            document_id="doc-1",
            document_name="manual.pdf",
            text="Contenido del manual.",
            page=page,
            bbox=BoundingBox(page=page, x0=0, y0=0, x1=1, y1=1),
            score=0.01,
        )

    adapter = QdrantAdapter.__new__(QdrantAdapter)
    adapter.client = SimpleNamespace(query_points=lambda **_: SimpleNamespace(points=[]))
    adapter.collection_name = "technical_documents"
    adapter._corpus_chunks = {}
    adapter._bm25_chunk_ids = []
    adapter._bm25_tokenized_corpus = []
    adapter._bm25_index = None
    adapter._document_scoped_fallback = MagicMock(
        return_value=[
            fallback_chunk("late", 4),
            fallback_chunk("cover", 1),
        ]
    )

    result = adapter.hybrid_search(
        query="¿Cuál es la marca?",
        query_embedding=[0.1],
        top_k=1,
        document_ids=["doc-1"],
    )

    assert result[0].chunk_id == "cover"
