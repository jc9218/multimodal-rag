from types import SimpleNamespace

from src.adapters.vector_db.qdrant_adapter import QdrantAdapter
from src.domain.models import BoundingBox, ExtractedImage


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
