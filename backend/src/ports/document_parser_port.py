from abc import ABC, abstractmethod
from typing import Callable, List, Optional, Tuple
from src.domain.models import Chunk, ExtractedImage


# Clase: DocumentParserPort.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class DocumentParserPort(ABC):
    @abstractmethod
    def parse_pdf(
        self,
        file_path: str,
        document_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        page_callback: Optional[
            Callable[[int, int, List[Chunk], List[ExtractedImage]], None]
        ] = None,
    ) -> Tuple[List[Chunk], List[ExtractedImage]]:
        """
        Parses a PDF file extracting text chunks with layout/bounding boxes,
        extracts embedded images with page coordinates, and correlates each chunk
        with its closest spatial images.
        """
        pass
