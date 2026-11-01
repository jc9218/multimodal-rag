import os

import re

import shutil

from typing import BinaryIO, Optional, Union

from src.ports.storage_port import StoragePort

from src.infrastructure.config import settings

MAX_UPLOAD_SIZE = settings.max_upload_size_bytes

# Class: UploadSizeExceededError.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class UploadSizeExceededError(ValueError):
    """Raised when a streamed upload exceeds the configured safety limit."""


# Class: StorageCapacityExceededError.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class StorageCapacityExceededError(ValueError):
    """Raised when local storage cannot safely accept another artifact."""


# Class: LocalStorageAdapter.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class LocalStorageAdapter(StoragePort):
    # Purpose: Init.

    # Inputs: self, base_storage_path.

    # Output: Operation result, or None when no value is returned.

    def __init__(self, base_storage_path: str = "./storage"):
        """init.

        Args:

            base_storage_path: str.

        Returns:

            unspecified..

        """

        self.base_path = os.path.abspath(base_storage_path)

        self.uploads_dir = os.path.join(self.base_path, "uploads")

        self.images_dir = os.path.join(self.base_path, "images")

        os.makedirs(self.uploads_dir, exist_ok=True)

        os.makedirs(self.images_dir, exist_ok=True)

    # Purpose: Ensure capacity.

    # Inputs: self, additional_bytes.

    # Output: None.

    def _ensure_capacity(self, additional_bytes: int) -> None:
        """ensure capacity.

        Args:

            additional_bytes: int.

        Returns:

            None..

        """

        usage = shutil.disk_usage(self.base_path)

        configured_limit = settings.MAX_LOCAL_STORAGE_MB * 1024 * 1024

        current_usage = 0

        for root, _, files in os.walk(self.base_path):
            for name in files:
                try:
                    current_usage += os.path.getsize(os.path.join(root, name))

                except OSError:
                    continue

        minimum_free = settings.MIN_FREE_STORAGE_MB * 1024 * 1024

        if (
            current_usage + additional_bytes > configured_limit
            or usage.free - additional_bytes < minimum_free
        ):
            raise StorageCapacityExceededError(
                "Local storage capacity is insufficient for this artifact."
            )

    # Purpose: Save upload.

    # Inputs: self, filename, content.

    # Output: str.

    def save_upload(self, filename: str, content: Union[bytes, BinaryIO]) -> str:
        """Save upload.

        Args:

            filename: str, content: Union[bytes, BinaryIO].

        Returns:

            str..

        """

        safe_filename = os.path.basename(filename)

        dest_path = os.path.join(self.uploads_dir, safe_filename)

        try:
            with open(dest_path, "wb") as f:
                if isinstance(content, (bytes, bytearray)):
                    if len(content) > MAX_UPLOAD_SIZE:
                        raise UploadSizeExceededError

                    self._ensure_capacity(len(content))

                    f.write(content)

                else:
                    total_bytes = 0

                    while chunk := content.read(64 * 1024):
                        total_bytes += len(chunk)

                        if total_bytes > MAX_UPLOAD_SIZE:
                            raise UploadSizeExceededError

                        self._ensure_capacity(len(chunk))

                        f.write(chunk)

        except Exception:
            if os.path.exists(dest_path):
                os.remove(dest_path)

            raise

        return dest_path

    # Purpose: Save image.

    # Inputs: self, document_id, image_filename, image_bytes.

    # Output: str.

    def save_image(
        self, document_id: str, image_filename: str, image_bytes: bytes
    ) -> str:
        """Save image.

        Args:

            document_id: str, image_filename: str, image_bytes: bytes.

        Returns:

            str..

        """

        safe_document_id = os.path.basename(document_id)

        safe_image_filename = re.sub(
            r"[^A-Za-z0-9._-]", "_", os.path.basename(image_filename)
        )

        if (
            not safe_document_id
            or safe_document_id != document_id
            or not safe_image_filename
        ):
            raise ValueError("Identificador o nombre de imagen no válido")

        doc_img_dir = os.path.join(self.images_dir, safe_document_id)

        os.makedirs(doc_img_dir, exist_ok=True)

        dest_path = os.path.join(doc_img_dir, safe_image_filename)

        self._ensure_capacity(len(image_bytes))

        with open(dest_path, "wb") as f:
            f.write(image_bytes)

        return dest_path

    # Purpose: Get image path.

    # Inputs: self, document_id, image_filename.

    # Output: Optional[str].

    def get_image_path(self, document_id: str, image_filename: str) -> Optional[str]:
        """Get image path.

        Args:

            document_id: str, image_filename: str.

        Returns:

            Optional[str]..

        """

        safe_document_id = os.path.basename(document_id)

        safe_image_filename = os.path.basename(image_filename)

        if safe_document_id != document_id or safe_image_filename != image_filename:
            return None

        image_dir = os.path.realpath(os.path.join(self.images_dir, safe_document_id))

        path = os.path.realpath(os.path.join(image_dir, safe_image_filename))

        if os.path.commonpath((image_dir, path)) != image_dir:
            return None

        return path if os.path.exists(path) else None

    # Purpose: Get upload path.

    # Inputs: self, document_id, filename.

    # Output: Optional[str].

    def get_upload_path(self, document_id: str, filename: str) -> Optional[str]:
        """Get upload path.

        Args:

            document_id: str, filename: str.

        Returns:

            Optional[str]..

        """

        safe_document_id = os.path.basename(document_id)

        safe_filename = os.path.basename(filename)

        if safe_document_id != document_id or safe_filename != filename:
            return None

        uploads_dir = os.path.realpath(self.uploads_dir)

        expected_path = os.path.realpath(
            os.path.join(uploads_dir, f"{document_id}_{safe_filename}")
        )

        if os.path.commonpath((uploads_dir, expected_path)) != uploads_dir:
            return None

        if os.path.isfile(expected_path):
            return expected_path

        # Recover jobs even if a legacy upload stored a normalized filename.

        prefix = f"{document_id}_"

        for stored_name in os.listdir(uploads_dir):
            if not stored_name.startswith(prefix) or not stored_name.lower().endswith(
                ".pdf"
            ):
                continue

            candidate = os.path.realpath(os.path.join(uploads_dir, stored_name))

            if os.path.commonpath(
                (uploads_dir, candidate)
            ) == uploads_dir and os.path.isfile(candidate):
                return candidate

        return None

    # Purpose: Delete document files.

    # Inputs: self, document_id.

    # Output: None.

    def delete_document_files(self, document_id: str) -> None:
        """Delete document files.

        Args:

            document_id: str.

        Returns:

            None..

        """

        import shutil

        # 1. Delete extracted images directory

        doc_img_dir = os.path.join(self.images_dir, document_id)

        if os.path.exists(doc_img_dir):
            shutil.rmtree(doc_img_dir, ignore_errors=True)

        # 2. Delete uploaded PDF file if it starts with document_id

        if os.path.exists(self.uploads_dir):
            for fname in os.listdir(self.uploads_dir):
                if fname.startswith(f"{document_id}_"):
                    try:
                        os.remove(os.path.join(self.uploads_dir, fname))

                    except Exception:
                        pass

    def list_uploaded_documents(self) -> list:
        """Lists uploaded documents found in uploads_dir with their original human-readable filename."""

        from datetime import datetime, timezone

        docs = []

        if os.path.exists(self.uploads_dir):
            for fname in sorted(os.listdir(self.uploads_dir)):
                if not fname.lower().endswith(".pdf"):
                    continue

                if "_" in fname:
                    parts = fname.split("_", 1)

                    did = parts[0]

                    original_name = parts[1]

                else:
                    did = fname

                    original_name = fname

                fpath = os.path.join(self.uploads_dir, fname)

                try:
                    mtime = datetime.fromtimestamp(
                        os.path.getmtime(fpath), timezone.utc
                    ).isoformat()

                except Exception:
                    mtime = datetime.now(timezone.utc).isoformat()

                docs.append(
                    {
                        "id": did,
                        "name": original_name,
                        "created_at": mtime,
                    }
                )

        return docs
