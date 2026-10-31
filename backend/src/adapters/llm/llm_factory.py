import logging
from typing import Dict, Type
from src.adapters.llm.gemini_adapter import GeminiAdapter
from src.adapters.llm.ollama_adapter import OllamaAdapter
from src.adapters.llm.openai_adapter import OpenAIAdapter
from src.infrastructure.config import Settings
from src.ports.llm_port import LLMPort

logger = logging.getLogger(__name__)


# Clase: LLMFactory.
# Entradas: configuración, dependencias o datos definidos por sus atributos.
# Salida: instancia que encapsula el comportamiento o modelo indicado.
class LLMFactory:
    """
    Factory & Registry for dynamically creating LLMPort implementations.
    Enables swapping between cloud LLMs (Gemini, OpenAI) and local LLMs (Ollama)
    purely via environment configuration, without touching any domain or use-case code.
    """

    _registry: Dict[str, Type[LLMPort]] = {
        "gemini": GeminiAdapter,
        "openai": OpenAIAdapter,
        "ollama": OllamaAdapter,
    }

    @classmethod
    def register_provider(cls, name: str, adapter_cls: Type[LLMPort]) -> None:
        """Allows registering custom or 3rd party LLM adapters at runtime."""
        cls._registry[name.lower()] = adapter_cls
        logger.info(f"Registered custom LLM provider: {name}")

    # Objetivo: Create.
    # Entradas: cls, settings.
    # Salida: LLMPort.
    @classmethod
    def create(cls, settings: Settings) -> LLMPort:
        provider = settings.LLM_PROVIDER.lower().strip()
        logger.info(f"LLMFactory: Creating adapter for provider '{provider}'...")

        if provider == "gemini":
            return GeminiAdapter(
                api_key=settings.api_key,
                model=settings.LLM_MODEL,
                embedding_model=settings.EMBEDDING_MODEL,
                embedding_dim=settings.EMBEDDING_DIMENSION,
                max_context_chars=settings.LLM_MAX_CONTEXT_CHARS,
                max_history_chars=settings.LLM_MAX_HISTORY_CHARS,
                max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
                thinking_budget=settings.LLM_THINKING_BUDGET,
            )

        elif provider == "openai":
            return OpenAIAdapter(
                api_key=settings.api_key,
                model=settings.LLM_MODEL,
                embedding_model=settings.EMBEDDING_MODEL,
                embedding_dim=settings.EMBEDDING_DIMENSION,
                max_context_chars=settings.LLM_MAX_CONTEXT_CHARS,
                max_history_chars=settings.LLM_MAX_HISTORY_CHARS,
                max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            )

        elif provider == "ollama":
            base_url = settings.LLM_BASE_URL or "http://localhost:11434"
            return OllamaAdapter(
                base_url=base_url,
                model=settings.LLM_MODEL,
                embedding_model=settings.EMBEDDING_MODEL,
                embedding_dim=settings.EMBEDDING_DIMENSION,
                max_context_chars=settings.LLM_MAX_CONTEXT_CHARS,
                max_history_chars=settings.LLM_MAX_HISTORY_CHARS,
                max_output_tokens=settings.LLM_MAX_OUTPUT_TOKENS,
            )

        elif provider in cls._registry:
            adapter_cls = cls._registry[provider]
            return adapter_cls(
                api_key=settings.api_key,
                model=settings.LLM_MODEL,
                embedding_model=settings.EMBEDDING_MODEL,
                embedding_dim=settings.EMBEDDING_DIMENSION,
            )

        else:
            supported = list(cls._registry.keys())
            raise ValueError(
                f"Unsupported LLM provider '{provider}'. Supported providers are: {supported}"
            )
