from unittest.mock import MagicMock
from src.application.get_job_status import GetJobStatusUseCase
from src.application.ingest_document import IngestDocumentUseCase
from src.application.query_rag import QueryRAGUseCase
from src.domain.models import (
    BoundingBox,
    Chunk,
    ExtractedImage,
    IngestionJob,
    JobStatusEnum,
    RetrievedChunk,
)


def test_ingest_document_use_case_success():
    # Arrange mocks
    mock_parser = MagicMock()
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()
    mock_job_repo = MagicMock()

    sample_bbox = BoundingBox(page=1, x0=10, y0=20, x1=100, y1=150)
    sample_chunk = Chunk(
        id="c1",
        document_id="doc1",
        text="Sample technical specifications of hydraulic system.",
        page=1,
        bbox=sample_bbox,
        associated_images=["img1"],
    )
    sample_image = ExtractedImage(
        id="img1",
        document_id="doc1",
        filename="diagram.png",
        page=1,
        bbox=sample_bbox,
        file_path="/tmp/diagram.png",
    )

    mock_parser.parse_pdf.return_value = ([sample_chunk], [sample_image])
    mock_llm.generate_embeddings.return_value = [[0.1] * 1536]
    mock_vector_store.index_chunks.return_value = 1

    use_case = IngestDocumentUseCase(
        parser=mock_parser,
        vector_store=mock_vector_store,
        llm=mock_llm,
        job_repo=mock_job_repo,
    )

    # Act
    use_case.execute_async("job123", "/tmp/doc.pdf", "doc1")

    # Assert
    mock_parser.parse_pdf.assert_called_once_with(
        file_path="/tmp/doc.pdf",
        document_id="doc1",
        progress_callback=mock_parser.parse_pdf.call_args.kwargs["progress_callback"],
    )
    mock_llm.generate_embeddings.assert_called_once_with([sample_chunk.text])
    assert sample_chunk.embedding == [0.1] * 1536
    mock_vector_store.index_chunks.assert_called_once()
    last_update_call = mock_job_repo.update_job_status.call_args_list[-1]
    assert last_update_call.kwargs["status"] == JobStatusEnum.COMPLETED
    assert last_update_call.kwargs["progress"] == 1.0


def test_scanned_pdf_ingestion_with_ocr():
    """Validates that scanned PDF documents extracted via OCR are ingested properly."""
    mock_parser = MagicMock()
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()
    mock_job_repo = MagicMock()

    # OCR extracted text chunk from scanned page
    ocr_bbox = BoundingBox(page=1, x0=50, y0=50, x1=500, y1=700)
    ocr_chunk = Chunk(
        id="c_scan_1",
        document_id="scan_doc",
        text="OCR text recovered from scanned technical manual page.",
        page=1,
        bbox=ocr_bbox,
        associated_images=["img_scan_1"],
    )
    scan_snapshot_image = ExtractedImage(
        id="img_scan_1",
        document_id="scan_doc",
        filename="scan_page_1.png",
        page=1,
        bbox=ocr_bbox,
        file_path="/tmp/scan_page_1.png",
    )

    mock_parser.parse_pdf.return_value = ([ocr_chunk], [scan_snapshot_image])
    mock_llm.generate_embeddings.return_value = [[0.1] * 768]
    mock_vector_store.index_chunks.return_value = 1

    use_case = IngestDocumentUseCase(
        parser=mock_parser,
        vector_store=mock_vector_store,
        llm=mock_llm,
        job_repo=mock_job_repo,
    )

    use_case.execute_async("job_scan_1", "/tmp/scan.pdf", "scan_doc")

    mock_parser.parse_pdf.assert_called_once_with(
        file_path="/tmp/scan.pdf",
        document_id="scan_doc",
        progress_callback=mock_parser.parse_pdf.call_args.kwargs["progress_callback"],
    )
    mock_vector_store.index_chunks.assert_called_once()
    last_update_call = mock_job_repo.update_job_status.call_args_list[-1]
    assert last_update_call.kwargs["status"] == JobStatusEnum.COMPLETED


def test_query_rag_use_case_with_results():
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()

    mock_llm.generate_query_embedding.return_value = [0.2] * 1536
    mock_llm.generate_defensive_answer.return_value = (
        "El sistema hidráulico opera a 250 bar [Fuente: manual.pdf, Pág. 1].",
        False,
    )

    sample_img = ExtractedImage(
        id="img_valve",
        document_id="doc1",
        filename="valve.png",
        page=1,
        bbox=BoundingBox(page=1, x0=10, y0=10, x1=50, y1=50),
        file_path="/tmp/valve.png",
    )

    retrieved_chunk = RetrievedChunk(
        chunk_id="c1",
        document_id="doc1",
        document_name="manual.pdf",
        text="Presión nominal de la válvula hidráulica: 250 bar.",
        page=1,
        bbox=BoundingBox(page=1, x0=10, y0=20, x1=100, y1=150),
        score=0.95,
        associated_images=[sample_img],
    )
    mock_vector_store.hybrid_search.return_value = [retrieved_chunk]

    use_case = QueryRAGUseCase(vector_store=mock_vector_store, llm=mock_llm)

    response = use_case.execute(query="¿Cuál es la presión de la válvula?", top_k=3)

    assert response.query == "¿Cuál es la presión de la válvula?"
    assert "250 bar" in response.answer
    assert len(response.sources) == 1
    assert len(response.images) == 1
    assert response.images[0].id == "img_valve"
    assert response.is_defensive is False


def test_query_rag_use_case_keeps_images_for_defensive_answers():
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()
    mock_llm.generate_query_embedding.return_value = [0.2] * 1536
    mock_llm.generate_defensive_answer.return_value = (
        "No cuento con información suficiente para confirmar el procedimiento.",
        True,
    )
    sample_img = ExtractedImage(
        id="img_process",
        document_id="doc1",
        filename="process.png",
        page=2,
        bbox=BoundingBox(page=2, x0=10, y0=10, x1=200, y1=200),
        file_path="/tmp/process.png",
        url="/api/v1/images/doc1/process.png",
    )
    mock_vector_store.hybrid_search.return_value = [
        RetrievedChunk(
            chunk_id="c-process",
            document_id="doc1",
            document_name="manual.pdf",
            text="El procedimiento se ilustra en el diagrama.",
            page=2,
            bbox=sample_img.bbox,
            score=0.8,
            associated_images=[sample_img],
        )
    ]

    response = QueryRAGUseCase(mock_vector_store, mock_llm).execute(
        query="¿Cómo se realiza el procedimiento?",
        document_ids=["doc1"],
    )

    assert response.is_defensive is True
    assert [image.id for image in response.images] == ["img_process"]


def test_query_rag_use_case_reuses_query_embedding():
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()
    mock_llm.generate_query_embedding.return_value = [0.2] * 1536
    mock_llm.generate_defensive_answer.return_value = ("respuesta", False)
    mock_vector_store.hybrid_search.return_value = []

    use_case = QueryRAGUseCase(vector_store=mock_vector_store, llm=mock_llm)

    use_case.execute(query="  ¿Cuál es la presión? ")
    use_case.execute(query="¿CUÁL ES LA PRESIÓN?")

    mock_llm.generate_query_embedding.assert_called_once()


def test_query_rag_use_case_returns_document_fallback_chunks():
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()
    mock_llm.generate_query_embedding.return_value = [0.2] * 1536
    mock_vector_store.hybrid_search.return_value = [
        RetrievedChunk(
            chunk_id="overview",
            document_id="doc1",
            document_name="manual.pdf",
            text="Documento sobre mantenimiento preventivo.",
            page=1,
            bbox=BoundingBox(page=1, x0=0, y0=0, x1=10, y1=10),
            score=0.01,
        )
    ]
    mock_llm.generate_defensive_answer.return_value = ("Trata sobre mantenimiento.", False)

    use_case = QueryRAGUseCase(vector_store=mock_vector_store, llm=mock_llm)
    response = use_case.execute(
        query="¿De qué habla el documento?",
        document_ids=["doc1"],
    )

    assert response.sources[0].chunk_id == "overview"
    assert response.answer == "Trata sobre mantenimiento."


def test_get_job_status_use_case():
    mock_repo = MagicMock()
    job = IngestionJob(job_id="j1", document_id="d1", filename="test.pdf")
    mock_repo.get_job.return_value = job

    use_case = GetJobStatusUseCase(mock_repo)
    result = use_case.execute("j1")
    assert result.job_id == "j1"
    assert result.filename == "test.pdf"


def test_ingest_document_use_case_cancellation():
    """Verifies that an ingestion job with CANCELLED status halts and does not index vectors."""
    mock_parser = MagicMock()
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()
    mock_job_repo = MagicMock()

    # Job is marked as CANCELLED
    cancelled_job = IngestionJob(
        job_id="j_cancel",
        document_id="d_cancel",
        filename="test.pdf",
        status=JobStatusEnum.CANCELLED,
    )
    mock_job_repo.get_job.return_value = cancelled_job

    use_case = IngestDocumentUseCase(
        parser=mock_parser,
        vector_store=mock_vector_store,
        llm=mock_llm,
        job_repo=mock_job_repo,
    )

    use_case.execute_async("j_cancel", "/tmp/doc.pdf", "d_cancel")

    # Parser and vector store should not be called
    mock_parser.parse_pdf.assert_not_called()
    mock_vector_store.index_chunks.assert_not_called()


def test_ingest_document_use_case_quota_recovery(monkeypatch):
    """Validates that a 429 quota exhaustion pauses the job, sets WAITING_QUOTA, and recovers."""
    import time
    monkeypatch.setattr(time, "sleep", lambda x: None)

    mock_parser = MagicMock()
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()
    mock_job_repo = MagicMock()

    sample_bbox = BoundingBox(page=1, x0=10, y0=20, x1=100, y1=150)
    sample_chunk = Chunk(
        id="c1",
        document_id="doc_quota",
        text="Contenido técnico para indexación",
        page=1,
        bbox=sample_bbox,
    )
    mock_parser.parse_pdf.return_value = ([sample_chunk], [])

    # First call fails with 429 quota exhaustion, second call succeeds
    mock_llm.generate_embeddings.side_effect = [
        Exception("429 RESOURCE_EXHAUSTED Quota exceeded retry in 1s"),
        [[0.1] * 768],
    ]
    mock_vector_store.index_chunks.return_value = 1

    use_case = IngestDocumentUseCase(
        parser=mock_parser,
        vector_store=mock_vector_store,
        llm=mock_llm,
        job_repo=mock_job_repo,
    )

    use_case.execute_async("job_quota_test", "/tmp/quota.pdf", "doc_quota")

    # Verify WAITING_QUOTA was dispatched during recovery
    statuses = [call.kwargs.get("status") for call in mock_job_repo.update_job_status.call_args_list]
    assert JobStatusEnum.WAITING_QUOTA in statuses
    # Verify job ultimately completed
    assert statuses[-1] == JobStatusEnum.COMPLETED
    assert mock_vector_store.index_chunks.call_count == 1


def test_query_rag_retrieves_images_from_page_fallback():
    """Validates that if chunks lack direct image links, images from that page are still retrieved."""
    mock_vector_store = MagicMock()
    mock_llm = MagicMock()

    sample_bbox = BoundingBox(page=2, x0=10, y0=20, x1=100, y1=150)
    chunk = RetrievedChunk(
        chunk_id="c_no_img",
        document_id="doc_img_test",
        document_name="manual.pdf",
        text="Sección técnica con esquema",
        page=2,
        bbox=sample_bbox,
        score=0.95,
        associated_images=[],  # chunk had no direct association
    )

    img = ExtractedImage(
        id="img_p2_1",
        document_id="doc_img_test",
        filename="diagrama_p2.png",
        page=2,
        bbox=sample_bbox,
        file_path="/storage/images/doc_img_test/diagrama_p2.png",
        url="/api/v1/images/doc_img_test/diagrama_p2.png",
    )

    mock_vector_store.hybrid_search.return_value = [chunk]
    mock_vector_store.get_images_for_page.return_value = [img]
    mock_llm.generate_query_embedding.return_value = [0.1] * 768
    mock_llm.generate_defensive_answer.return_value = ("Respuesta técnica sobre el esquema.", False)

    use_case = QueryRAGUseCase(vector_store=mock_vector_store, llm=mock_llm)
    res = use_case.execute(query="¿Cómo funciona el esquema?", top_k=2)

    assert len(res.images) == 1
    assert res.images[0].id == "img_p2_1"
    assert res.images[0].page == 2
