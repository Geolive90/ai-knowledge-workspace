"""Unit tests for VectorStore behavior using FakeVectorStore."""

import pytest

from app.services.vector_store.exceptions import (
    VectorStoreDimensionMismatchError,
    VectorStoreDuplicateIdError,
)
from app.services.vector_store.provider import VectorAddItem


def test_add_and_count(fake_vector_store) -> None:
    fake_vector_store.add(
        [
            VectorAddItem(chunk_id=1, vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            VectorAddItem(chunk_id=2, vector=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ]
    )

    assert fake_vector_store.count == 2


def test_search_returns_neighbors_best_first(fake_vector_store) -> None:
    fake_vector_store.add(
        [
            VectorAddItem(chunk_id=1, vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            VectorAddItem(chunk_id=2, vector=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            VectorAddItem(chunk_id=3, vector=[0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ]
    )

    results = fake_vector_store.search([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], k=3)

    assert [result.chunk_id for result in results] == [1, 3, 2]
    assert results[0].score > results[1].score > results[2].score


def test_dimension_mismatch_on_add(fake_vector_store) -> None:
    with pytest.raises(VectorStoreDimensionMismatchError):
        fake_vector_store.add(
            [VectorAddItem(chunk_id=1, vector=[1.0, 0.0, 0.0])]
        )


def test_dimension_mismatch_on_search(fake_vector_store) -> None:
    fake_vector_store.add(
        [VectorAddItem(chunk_id=1, vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])]
    )

    with pytest.raises(VectorStoreDimensionMismatchError):
        fake_vector_store.search([1.0, 0.0, 0.0], k=1)


def test_duplicate_chunk_id_raises(fake_vector_store) -> None:
    vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    fake_vector_store.add([VectorAddItem(chunk_id=42, vector=vector)])

    with pytest.raises(VectorStoreDuplicateIdError):
        fake_vector_store.add([VectorAddItem(chunk_id=42, vector=vector)])


def test_duplicate_chunk_id_in_same_batch_raises(fake_vector_store) -> None:
    vector = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    with pytest.raises(VectorStoreDuplicateIdError):
        fake_vector_store.add(
            [
                VectorAddItem(chunk_id=42, vector=vector),
                VectorAddItem(chunk_id=42, vector=vector),
            ]
        )


def test_remove_by_chunk_ids_is_idempotent(fake_vector_store) -> None:
    fake_vector_store.add(
        [
            VectorAddItem(chunk_id=1, vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            VectorAddItem(chunk_id=2, vector=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
        ]
    )

    removed = fake_vector_store.remove_by_chunk_ids([1, 99])
    again = fake_vector_store.remove_by_chunk_ids([1, 99])

    assert removed == 1
    assert again == 0
    assert fake_vector_store.count == 1


def test_clear_resets_count(fake_vector_store) -> None:
    fake_vector_store.add(
        [VectorAddItem(chunk_id=1, vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])]
    )

    fake_vector_store.clear()

    assert fake_vector_store.count == 0


def test_empty_search_returns_empty_list(fake_vector_store) -> None:
    assert fake_vector_store.search([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], k=5) == []


def test_non_positive_k_returns_empty_list(fake_vector_store) -> None:
    fake_vector_store.add(
        [VectorAddItem(chunk_id=1, vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])]
    )

    assert fake_vector_store.search([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], k=0) == []
