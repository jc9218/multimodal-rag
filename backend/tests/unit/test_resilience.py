from unittest.mock import MagicMock, patch
from openai import RateLimitError
import pytest
from src.adapters.llm.gemini_adapter import GeminiAdapter
from src.adapters.llm.openai_adapter import OpenAIAdapter
from src.domain.exceptions import LLMServiceError


def test_openai_adapter_defensive_admission():
    adapter = OpenAIAdapter(api_key="sk-fake")
    adapter.client = MagicMock()

    # Mock response admitting lack of information
    mock_choice = MagicMock()
    mock_choice.message.content = (
        "Con base en la documentación proporcionada, no cuento con información suficiente "
        "para responder sobre el torque del perno 12."
    )
    adapter.client.chat.completions.create.return_value = MagicMock(choices=[mock_choice])

    answer, is_defensive = adapter.generate_defensive_answer("¿Torque del perno 12?", [])

    assert is_defensive is True
    assert "no cuento con información suficiente" in answer.lower()


def test_gemini_adapter_defensive_admission():
    adapter = GeminiAdapter(api_key="test-key")
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        "Con base en la documentación proporcionada, no cuento con información suficiente "
        "para responder sobre las especificaciones de presión."
    )
    mock_model.generate_content.return_value = mock_response
    adapter._model = mock_model
    adapter._genai = MagicMock()

    answer, is_defensive = adapter.generate_defensive_answer("¿Presión del perno?", [])

    assert is_defensive is True
    assert "no cuento con información suficiente" in answer.lower()


def test_gemini_adapter_uses_primary_model():
    adapter = GeminiAdapter(api_key="test-key", model="gemini-primary")
    adapter._genai_client = MagicMock()
    adapter._call_gemini_model = MagicMock(return_value="Respuesta del modelo principal.")

    answer = adapter._call_gemini_generate("¿De qué trata el documento?")

    assert answer == "Respuesta del modelo principal."
    adapter._call_gemini_model.assert_called_once_with("¿De qué trata el documento?")


def test_gemini_adapter_omits_zero_thinking_budget():
    adapter = GeminiAdapter(api_key="test-key", model="configured-model")
    client = MagicMock()
    response = MagicMock()
    response.text = "Respuesta"
    client.models.generate_content.return_value = response
    adapter._genai_client = client

    adapter._call_gemini_model("Pregunta")

    config = client.models.generate_content.call_args.kwargs["config"]
    assert config.thinking_config is None


def test_openai_adapter_exponential_backoff_retry_on_rate_limit():
    adapter = OpenAIAdapter(api_key="sk-fake")
    adapter.client = MagicMock()

    # Configure client to fail twice with RateLimitError, then succeed
    mock_response = MagicMock()
    mock_data = MagicMock()
    mock_data.embedding = [0.05] * 1536
    mock_response.data = [mock_data]

    mock_rate_limit = RateLimitError(
        message="Rate limit reached",
        response=MagicMock(status_code=429),
        body={},
    )

    adapter.client.embeddings.create.side_effect = [
        mock_rate_limit,
        mock_rate_limit,
        mock_response,
    ]

    # Patch tenacity wait so test doesn't sleep
    with patch("tenacity.nap.time.sleep", return_value=None):
        embeddings = adapter.generate_embeddings(["test technical sentence"])

    assert len(embeddings) == 1
    assert len(embeddings[0]) == 1536
    assert adapter.client.embeddings.create.call_count == 3
