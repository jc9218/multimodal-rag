from io import BytesIO

import pytest

from src.adapters.storage import local_storage
from src.adapters.storage.local_storage import (
    LocalStorageAdapter,
    StorageCapacityExceededError,
    UploadSizeExceededError,
)


def test_save_upload_streams_binary_file(tmp_path):
    storage = LocalStorageAdapter(str(tmp_path))

    path = storage.save_upload("document.pdf", BytesIO(b"%PDF-1.7\ncontent"))

    with open(path, "rb") as saved:
        assert saved.read() == b"%PDF-1.7\ncontent"


def test_save_upload_removes_partial_file_when_stream_exceeds_limit(tmp_path, monkeypatch):
    storage = LocalStorageAdapter(str(tmp_path))
    monkeypatch.setattr(
        local_storage,
        "MAX_UPLOAD_SIZE",
        4,
    )

    with pytest.raises(UploadSizeExceededError):
        storage.save_upload("document.pdf", BytesIO(b"%PDF-1.7"))

    assert not (tmp_path / "uploads" / "document.pdf").exists()


def test_save_upload_rejects_when_configured_local_quota_is_exceeded(tmp_path, monkeypatch):
    storage = LocalStorageAdapter(str(tmp_path))
    monkeypatch.setattr(local_storage.settings, "MAX_LOCAL_STORAGE_MB", 0)

    with pytest.raises(StorageCapacityExceededError):
        storage.save_upload("document.pdf", BytesIO(b"%PDF-1.7"))

    assert not (tmp_path / "uploads" / "document.pdf").exists()


def test_image_paths_reject_traversal(tmp_path):
    storage = LocalStorageAdapter(str(tmp_path))

    assert storage.get_image_path("doc-1", "../secret.txt") is None
    with pytest.raises(ValueError):
        storage.save_image("../outside", "image.png", b"data")


def test_image_filename_is_sanitized(tmp_path):
    storage = LocalStorageAdapter(str(tmp_path))

    path = storage.save_image("doc-1", "diagram page.png", b"data")

    assert path.endswith("diagram_page.png")
    assert (tmp_path / "images" / "doc-1" / "diagram_page.png").read_bytes() == b"data"


def test_get_upload_path_recovers_legacy_filename(tmp_path):
    storage = LocalStorageAdapter(str(tmp_path))
    stored = tmp_path / "uploads" / "doc-1_original-name.pdf"
    stored.write_bytes(b"%PDF-1.7")

    assert storage.get_upload_path("doc-1", "renamed.pdf") == str(stored)
