"""Optional integration tests for FaissVectorStore."""

import os

import pytest

from app.services.vector_store.exceptions import (
    VectorStoreDimensionMismatchError,
    VectorStoreDuplicateIdError,
    VectorStoreLoadError,
)
from app.services.vector_store.factory import clear_vector_store_caches
from app.services.vector_store.provider import VectorAddItem
from app.services.vector_store.providers.faiss import FaissVectorStore

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_FAISS_INTEGRATION") != "1",
    reason="Set RUN_FAISS_INTEGRATION=1 to run FAISS integration tests.",
)

DIMENSIONS = 4
SCORE_TOLERANCE = 1e-5


def _make_store(index_path, dimensions: int = DIMENSIONS) -> FaissVectorStore:
    return FaissVectorStore(dimensions=dimensions, index_path=index_path)


def _unit_vector(first: float, second: float = 0.0, third: float = 0.0) -> list[float]:
    return [first, second, third, 0.0]


def test_add_and_search_preserves_neighbor_ordering(tmp_path) -> None:
    index_path = tmp_path / "ordering.faiss"
    store = _make_store(index_path)
    store.add(
        [
            VectorAddItem(chunk_id=1, vector=_unit_vector(1.0, 0.0)),
            VectorAddItem(chunk_id=2, vector=_unit_vector(0.0, 1.0)),
            VectorAddItem(chunk_id=3, vector=_unit_vector(0.9, 0.1)),
        ]
    )

    results = store.search(_unit_vector(1.0, 0.0), k=3)

    assert [result.chunk_id for result in results] == [1, 3, 2]
    assert results[0].score > results[1].score > results[2].score


def test_chunk_id_preserved_in_search_results(tmp_path) -> None:
    store = _make_store(tmp_path / "ids.faiss")
    store.add([VectorAddItem(chunk_id=101, vector=_unit_vector(1.0))])

    results = store.search(_unit_vector(1.0), k=1)

    assert len(results) == 1
    assert results[0].chunk_id == 101


def test_dimension_mismatch_rejected_on_add_and_search(tmp_path) -> None:
    store = _make_store(tmp_path / "dim.faiss")

    with pytest.raises(VectorStoreDimensionMismatchError):
        store.add([VectorAddItem(chunk_id=1, vector=[1.0, 0.0, 0.0])])

    store.add([VectorAddItem(chunk_id=1, vector=_unit_vector(1.0))])

    with pytest.raises(VectorStoreDimensionMismatchError):
        store.search([1.0, 0.0, 0.0], k=1)


def test_persistence_invariant_across_reload(tmp_path) -> None:
    index_path = tmp_path / "persist.faiss"
    store = _make_store(index_path)
    query = _unit_vector(1.0, 0.0)
    store.add(
        [
            VectorAddItem(chunk_id=1, vector=_unit_vector(1.0, 0.0)),
            VectorAddItem(chunk_id=2, vector=_unit_vector(0.0, 1.0)),
            VectorAddItem(chunk_id=3, vector=_unit_vector(0.9, 0.1)),
        ]
    )

    before = store.search(query, k=3)
    store.save()

    reloaded = _make_store(index_path)
    reloaded.load()
    after = reloaded.search(query, k=3)

    assert [result.chunk_id for result in after] == [result.chunk_id for result in before]
    assert [result.score for result in after] == pytest.approx(
        [result.score for result in before],
        abs=SCORE_TOLERANCE,
    )


def test_remove_by_chunk_ids(tmp_path) -> None:
    store = _make_store(tmp_path / "remove.faiss")
    store.add(
        [
            VectorAddItem(chunk_id=1, vector=_unit_vector(1.0)),
            VectorAddItem(chunk_id=2, vector=_unit_vector(0.0, 1.0)),
        ]
    )

    removed = store.remove_by_chunk_ids([1, 99])
    results = store.search(_unit_vector(1.0), k=2)

    assert removed == 1
    assert store.count == 1
    assert [result.chunk_id for result in results] == [2]


def test_duplicate_chunk_id_raises(tmp_path) -> None:
    store = _make_store(tmp_path / "duplicate.faiss")
    vector = _unit_vector(1.0)
    store.add([VectorAddItem(chunk_id=7, vector=vector)])

    with pytest.raises(VectorStoreDuplicateIdError):
        store.add([VectorAddItem(chunk_id=7, vector=vector)])


def test_duplicate_chunk_id_in_same_batch_raises(tmp_path) -> None:
    store = _make_store(tmp_path / "duplicate-batch.faiss")
    vector = _unit_vector(1.0)

    with pytest.raises(VectorStoreDuplicateIdError):
        store.add(
            [
                VectorAddItem(chunk_id=7, vector=vector),
                VectorAddItem(chunk_id=7, vector=vector),
            ]
        )


def test_empty_index_search_returns_empty_list(tmp_path) -> None:
    store = _make_store(tmp_path / "empty.faiss")

    assert store.search(_unit_vector(1.0), k=5) == []


def test_missing_index_file_starts_empty(tmp_path) -> None:
    index_path = tmp_path / "missing.faiss"
    store = _make_store(index_path)

    store.load()

    assert store.count == 0
    assert store.search(_unit_vector(1.0), k=1) == []


def test_corrupt_index_file_raises_load_error(tmp_path) -> None:
    index_path = tmp_path / "corrupt.faiss"
    index_path.write_text("not-a-faiss-index", encoding="utf-8")
    store = _make_store(index_path)

    with pytest.raises(VectorStoreLoadError):
        store.load()


def test_loaded_index_with_wrong_dimensions_raises_load_error(tmp_path) -> None:
    index_path = tmp_path / "wrong-dim.faiss"
    writer = _make_store(index_path, dimensions=4)
    writer.add([VectorAddItem(chunk_id=1, vector=_unit_vector(1.0))])
    writer.save()

    reader = _make_store(index_path, dimensions=8)

    with pytest.raises(VectorStoreLoadError):
        reader.load()


def test_clear_resets_index(tmp_path) -> None:
    store = _make_store(tmp_path / "clear.faiss")
    store.add([VectorAddItem(chunk_id=1, vector=_unit_vector(1.0))])

    store.clear()

    assert store.count == 0


def test_zero_norm_vector_rejected_on_add(tmp_path) -> None:
    from app.services.vector_store.exceptions import VectorStoreProviderError

    store = _make_store(tmp_path / "zero-add.faiss")

    with pytest.raises(VectorStoreProviderError):
        store.add([VectorAddItem(chunk_id=1, vector=[0.0, 0.0, 0.0, 0.0])])


def test_zero_norm_query_rejected_on_search(tmp_path) -> None:
    from app.services.vector_store.exceptions import VectorStoreProviderError

    store = _make_store(tmp_path / "zero-search.faiss")
    store.add([VectorAddItem(chunk_id=1, vector=_unit_vector(1.0))])

    with pytest.raises(VectorStoreProviderError):
        store.search([0.0, 0.0, 0.0, 0.0], k=1)


def test_invalid_batch_does_not_mutate_index(tmp_path) -> None:
    store = _make_store(tmp_path / "batch-no-mutate.faiss")
    valid = _unit_vector(1.0)

    with pytest.raises(VectorStoreDimensionMismatchError):
        store.add(
            [
                VectorAddItem(chunk_id=1, vector=valid),
                VectorAddItem(chunk_id=2, vector=[1.0, 0.0, 0.0]),
            ]
        )
    assert store.count == 0

    store.add([VectorAddItem(chunk_id=1, vector=valid)])
    assert store.count == 1

    with pytest.raises(VectorStoreDuplicateIdError):
        store.add(
            [
                VectorAddItem(chunk_id=2, vector=_unit_vector(0.0, 1.0)),
                VectorAddItem(chunk_id=1, vector=valid),
            ]
        )
    assert store.count == 1


def test_load_missing_file_clears_in_memory_vectors(tmp_path) -> None:
    index_path = tmp_path / "missing-after-memory.faiss"
    store = _make_store(index_path)
    store.add([VectorAddItem(chunk_id=1, vector=_unit_vector(1.0))])
    assert store.count == 1

    store.load()

    assert store.count == 0
    assert store.search(_unit_vector(1.0), k=1) == []


def test_loaded_index_validates_id_map_flat_ip_structure(tmp_path) -> None:
    import faiss

    index_path = tmp_path / "structure.faiss"
    store = _make_store(index_path)
    store.add([VectorAddItem(chunk_id=1, vector=_unit_vector(1.0))])
    store.save()

    reloaded = _make_store(index_path)
    reloaded.load()

    assert isinstance(reloaded._index, faiss.IndexIDMap2)
    inner_index = faiss.downcast_index(reloaded._index.index)
    assert isinstance(inner_index, faiss.IndexFlatIP)


def test_save_failure_removes_temp_file_and_preserves_destination(tmp_path, monkeypatch) -> None:
    import faiss

    from app.services.vector_store.exceptions import VectorStorePersistenceError

    index_path = tmp_path / "save-fail.faiss"
    store = _make_store(index_path)
    store.add([VectorAddItem(chunk_id=1, vector=_unit_vector(1.0))])
    store.save()
    original_bytes = index_path.read_bytes()
    temp_path = index_path.with_suffix(index_path.suffix + ".tmp")

    def fail_write(*args, **kwargs):
        raise RuntimeError("simulated write failure")

    monkeypatch.setattr(faiss, "write_index", fail_write)

    with pytest.raises(VectorStorePersistenceError) as exc_info:
        store.save()

    assert exc_info.value.__cause__ is not None
    assert not temp_path.exists()
    assert index_path.read_bytes() == original_bytes


def test_non_positive_k_returns_empty_list(tmp_path) -> None:
    store = _make_store(tmp_path / "nonpositive-k.faiss")
    store.add([VectorAddItem(chunk_id=1, vector=_unit_vector(1.0))])

    assert store.search(_unit_vector(1.0), k=0) == []


def test_factory_cache_clear_is_callable() -> None:
    clear_vector_store_caches()
