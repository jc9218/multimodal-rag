from src.adapters.llm.prompt_budget import format_context, format_history
from src.domain.models import BoundingBox, RetrievedChunk


def _chunk(text: str) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id="chunk-1",
        document_id="doc-1",
        document_name="manual.pdf",
        text=text,
        page=1,
        bbox=BoundingBox(page=1, x0=0, y0=0, x1=10, y1=10),
        score=1.0,
    )


def test_format_context_respects_character_budget():
    formatted = format_context([_chunk("x" * 1000)], max_context_chars=300)

    assert len(formatted) <= 300
    assert "manual.pdf" in formatted


def test_format_history_uses_recent_items_and_budget():
    history = [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "middle"},
        {"role": "user", "content": "recent"},
    ]

    formatted = format_history(history, max_history_chars=80)

    assert "recent" in formatted
    assert len(formatted) <= len("HISTORIAL PREVIO DE LA CONVERSACIÓN:\n") + 80 + 1
