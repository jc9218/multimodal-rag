import os

import pytest
from src.adapters.llm.gemini_adapter import GeminiAdapter
from src.adapters.llm.llm_factory import LLMFactory
from src.adapters.llm.ollama_adapter import OllamaAdapter
from src.adapters.llm.openai_adapter import OpenAIAdapter
from src.infrastructure.config import Settings
from src.ports.llm_port import LLMPort


LLM_MODEL = os.getenv("LLM_MODEL", "")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "")


def test_llm_factory_creates_gemini():
    settings = Settings(
        LLM_PROVIDER="gemini",
        LLM_PROVIDER_API_KEY="fake-gemini-key",
        LLM_MODEL=LLM_MODEL,
        EMBEDDING_MODEL=EMBEDDING_MODEL,
        EMBEDDING_DIMENSION=768,
    )
    llm = LLMFactory.create(settings)
    assert isinstance(llm, LLMPort)
    assert isinstance(llm, GeminiAdapter)


def test_llm_factory_creates_openai():
    settings = Settings(
        LLM_PROVIDER="openai",
        LLM_PROVIDER_API_KEY="fake-openai-key",
        LLM_MODEL=LLM_MODEL,
        EMBEDDING_MODEL=EMBEDDING_MODEL,
        EMBEDDING_DIMENSION=1536,
    )
    llm = LLMFactory.create(settings)
    assert isinstance(llm, LLMPort)
    assert isinstance(llm, OpenAIAdapter)


def test_llm_factory_creates_ollama():
    settings = Settings(
        LLM_PROVIDER="ollama",
        LLM_BASE_URL="http://localhost:11434",
        LLM_MODEL=LLM_MODEL,
        EMBEDDING_MODEL=EMBEDDING_MODEL,
        EMBEDDING_DIMENSION=768,
    )
    llm = LLMFactory.create(settings)
    assert isinstance(llm, LLMPort)
    assert isinstance(llm, OllamaAdapter)


def test_llm_factory_invalid_provider_raises_error():
    settings = Settings(
        LLM_PROVIDER="unknown_provider",
        LLM_MODEL="dummy",
        EMBEDDING_MODEL="dummy",
        EMBEDDING_DIMENSION=768,
    )
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        LLMFactory.create(settings)
