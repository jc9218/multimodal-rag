import os
import re
import tempfile
import unicodedata
from typing import BinaryIO, Optional, Union

import httpx
import logging

from src.adapters.storage.local_storage import (
    LocalStorageAdapter,
    MAX_UPLOAD_SIZE,
    UploadSizeExceededError,
)

logger = logging.getLogger(__name__)


class SupabaseStorageError(RuntimeError):
    """Raised when Supabase rejects or cannot persist a storage object."""


# Clase: SupabaseStorageAdapter.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class SupabaseStorageAdapter(LocalStorageAdapter):
    """Stores source PDFs in Supabase Storage and uses local disk for derived files."""

    # Objetivo: Init.
    # Entradas: self, base_storage_path, supabase_url, service_role_key, bucket.
    # Salida: Resultado de la operación o None si no retorna un valor..
    def __init__(
        self,
        base_storage_path: str,
        supabase_url: str,
        service_role_key: str,
        bucket: str,
    ):
        if not supabase_url or not service_role_key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required for Supabase storage."
            )
        super().__init__(base_storage_path)
        self._object_url = (
            f"{supabase_url.rstrip('/')}/storage/v1/object/{bucket}"
        )
        self._list_url = f"{supabase_url.rstrip('/')}/storage/v1/object/list/{bucket}"
        self._headers = {
            "Authorization": "Bearer " + service_role_key,
            "apikey": service_role_key,
        }

    @staticmethod
    def _safe_object_filename(filename: str) -> str:
        normalized = unicodedata.normalize("NFKD", os.path.basename(filename))
        ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", ascii_name)
        if not safe_name.lower().endswith(".pdf"):
            safe_name = f"{safe_name}.pdf"
        return safe_name

    # Objetivo: Save upload.
    # Entradas: self, filename, content.
    # Salida: str.
    def save_upload(self, filename: str, content: Union[bytes, BinaryIO]) -> str:
        safe_filename = self._safe_object_filename(filename)
        object_url = f"{self._object_url}/uploads/{safe_filename}"
        self._ensure_capacity(MAX_UPLOAD_SIZE)
        with tempfile.NamedTemporaryFile(
            mode="w+b", dir=self.uploads_dir, prefix=".upload-", delete=False
        ) as temp_file:
            temp_path = temp_file.name
            try:
                total = 0
                if isinstance(content, (bytes, bytearray)):
                    chunks = [bytes(content)]
                else:
                    chunks = iter(lambda: content.read(64 * 1024), b"")
                for chunk in chunks:
                    total += len(chunk)
                    if total > MAX_UPLOAD_SIZE:
                        raise UploadSizeExceededError
                    temp_file.write(chunk)
                temp_file.flush()
                temp_file.seek(0)
                response = httpx.put(
                    object_url,
                    headers={
                        **self._headers,
                        "Content-Type": "application/pdf",
                        "x-upsert": "true",
                    },
                    content=temp_file,
                    timeout=60.0,
                )
                if response.is_error:
                    detail = response.text[:500]
                    logger.error(
                        "Supabase upload rejected object path=%s status=%s response=%s",
                        f"uploads/{safe_filename}",
                        response.status_code,
                        detail,
                    )
                    raise SupabaseStorageError(
                        f"Supabase rechazó el archivo ({response.status_code}): {detail}"
                    )
                local_path = os.path.join(self.uploads_dir, safe_filename)
                temp_file.seek(0)
                with open(local_path, "wb") as local_file:
                    while chunk := temp_file.read(64 * 1024):
                        local_file.write(chunk)
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
        return local_path

    # Objetivo: Cleanup local cache.
    # Entradas: self, document_id.
    # Salida: None.
    def cleanup_local_cache(self, document_id: str) -> None:
        super().delete_document_files(document_id)

    # Objetivo: Get upload path.
    # Entradas: self, document_id, filename.
    # Salida: Optional[str].
    def get_upload_path(self, document_id: str, filename: str) -> Optional[str]:
        safe_filename = os.path.basename(filename)
        if safe_filename != filename:
            return None
        object_name = f"{document_id}_{self._safe_object_filename(filename)}"
        local_path = os.path.join(self.uploads_dir, object_name)
        try:
            response = httpx.get(
                f"{self._object_url}/uploads/{object_name}",
                headers=self._headers,
                timeout=60.0,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            self._ensure_capacity(len(response.content))
            with open(local_path, "wb") as downloaded:
                downloaded.write(response.content)
            return local_path
        except httpx.HTTPError:
            return None

    # Objetivo: Save image.
    # Entradas: self, document_id, image_filename, image_bytes.
    # Salida: str.
    def save_image(self, document_id: str, image_filename: str, image_bytes: bytes) -> str:
        safe_document_id = os.path.basename(document_id)
        safe_image_filename = re.sub(
            r"[^A-Za-z0-9._-]", "_", os.path.basename(image_filename)
        )
        if safe_document_id != document_id or not safe_image_filename:
            raise ValueError("Identificador o nombre de imagen no válido")
        object_name = f"images/{safe_document_id}/{safe_image_filename}"
        response = httpx.put(
            f"{self._object_url}/{object_name}",
            headers={
                **self._headers,
                "Content-Type": "image/png",
                "x-upsert": "true",
            },
            content=image_bytes,
            timeout=60.0,
        )
        response.raise_for_status()
        return f"supabase://{object_name}"

    # Objetivo: Get image path.
    # Entradas: self, document_id, image_filename.
    # Salida: Optional[str].
    def get_image_path(self, document_id: str, image_filename: str) -> Optional[str]:
        safe_document_id = os.path.basename(document_id)
        safe_image_filename = os.path.basename(image_filename)
        if safe_document_id != document_id or safe_image_filename != image_filename:
            return None
        local_dir = os.path.join(self.images_dir, safe_document_id)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, safe_image_filename)
        if os.path.isfile(local_path):
            return local_path
        try:
            response = httpx.get(
                f"{self._object_url}/images/{safe_document_id}/{safe_image_filename}",
                headers=self._headers,
                timeout=60.0,
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            with open(local_path, "wb") as downloaded:
                downloaded.write(response.content)
            return local_path
        except httpx.HTTPError:
            return None

    # Objetivo: Delete document files.
    # Entradas: self, document_id.
    # Salida: None.
    def delete_document_files(self, document_id: str) -> None:
        try:
            object_paths: list[str] = []
            for prefix in (f"uploads/{document_id}_", f"images/{document_id}/"):
                response = httpx.post(
                    self._list_url,
                    headers={**self._headers, "Content-Type": "application/json"},
                    json={"prefix": prefix, "limit": 1000},
                    timeout=30.0,
                )
                response.raise_for_status()
                for item in response.json():
                    if isinstance(item, dict) and item.get("name"):
                        item_name = str(item["name"]).lstrip("/")
                        object_paths.append(
                            item_name
                            if item_name.startswith(prefix)
                            else f"{prefix}{item_name}"
                        )

            if object_paths:
                response = httpx.post(
                    f"{self._object_url}/remove",
                    headers={**self._headers, "Content-Type": "application/json"},
                    json=object_paths,
                    timeout=30.0,
                )
                response.raise_for_status()
        except httpx.HTTPError:
            logger.exception(
                "Could not remove Supabase objects for document_id=%s",
                document_id,
            )
        finally:
            super().delete_document_files(document_id)
