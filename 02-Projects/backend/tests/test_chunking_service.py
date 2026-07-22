"""Tests for app.services.chunking_service."""

from app.services.chunking_service import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    build_chunks,
    normalize_line_endings,
)


def assert_slice_invariant(source: str, chunks) -> None:
    normalized = normalize_line_endings(source)
    for chunk in chunks:
        assert normalized[chunk.character_start : chunk.character_end] == chunk.chunk_text
        assert chunk.token_count is None


def test_empty_text_returns_zero_chunks() -> None:
    assert build_chunks("") == []


def test_whitespace_only_returns_zero_chunks() -> None:
    assert build_chunks("   \n\t  \r\n  ") == []


def test_short_text_single_chunk() -> None:
    text = "Hello, world."
    chunks = build_chunks(text)

    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].chunk_text == text
    assert chunks[0].character_start == 0
    assert chunks[0].character_end == len(text)
    assert_slice_invariant(text, chunks)


def test_exactly_1000_characters_single_chunk() -> None:
    text = "a" * 1000
    chunks = build_chunks(text)

    assert len(chunks) == 1
    assert len(chunks[0].chunk_text) == 1000
    assert chunks[0].character_start == 0
    assert chunks[0].character_end == 1000
    assert_slice_invariant(text, chunks)


def test_1001_characters_two_chunks_with_overlap() -> None:
    text = "a" * 1001
    chunks = build_chunks(text)

    assert len(chunks) == 2
    assert chunks[0].character_start == 0
    assert chunks[0].character_end == 1000
    assert chunks[1].character_start == 800
    assert chunks[1].character_end == 1001
    assert len(chunks[0].chunk_text) == 1000
    assert len(chunks[1].chunk_text) == 201
    assert_slice_invariant(text, chunks)


def test_long_multiline_text_respects_chunk_size() -> None:
    paragraph = "word " * 120
    text = (paragraph.strip() + "\n\n") * 20
    chunks = build_chunks(text)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk.chunk_text) <= CHUNK_SIZE
    assert_slice_invariant(text, chunks)


def test_paragraph_boundary_prefers_double_newline() -> None:
    first = "A" * 800
    second = "B" * 50
    text = f"{first}\n\n{second}"
    chunks = build_chunks(text)

    assert len(chunks) == 1
    assert chunks[0].chunk_text == text
    assert "\n\n" in chunks[0].chunk_text
    assert_slice_invariant(text, chunks)


def test_paragraph_boundary_breaks_at_double_newline_when_splitting() -> None:
    first = "A" * 900
    second = "B" * 100
    text = f"{first}\n\n{second}"
    chunks = build_chunks(text)

    assert len(chunks) == 2
    assert chunks[0].character_end == 902
    assert chunks[0].chunk_text.endswith("\n\n")
    assert_slice_invariant(text, chunks)


def test_repeated_text_overlap_geometry() -> None:
    unit = "abc "
    text = unit * 400
    chunks = build_chunks(text)

    assert len(chunks) >= 2
    for index in range(len(chunks) - 1):
        current = chunks[index]
        following = chunks[index + 1]
        overlap = current.character_end - following.character_start
        assert overlap == CHUNK_OVERLAP

        shared = text[following.character_start : current.character_end]
        assert current.chunk_text.endswith(shared)
        assert following.chunk_text.startswith(shared)

    assert_slice_invariant(text, chunks)


def test_unicode_text() -> None:
    text = "Cafe\u0301 resume\u2014 section\n\nEmoji: \U0001F600 " * 50
    chunks = build_chunks(text)

    assert len(chunks) >= 1
    for chunk in chunks:
        assert len(chunk.chunk_text) <= CHUNK_SIZE
    assert_slice_invariant(text, chunks)


def test_line_ending_normalization_before_chunking() -> None:
    text = "Line one\r\nLine two\r\n\r\nLine three"
    chunks = build_chunks(text)

    assert len(chunks) == 1
    assert "\r" not in chunks[0].chunk_text
    assert chunks[0].chunk_text == normalize_line_endings(text)
    assert_slice_invariant(text, chunks)


def test_chunk_indexes_are_sequential() -> None:
    text = "paragraph\n\n" * 300
    chunks = build_chunks(text)

    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert_slice_invariant(text, chunks)


def test_large_paragraph_splits_with_space_or_character_fallback() -> None:
    text = "x" * 1500
    chunks = build_chunks(text)

    assert len(chunks) == 2
    assert chunks[0].character_end == 1000
    assert chunks[1].character_start == 800
    assert_slice_invariant(text, chunks)
