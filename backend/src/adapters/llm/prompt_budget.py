from typing import List, Optional

from src.domain.models import RetrievedChunk


DEFAULT_MAX_CONTEXT_CHARS = 12000
DEFAULT_MAX_HISTORY_CHARS = 2400
DEFAULT_MAX_CHUNK_CHARS = 3500
DEFAULT_MAX_OUTPUT_TOKENS = 512


def format_context(
    context_chunks: List[RetrievedChunk],
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
    max_chunk_chars: int = DEFAULT_MAX_CHUNK_CHARS,
) -> str:
    """
    Formats retrieved document chunks with explicit XML boundary tags.
    Sanitizes untrusted text to prevent XML breakout or indirect prompt injection.
    Strictly adheres to max_context_chars budget.
    """
    if not context_chunks:
        empty = "<document_context></document_context>"
        return empty[:max_context_chars]

    header = "<document_context>\n"
    footer = "\n</document_context>"
    base_overhead = len(header) + len(footer)

    if max_context_chars <= base_overhead:
        return (header + footer)[:max_context_chars]

    available_chars = max_context_chars - base_overhead
    parts: List[str] = []
    used_chars = 0

    for index, chunk in enumerate(context_chunks, 1):
        remaining = available_chars - used_chars
        if remaining <= 0:
            break
        text_limit = min(max_chunk_chars, max(0, remaining))
        # Sanitize closing XML tags inside untrusted document text to prevent delimiter breakout
        safe_text = (
            chunk.text[:text_limit]
            .replace("</document_context>", "[/document_context]")
            .replace("<document_context>", "[document_context]")
            .replace("</chunk>", "[/chunk]")
            .replace("<chunk>", "[chunk]")
        )
        part = (
            f'  <chunk index="{index}" document="{chunk.document_name}" page="{chunk.page}">\n'
            f"    {safe_text}\n"
            f"  </chunk>"
        )
        if len(part) > remaining:
            part = part[:remaining]
        parts.append(part)
        used_chars += len(part)

    result = header + "\n".join(parts) + footer
    return result[:max_context_chars]


def format_history(
    chat_history: Optional[List[dict]],
    max_history_chars: int = DEFAULT_MAX_HISTORY_CHARS,
) -> str:
    """
    Formats recent conversation history, sanitizing user-provided strings
    to neutralize delimiter injection attempts. Strictly adheres to max_history_chars.
    """
    if not chat_history:
        return ""

    lines: List[str] = []
    used_chars = 0
    for item in chat_history[-4:]:
        role = "Usuario" if item.get("role") in ["user", "human"] else "Asistente"
        raw_text = item.get("content", item.get("text", "")).strip()
        if not raw_text:
            continue
        # Neutralize XML tag spoofing in conversation history
        safe_text = (
            raw_text.replace("</document_context>", "[/document_context]")
            .replace("<document_context>", "[document_context]")
            .replace("</user_query>", "[/user_query]")
            .replace("<user_query>", "[user_query]")
            .replace("</conversation_history>", "[/conversation_history]")
            .replace("<conversation_history>", "[conversation_history]")
        )
        line = f"{role}: {safe_text}\n"
        remaining = max_history_chars - used_chars
        if remaining <= 0:
            break
        lines.append(line[:remaining])
        used_chars += min(len(line), remaining)

    if not lines:
        return ""
    return "HISTORIAL PREVIO DE LA CONVERSACIÓN:\n" + "".join(lines) + "\n"
