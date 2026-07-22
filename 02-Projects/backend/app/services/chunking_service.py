"""Custom recursive character chunking for document extracted text."""

from dataclasses import dataclass
from typing import Optional

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
SEPARATORS = ["\n\n", "\n", " ", ""]


@dataclass(frozen=True)
class ChunkRecord:
    chunk_index: int
    chunk_text: str
    character_start: int
    character_end: int
    token_count: Optional[int] = None


def normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def build_chunks(extracted_text: str) -> list[ChunkRecord]:
    """
    Split extracted text into overlapping chunks with exact source offsets.

    Empty or whitespace-only input returns zero chunks.
    """
    text = normalize_line_endings(extracted_text)
    if not text.strip():
        return []

    chunks: list[ChunkRecord] = []
    start = 0
    text_length = len(text)
    chunk_index = 0

    while start < text_length:
        max_end = min(start + CHUNK_SIZE, text_length)

        if max_end == text_length:
            end = text_length
        else:
            end = _find_break_point(text, start, max_end, SEPARATORS)
            if end <= start:
                end = min(start + 1, text_length)

        chunk_text = text[start:end]
        chunks.append(
            ChunkRecord(
                chunk_index=chunk_index,
                chunk_text=chunk_text,
                character_start=start,
                character_end=end,
                token_count=None,
            )
        )
        chunk_index += 1

        if end >= text_length:
            break

        next_start = end - CHUNK_OVERLAP
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def _find_break_point(
    text: str,
    start: int,
    max_end: int,
    separators: list[str],
) -> int:
    """
    Recursively choose a break point using separator priority.

    Searches backward in text[start:max_end] for the last occurrence of the
    current separator. Falls through to the next separator, then to max_end
    for character-level splitting.
    """
    if not separators:
        return max_end

    separator, *remaining_separators = separators

    if separator == "":
        return max_end

    window = text[start:max_end]
    separator_index = window.rfind(separator)

    if separator_index != -1:
        break_end = start + separator_index + len(separator)
        if break_end > start:
            return break_end

    return _find_break_point(text, start, max_end, remaining_separators)
