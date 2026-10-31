import os
from unittest.mock import MagicMock
from src.domain.models import BoundingBox, Chunk, ExtractedImage, JobStatusEnum
from src.infrastructure.memory import get_process_memory_mb, release_memory
from src.application.ingest_document import IngestDocumentUseCase


def test_release_memory_executes_safely():
    """Verify release_memory can be called without errors on any platform."""
    release_memory()
    mem = get_process_memory_mb()
    assert isinstance(mem, int)
    assert mem >= 0


def test_incremental_ingestion_completes_when_parser_returns_empty_tuple():
    """
    Verify that when page_callback streams and indexes chunks per page,
    the use case correctly registers completion with the total indexed count
    instead of failing or reporting 'no text detected'.
    """
    mock_parser = MagicMock()
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()
    mock_job_repo = MagicMock()

    chunk1 = Chunk(
        id="c1",
        document_id="doc1",
        text="Sample text page 1",
        page=1,
        bbox=BoundingBox(page=1, x0=0, y0=0, x1=10, y1=10),
    )
    mock_llm.generate_embeddings.return_value = [[0.1] * 3]
    mock_vector_store.index_chunks.return_value = 1

    def side_effect_parse(**kwargs):
        # page_callback is invoked for page 1
        kwargs["page_callback"](1, 1, [chunk1], [])
        # Streaming parser returns empty list since chunks were dispatched incrementally
        return [], []

    mock_parser.parse_pdf.side_effect = side_effect_parse
    use_case = IngestDocumentUseCase(mock_parser, mock_vector_store, mock_llm, mock_job_repo)

    use_case.execute_async("job_test", "/tmp/test.pdf", "doc1")

    # Ensure job completed with the count of indexed chunks
    last_update = mock_job_repo.update_job_status.call_args_list[-1]
    assert last_update.kwargs["status"] == JobStatusEnum.COMPLETED
    assert "1 fragmentos preparados" in last_update.kwargs["message"]
