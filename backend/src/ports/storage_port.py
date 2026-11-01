from abc import ABC, abstractmethod
from typing import BinaryIO, Optional, Union


# Class: StoragePort.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class StoragePort(ABC):
    @abstractmethod
    def save_upload(self, filename: str, content: Union[bytes, BinaryIO]) -> str:
        """Saves an uploaded PDF and returns its absolute path."""
        pass

    @abstractmethod
    def save_image(self, document_id: str, image_filename: str, image_bytes: bytes) -> str:
        """Saves an extracted image and returns its relative or absolute path."""
        pass

    # Purpose: Get image path.
    # Inputs: self, document_id, image_filename.
    # Output: Optional[str].
    @abstractmethod
    def get_image_path(self, document_id: str, image_filename: str) -> Optional[str]:
        pass

    @abstractmethod
    def get_upload_path(self, document_id: str, filename: str) -> Optional[str]:
        """Returns the persisted upload path for a document, if it exists."""
        pass

    @abstractmethod
    def delete_document_files(self, document_id: str) -> None:
        """Deletes upload files and image directories associated with document_id."""
        pass

    @abstractmethod
    def list_uploaded_documents(self) -> list:
        """Lists uploaded documents stored on disk with original filenames."""
        pass
