from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from src.domain.models import RetrievedChunk


# Class: LLMPort.
# Inputs: Configuration, dependencies, or data defined by its attributes.
# Output: Instance encapsulating the specified behavior or model.
class LLMPort(ABC):
    @abstractmethod
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a list of strings."""
        pass

    @abstractmethod
    def generate_query_embedding(self, query: str) -> List[float]:
        """Generates embedding for a single user question."""
        pass

    @abstractmethod
    def generate_defensive_answer(
        self,
        query: str,
        context_chunks: List[RetrievedChunk],
        chat_history: Optional[List[dict]] = None,
    ) -> Tuple[str, bool]:
        """
        Generates an answer using defensive prompt engineering.
        Maintains conversational context if chat_history is provided.
        Returns a tuple: (answer_markdown, is_defensive_admission).
        If information is missing, admits it explicitly without hallucinating.
        """
        pass
