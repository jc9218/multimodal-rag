from __future__ import annotations

from datetime import datetime, timezone

from enum import Enum

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# Class: JobStatusEnum.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class JobStatusEnum(str, Enum):
    PENDING = "PENDING"

    EXTRACTING = "EXTRACTING"

    INDEXING = "INDEXING"

    WAITING_QUOTA = "WAITING_QUOTA"

    COMPLETED = "COMPLETED"

    FAILED = "FAILED"

    CANCELLED = "CANCELLED"


# Class: BoundingBox.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class BoundingBox(BaseModel):
    page: int

    x0: float

    y0: float

    x1: float

    y1: float

    # Purpose: Width.

    # Inputs: self.

    # Output: float.

    @property
    def width(self) -> float:
        """Width.

        Args:

            None.

        Returns:

            float..

        """

        return max(0.0, self.x1 - self.x0)

    # Purpose: Height.

    # Inputs: self.

    # Output: float.

    @property
    def height(self) -> float:
        """Height.

        Args:

            None.

        Returns:

            float..

        """

        return max(0.0, self.y1 - self.y0)

    # Purpose: Center.

    # Inputs: self.

    # Output: tuple[float, float].

    @property
    def center(self) -> tuple[float, float]:
        """Center.

        Args:

            None.

        Returns:

            tuple[float, float]..

        """

        return ((self.x0 + self.x1) / 2.0, (self.y0 + self.y1) / 2.0)

    def distance_to(self, other: BoundingBox) -> float:
        """Euclidean distance between center points (same page)."""

        if self.page != other.page:
            return float("inf")

        c1 = self.center

        c2 = other.center

        return ((c1[0] - c2[0]) ** 2 + (c1[1] - c2[1]) ** 2) ** 0.5


# Class: ExtractedImage.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class ExtractedImage(BaseModel):
    id: str

    document_id: str

    filename: str

    page: int

    bbox: BoundingBox

    file_path: str

    url: Optional[str] = None

    format: str = "png"

    width_px: int = 0

    height_px: int = 0


# Class: Chunk.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class Chunk(BaseModel):
    id: str

    document_id: str

    text: str

    page: int

    bbox: BoundingBox

    associated_images: List[str] = Field(default_factory=list)

    embedding: Optional[List[float]] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)


# Class: Document.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class Document(BaseModel):
    id: str

    filename: str

    total_pages: int

    chunks_count: int = 0

    images_count: int = 0

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Class: IngestionJob.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class IngestionJob(BaseModel):
    job_id: str

    document_id: str

    filename: str

    upload_id: Optional[str] = None

    status: JobStatusEnum = JobStatusEnum.PENDING

    progress: float = 0.0  # 0.0 to 1.0

    message: str = "Job initialized"

    error: Optional[str] = None

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# Class: RetrievedChunk.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class RetrievedChunk(BaseModel):
    chunk_id: str

    document_id: str

    document_name: str

    text: str

    page: int

    bbox: BoundingBox

    score: float

    associated_images: List[ExtractedImage] = Field(default_factory=list)


# Class: QueryResponse.

# Inputs: Configuration, dependencies, or data defined by its attributes.

# Output: Instance encapsulating the specified behavior or model.


class QueryResponse(BaseModel):
    query: str

    answer: str

    sources: List[RetrievedChunk] = Field(default_factory=list)

    images: List[ExtractedImage] = Field(default_factory=list)

    is_defensive: bool = False
