# AI Knowledge Workspace — Architecture

## 1. Purpose

This document explains how the AI Knowledge Workspace is organized, which architectural decisions are verified in code, and which alternatives were rejected.

It records **enduring design decisions** — not transient terminal output or chronological troubleshooting (see `BUILD_LOG.md` for history, `PROJECT_STATE.md` for current snapshot).

After Version 1, this document will become a central study guide for understanding the complete system.

---

## 2. High-Level System

```text
User
  ↓
Frontend (planned)
  ↓
FastAPI Backend
  ↓
Authentication and Authorization
  ↓
Application Services
  ↓
Database and File Storage
  ↓
Document Processing (extract → persist text → chunk → embed → index)
  ↓
Semantic Retrieval (verified — Phase 4E)
  ↓
Large Language Model (planned)
  ↓
Grounded Answer with Citations (planned)
```

---

## 3. Authentication and Authorization

### Authentication (Verified)

Authentication identifies **who** is making a request.

- Users register and log in through the auth router.
- Login returns a JWT access token.
- Protected routes depend on `get_current_user`, which decodes the bearer token and loads the `User` record.
- Invalid or missing tokens return **401 Unauthorized**.

### Authorization (Verified — Document Ownership)

Authorization controls **what** an authenticated user may access.

- Every document row stores `user_id` as a non-nullable FK to `users.id`.
- All document service queries filter by `user_id`.
- Cross-user document requests return **404 Not Found** (same message as missing documents) to avoid leaking existence.

Authentication and authorization are separate: a valid token alone does not grant access to another user's documents.

---

## 4. Document Request Flows (Verified)

### Upload — `POST /documents/upload` (Verified — Phases 3 + 4D)

```text
Client (Bearer + file)
  → get_current_user
  → file_handler.save_uploaded_file          (disk first — not idempotent)
  → text_extraction_service.extract_text     (raw text)
  → document_service.create_document_with_chunks(...)
       normalize once → build_chunks → persist Document + DocumentChunk rows (single commit)
  → IndexingService.index_document(...)      (Phase 4D — synchronous after chunk persist)
  → JSON: message, document_id, filename, extracted_character_count, text_preview,
       indexing_status, chunk_count, vectors_indexed, indexed_at, indexing_error,
       retry (when indexing_status=failed)
```

**Creation vs indexing failure semantics (Phase 4D):**

| Failure point | HTTP | Durable state |
|---------------|------|---------------|
| File save, extraction, or chunk DB persist | Non-2xx | No document (file cleaned up where applicable) |
| Post-upload indexing | **200** | Document + chunks remain; `indexing_status=failed`; retry via `POST /documents/{id}/index` |

### Upload — Pre-Phase 3 (Historical)

Previously used `document_service.create_document()` without chunk persistence. Legacy documents may have zero chunk rows until re-uploaded.

### List / Retrieve / Download / Delete

All use `get_document_for_user` or `get_documents_for_user` — owner-scoped. See prior verified flows in repository routers.

### Search — `POST /search` (Verified — Phase 4E)

```text
Client (Bearer + SearchRequest JSON)
  → get_current_user
  → search.router.search
  → RetrievalService.search(user_id, query, top_k, document_id?)
       validate query (non-empty, max length)
       embed query via EmbeddingService
       compute fetch_k (bounded over-fetch)
       VectorStore.search(query_vector, fetch_k)   (global FAISS — ownership-agnostic)
       document_service.get_indexed_searchable_chunks_by_ids(chunk_ids, user_id, document_id?)
            filter: owned documents only
            gate: indexing_status='indexed'
       rank by FAISS score; limit to top_k
  → JSON: query, top_k, results[{ chunk_id, document_id, document_filename, chunk_index, chunk_text, score }]
```

**Router boundary:** The search router is thin — JWT authentication, request validation via Pydantic schema, dependency injection, and exception-to-HTTP mapping only. All retrieval orchestration lives in `RetrievalService`.

**Phase 4E explicit boundary — not in scope:**

- No LLM answering
- No RAG response generation
- No citations
- No conversation history

**Exception-to-HTTP mapping (search router):**

| Exception | HTTP | Message |
|-----------|------|---------|
| `RetrievalValidationError` | 422 | Validation detail from service |
| `RetrievalNotFoundError` | 404 | `"Document not found."` |
| `RetrievalEmbeddingError` | 500 | `"Search could not be completed."` |
| `RetrievalVectorStoreError` | 500 | `"Search could not be completed."` |
| `RetrievalError` (base) | 500 | `"Search could not be completed."` |

Optional `document_id` scopes retrieval to one owned, indexed document. Cross-user or non-existent document IDs return **404** (same message as missing documents).

---

## 5. Data Model

### User (`users`)

Key fields: `id`, `email`, `hashed_password`, `role`, `is_active`, `created_at`

Relationship: `User.documents` → one-to-many `Document`

### Document (`documents`)

Key fields:

- `id`
- `user_id` (FK → `users.id`, non-nullable, indexed)
- `filename`, `file_path`
- `extracted_text` (`Text`, nullable — legacy rows may be NULL)
- `uploaded_at`
- `indexing_status` (`String(32)`, default `pending`) — Phase 4D
- `indexing_error` (`Text`, nullable) — Phase 4D
- `indexed_at` (`DateTime`, nullable) — Phase 4D
- `indexing_started_at` (`DateTime`, nullable) — Phase 4D; stale-processing detection

Relationships:

- `Document.owner` → `User`
- `Document.chunks` → one-to-many `DocumentChunk` (`cascade="all, delete-orphan"`, ordered by `chunk_index`)

### DocumentChunk (`document_chunks`) — Schema Verified (Phase 1)

| Column | Purpose |
|--------|---------|
| `id` | PK; future embedding/citation key |
| `document_id` | FK → `documents.id`, **ON DELETE CASCADE** |
| `chunk_index` | 0-based order within document |
| `chunk_text` | Chunk body for embedding/retrieval |
| `character_start` / `character_end` | Offsets into `documents.extracted_text` (end exclusive) |
| `token_count` | Nullable; reserved for future token-aware stages |
| `created_at` | Audit timestamp |

Constraints:

- Unique `(document_id, chunk_index)`
- **No `user_id`** — ownership inherited through parent document

Relationships:

- `DocumentChunk.document` → `Document`
- `DocumentChunk.embedding` → one-to-one `ChunkEmbedding` (`uselist=False`, `cascade="all, delete-orphan"`)

### ChunkEmbedding (`chunk_embeddings`) — Schema Verified (Phase 4A)

| Column | Purpose |
|--------|---------|
| `id` | PK |
| `chunk_id` | FK → `document_chunks.id`, **ON DELETE CASCADE**, UNIQUE |
| `model_name` | Embedding provider/model identifier (e.g. `sentence-transformers/all-MiniLM-L6-v2`) |
| `dimensions` | Vector length at creation time |
| `created_at` | Audit timestamp |

Constraints:

- One embedding metadata row per chunk (`chunk_id` UNIQUE)
- **Metadata only** — no `vector_blob`; vectors stored in FAISS (Version 1)
- **No `user_id`** — ownership inherited through `document_chunks` → `documents.user_id`

Relationships:

- `ChunkEmbedding.chunk` → `DocumentChunk` (`back_populates="embedding"`)

Cascade chain (verified):

```text
DELETE Document → CASCADE DocumentChunk → CASCADE ChunkEmbedding
```

Index recovery (Version 1 design): regenerate embeddings from `chunk_text` when FAISS index is rebuilt.

---

## 6. Schema Migrations (Repository-Proven Chain)

| Revision | Change |
|----------|--------|
| `bdc259e18150` | Add `users.role` |
| `c4a8f2e19061` | Add `documents.user_id` + FK + index; non-destructive backfill rules |
| `d7b3a4f29182` | Add nullable `documents.extracted_text` |
| `e8c5b6a30293` | Create `document_chunks` |
| `f3a1b8c45201` | Create `chunk_embeddings` (metadata only) |
| `a7c2d9e48103` | Add document indexing lifecycle columns (Phase 4D) |

Legacy document rows without owner: assigned to `documenttest@example.com` only when rows exist during migration; never deleted.

### Empty-Database Migration Limitation (Pre-Existing Technical Debt)

The full Alembic chain **cannot initialize an empty database**: revision `bdc259e18150` executes `ALTER TABLE users ADD COLUMN role` and requires a pre-existing `users` table. This predates Phase 4A.

**Must be repaired before:** Docker deployment, CI fresh-database testing, or cloud deployment.

Per-revision migration tests stamp at `e8c5b6a30293` and upgrade only subsequent revisions. See `BUILD_LOG.md`.

---

## 7. SQLite Foreign Key Enforcement (Verified Design)

**Decision:** Enable `PRAGMA foreign_keys=ON` on every SQLAlchemy engine connection via `@event.listens_for(engine, "connect")` in `database.py`.

**Rationale:** SQLite defaults to FK off per connection; `ON DELETE CASCADE` on `document_chunks.document_id` requires enforcement at runtime.

**Rejected inference:** Standalone `sqlite3.connect()` returning `PRAGMA foreign_keys = 0` does **not** validate application behavior (separate connection, no listener).

**Verified check path:** Import `engine` from `app.database.database` and query `PRAGMA foreign_keys` on `engine.connect()`.

---

## 8. Document Processing Architecture

### Text Extraction (Verified)

`text_extraction_service.py` supports `.txt`, `.docx`, `.pdf`. Extraction runs at upload; failures delete the saved file before DB write.

### Persisted Extracted Text (Verified)

Full text stored in `documents.extracted_text`. Not exposed on list/get API schemas.

### Chunking — Design Decisions (Approved; Phases 1–3 Complete)

#### Storage decision

| Option | Verdict |
|--------|---------|
| Chunks embedded in `documents` row | **Rejected** |
| Separate `document_chunks` table | **Approved** |

#### Splitter decision (Version 1)

| Option | Verdict |
|--------|---------|
| `langchain-text-splitters` + post-hoc offset verification | **Rejected** |
| Custom recursive character splitter in `chunking_service.py` | **Approved** |

**Rationale:** Deterministic behavior, exact offsets by slicing, no new dependency, easier testing, schema independent of library.

#### Approved parameters

- Size: 1000 characters
- Overlap: 200 characters
- Separators: `\n\n`, `\n`, ` `, character fallback
- Empty/whitespace-only → zero chunks

#### Normalization and offset invariant (enduring)

- `build_chunks()` normalizes CRLF and CR line endings to LF before chunking.
- `character_start` and `character_end` refer to the **normalized** text used inside the chunking engine.
- The slice invariant is: `document.extracted_text[start:end] == chunk_text` after Phase 3 upload orchestration.
- Normalization occurs once in `create_document_with_chunks()` before both persistence and chunk generation.
- `text_extraction_service.py` returns raw extracted text; the orchestration layer establishes the canonical normalized string stored in `documents.extracted_text`.

#### Implementation status

| Component | Status |
|-----------|--------|
| `document_chunks` schema + model | **Verified and approved (Phase 1)** |
| `chunking_service.build_chunks()` | **Implemented, unit-tested (13/13), approved (Phase 2)** |
| `create_document_with_chunks()` upload orchestration | **Implemented and verified (Phase 3 — July 22, 2026)** |
| Normalized-text persistence boundary | **Established at orchestration (Phase 3)** |
| `chunk_embeddings` metadata schema + model | **Verified and approved (Phase 4A — July 22, 2026)** |
| `EmbeddingProvider` / `EmbeddingService` | **Verified and approved (Phase 4B — July 22, 2026)** |
| `VectorStore` / FAISS | **Verified and approved (Phase 4C — July 22, 2026)** |
| Upload embedding integration | **Verified and approved (Phase 4D — July 22, 2026)** |
| Semantic retrieval / search API | **Verified and approved (Phase 4E — July 23, 2026)** |
| Chunk API endpoints | **Deferred** |

#### Chunking architectural invariants (Phases 1–3)

These are permanent guarantees, not implementation details:

1. **A document owns its chunks** — every `DocumentChunk` row references exactly one `documents.id`; ownership inherits through the parent document (no `user_id` on chunks).
2. **Chunks never exist independently** — chunk rows are created only as part of a document's lifecycle; `ON DELETE CASCADE` and ORM `delete-orphan` enforce this.
3. **Chunk offsets always reference `documents.extracted_text`** — `character_start` and `character_end` index into the persisted extracted-text column (end exclusive).
4. **Normalization occurs before persistence and chunk generation** — a single canonical normalized string is persisted and chunked; offsets must not be computed against a different string than the one stored.
5. **Upload persistence is atomic** — document row and all chunk rows commit in one transaction, or none persist.
6. **Chunk generation is deterministic** — identical normalized input produces identical chunk boundaries and indexes via the approved custom splitter.

#### Phase 3 — `create_document_with_chunks()` orchestration contract

**Status:** Implemented and verified (July 22, 2026).

This function becomes the **primary service-layer entry point for document ingestion** (upload). Future phases (embeddings, vector indexing, retrieval) extend downstream of this contract; they must not change its core meaning.

| Aspect | Contract |
|--------|----------|
| **Inputs** | `db: Session` (request-scoped); `user_id: int`; `filename: str`; `file_path: str` (stored name); `extracted_text: str` (raw output from `extract_text()`, not yet normalized) |
| **Output** | Persisted `Document` instance with `id` assigned after commit; `document.chunks` populated when N > 0 |
| **Responsibilities** | (1) Normalize line endings once via `normalize_line_endings()`. (2) Persist canonical text in `Document.extracted_text`. (3) Call `build_chunks(canonical_text)`. (4) Map each `ChunkRecord` to a `DocumentChunk` via relationship append. (5) Commit atomically. (6) Return refreshed document. |
| **Out of scope** | HTTP handling, file I/O, text extraction, embedding generation, chunk API exposure, background jobs |
| **Transaction ownership** | This function owns the **single persistence transaction** for document + chunks. It performs exactly one `db.commit()` after all rows are staged. It does not commit partially. Callers must not commit before or after on behalf of this operation. |
| **Normalization guarantee** | `Document.extracted_text` stores the same canonical normalized string passed to `build_chunks()`. Offsets in chunk rows index directly into that column. |
| **Failure guarantees** | On any exception before successful commit: no durable document or chunk rows (session rolled back by caller). The function does not delete files on disk — that remains the router's responsibility. Zero chunks (whitespace-only input) is success: document persisted, no chunk rows. |

**Why transaction ownership belongs in the orchestration service:** Phase 3 introduces one logical persistence boundary — document ingestion with derived chunks. All rows share one commit point and one rollback scope. Placing `commit()` here keeps the router thin, keeps `chunking_service` pure (no DB), and matches existing `document_service` patterns. If later phases add separate persistence boundaries (e.g., async embedding writes), those will be **additional** orchestration steps or functions — not partial commits inside this contract.

#### Phase 3 — ORM flush lifecycle (design decision)

**Explicit `db.flush()` is not required** for Phase 3.

The intended pattern:

1. Construct `Document` with `extracted_text=canonical_text`.
2. Append `DocumentChunk` instances via `document.chunks.append(...)` (relationship cascade).
3. `db.add(document)`.
4. Single `db.commit()`.

With `SessionLocal(autocommit=False, autoflush=False)`, SQLAlchemy performs an **implicit flush immediately before `commit()`**, ordering inserts to satisfy foreign-key dependencies (document first, then chunks). Relationship management assigns `document_id` on chunk rows during that flush — no manual `document.id` access is needed in Phase 3.

**Documented decision:** Rely on relationship-based persistence and implicit flush-at-commit. Do not add an explicit `flush()` unless a future requirement needs `document.id` before commit (e.g., external system callback) — that is out of Phase 3 scope.

Optional pre-commit validation (in-memory, no extra flush): assert `canonical_text[start:end] == chunk_text` for each record before `commit()`.

#### Phase 3 — Upload idempotency policy

**Upload is not idempotent in Version 1.**

Each request:

- Writes a **new** file under `uploads/` (UUID stored filename).
- Creates a **new** document row on successful persistence.

If persistence fails after the file is written, the router deletes the orphaned file and returns an error; the client must **retry the full upload**. A retry is a new request — it does not resume or deduplicate a partial attempt. This is acceptable for v1 and keeps failure handling simple.

#### Phase 3 — Legacy documents without chunks

Documents uploaded **before Phase 3** may have:

- `extracted_text` populated or NULL (legacy rows).
- **Zero** `document_chunks` rows.

This is a **valid state**. Downstream retrieval, embedding, and Q&A phases must treat "document exists, chunks absent" as normal until optional future backfill or reprocessing (re-upload, admin job, etc.) is explicitly designed and approved. Phase 3 does not backfill existing documents.

#### Phase 3 — Verification requirements (design)

In addition to existing chunking unit tests, Phase 3 implementation must verify:

1. **Slice invariant (persisted):** `document.extracted_text[chunk.character_start:chunk.character_end] == chunk.chunk_text` for every chunk row.
2. **Sequential indexes:** persisted `chunk_index` values are exactly `0..N-1` with no gaps or duplicates per document.
3. **CRLF normalization:** upload with `\r\n` content persists LF-only `extracted_text` with valid offsets.
4. **Zero-chunk documents:** whitespace-only input persists document, zero chunk rows.
5. **Atomicity:** simulated commit failure leaves no document or chunk rows; orphaned file removed by router.
6. **Ownership regression:** cross-user access still returns 404.
7. **Upload response shape unchanged.**

### Embedding Metadata Storage (Verified — Phase 4A)

Embeddings do **not** live on `document_chunks`. Metadata is stored in `chunk_embeddings` referencing `chunk_id`.

| Storage | Holds |
|---------|--------|
| **SQLite `chunk_embeddings`** | `model_name`, `dimensions`, `created_at` (metadata only) |
| **FAISS index file (Phase 4C)** | Vector data keyed by `chunk_id` |

Version 1 design decisions (approved):

- No `vector_blob` in SQLite — FAISS is the sole vector store in Version 1
- Index recovery regenerates embeddings from `chunk_text`
- `EmbeddingProvider` → `EmbeddingService` → vector generation; `VectorStore` → FAISS persistence (Phase 4C)
- Upload orchestration wiring embed + metadata + index resolved in Phase 4D

### Indexing Orchestration Layer (Verified — Phase 4D)

Phase 4D introduced an orchestration layer that connects existing components without redesigning extraction, chunking, embedding, or vector-store internals. Indexing operates on **already persisted chunks** — it does not re-extract or re-chunk during normal flow.

```text
Upload / POST /documents/{id}/index
        ↓
IndexingService (injected: EmbeddingService, VectorStore, config)
        ↓
claim processing (optimistic DB update + in-process RLock)
        ↓
optional purge (retry / force / stale reclaim)
        ↓
embed texts → vector_store.add() → vector_store.save()
        ↓
insert chunk_embeddings + set indexing_status=indexed (single DB commit)
```

| Component | Role |
|-----------|------|
| **`IndexingService`** | Core orchestration: claim, purge, embed, FAISS add/save, metadata commit, failure compensation |
| **`IndexingResult` / `PurgeResult`** | Structured outcomes for upload and index endpoints |
| **Exception hierarchy** | `IndexingError` base; `IndexingNotFoundError`, `IndexingConflictError`, `IndexingEmbeddingError`, `IndexingVectorStoreError`, `IndexingPersistenceError` |
| **Factory** | `create_indexing_service`, `get_indexing_service` (cached), `clear_indexing_caches()` |

**Entry points:**

1. **Primary:** Synchronous `IndexingService.index_document()` at end of `POST /documents/upload` (after `create_document_with_chunks()`)
2. **Secondary:** `POST /documents/{document_id}/index` for retry or force reindex (`force_reindex` query param)

**Indexing status values:**

| Status | Meaning |
|--------|---------|
| `pending` | Document created; not yet indexed (default for new and migrated rows) |
| `processing` | Indexing claimed; work in progress |
| `indexed` | Indexing completed successfully — **only this status means retrieval may proceed (Phase 4E gate)** |
| `failed` | Indexing failed; `indexing_error` populated; retry via index endpoint |

**Configuration (Phase 4D):**

| Setting | Env var | Default |
|---------|---------|---------|
| Stale processing timeout | `INDEXING_STALE_TIMEOUT_SECONDS` | `300` (minimum 30) |

Rejected config flags: `INDEXING_ENABLED`, `INDEXING_MAX_CHUNKS`.

#### Consistency model (definitive sequence)

1. Acquire in-process document `RLock` (non-blocking for index entry)
2. Conditional optimistic DB update → `processing` + `indexing_started_at`
3. Purge prior artifacts when retry, force reindex, or stale reclaim
4. Zero chunks → mark `indexed` immediately (`vectors_indexed=0`); skip embed and FAISS
5. Embed chunk texts via `EmbeddingService`
6. `vector_store.add()` (in-memory)
7. `vector_store.save()` — **disk before indexed status**
8. Single DB commit: insert `chunk_embeddings` rows + set `indexing_status=indexed` + `indexed_at`
9. On failure: idempotent purge attempt + mark `failed` (with rollback on failed-status commit failure)

**Source of truth:** Only `indexing_status='indexed'` means indexing completed. Metadata or FAISS presence alone is insufficient for retrieval (Phase 4E must gate on status).

#### Retry and idempotency

- **`indexed` without force:** Idempotent no-op; no embed/add/save calls
- **`failed` or stale `processing`:** Reclaimable via conditional update
- **Active `processing`:** Returns 409 Conflict
- **Force reindex:** Purge once, then full re-index

#### Deletion behavior (Phase 4D)

```text
DELETE /documents/{id}
  → document_lock (blocking, holds through purge + DB delete)
  → purge_document_index()  (FAISS remove + save, chunk_embeddings delete)
  → delete_document()       (ORM cascade: chunks, metadata)
  → delete_stored_file()    (best effort; logs warning on failure, still HTTP 200)
```

**Trade-off:** FAISS purge before DB delete prioritizes eliminating ghost vectors over temporary unsearchability if DB delete fails. Document row and file may remain; vectors are gone; retry delete succeeds.

#### Concurrency (Version 1)

- Per-document `threading.RLock` registry (never evicted — accepted v1 limitation)
- Optimistic conditional DB claim with stale timeout
- `purge_document_index()` reacquires same RLock (reentrant)
- Delete holds lock through purge + DB delete to prevent index/delete race
- Multi-worker FAISS not synchronized

#### Phase 4D contracts preserved (unchanged)

- `create_document_with_chunks()` — signature and single-commit semantics unchanged
- Text extraction, chunking, `EmbeddingService`, `FaissVectorStore` internals not redesigned
- FastAPI HTTP mapping remains in routers; core service has no FastAPI imports

### Semantic Retrieval Layer (Verified — Phase 4E)

**Status:** Implemented and verified (July 23, 2026).

**Purpose:** Owner-scoped semantic search over indexed document chunks. Returns ranked chunk matches with similarity scores. Does not generate answers, citations, or conversational responses.

**HTTP surface:**

| Endpoint | Auth | Request body | Response |
|----------|------|--------------|----------|
| `POST /search` | JWT (`get_current_user`) | `SearchRequest`: `query` (required), `top_k` (optional), `document_id` (optional) | `SearchResponse` |

**Response schema (`SearchResponse`):**

- `query` — echoed search query
- effective `top_k` (response field `top_k`; resolved after defaults and max cap)
- `results` — list of `SearchHitResponse` items, each containing:
  - `chunk_id`
  - `document_id`
  - `document_filename`
  - `chunk_index`
  - `chunk_text`
  - `score` (FAISS similarity score)

**Thin router / fat service boundary:**

- `app/routers/search.py` — authentication, schema validation, DI, HTTP status mapping
- `app/services/retrieval/service.py` — `RetrievalService.search()` orchestration

**RetrievalService orchestration sequence:**

1. **Query validation** — reject empty/whitespace-only queries and queries exceeding configured max length (`RetrievalValidationError`).
2. **Query embedding** — single-vector embed via injected `EmbeddingService` (`RetrievalEmbeddingError` on failure).
3. **Bounded over-fetch** — compute `fetch_k = min(index_count, search_max_fetch_k, max(top_k, top_k × multiplier, top_k + buffer))` from settings defaults.
4. **Global FAISS search** — `VectorStore.search(query_vector, fetch_k)` returns `(chunk_id, score)` pairs. **VectorStore remains ownership-agnostic** (Phase 4C design preserved).
5. **Ownership filtering** — hydrate candidate chunks via `document_service.get_indexed_searchable_chunks_by_ids()`, scoped to `user_id`.
6. **`indexing_status='indexed'` gate** — only chunks belonging to documents with completed indexing are returned (literal `"indexed"` string in document service to avoid circular imports with indexing package).
7. **Optional document scope** — when `document_id` is provided, verify ownership and indexed status; non-owned or missing documents raise `RetrievalNotFoundError`.
8. **Ranking and limiting** — preserve FAISS score order among surviving rows; return at most `top_k` results.

**FAISS chunk ID alignment:** FAISS stores `document_chunks.id` as the vector ID (Phase 4C invariant). Retrieval uses those IDs for database hydration.

**Configuration defaults (`app/config.py`):**

| Setting | Default |
|---------|---------|
| `search_default_top_k` | 10 |
| `search_max_top_k` | 50 |
| `search_over_fetch_multiplier` | 5 |
| `search_over_fetch_min_buffer` | 20 |
| `search_max_fetch_k` | 200 |
| `search_max_query_length` | 4000 |

**Version 1 limitation — global FAISS with application-layer filtering:**

The FAISS index is **global** (all users' vectors in one index). `VectorStore.search()` has no ownership awareness. `RetrievalService` compensates with bounded over-fetch followed by ownership and indexing-status filtering in the application layer. After filtering, the response may validly contain **fewer than `top_k` results** even when additional owned indexed chunks exist beyond the over-fetch window. This is an accepted Version 1 tradeoff; multi-tenant pre-filtering inside FAISS is deferred.

**Phase 4E explicit non-goals (unchanged from plan):**

- No LLM answering or RAG response generation
- No citations
- No conversation or message history
- No changes to `DocumentResponse` or list/detail document endpoints (richer indexing metadata on those endpoints recorded as a possible future enhancement only)

### Embedding Service Layer (Verified — Phase 4B)

Phase 4B introduced text-to-vector conversion **without** vector storage, upload integration, search, or RAG behavior.

```text
Application workflow (Phase 4D+)
        ↓
EmbeddingService          validation, batching, dimension checks
        ↓ depends on
EmbeddingProvider         Protocol (interface only)
        ↓ implemented by
SentenceTransformersProvider   lazy model load, canonical model metadata
```

| Component | Role |
|-----------|------|
| **`EmbeddingProvider`** | Protocol: `embed_text`, `embed_texts`, `model_name`, `dimensions` |
| **`EmbeddingService`** | Validates input, batches by `embedding_batch_size`, validates vector count/dimensions, returns `EmbeddingVector` |
| **`EmbeddingVector`** | Frozen dataclass: `vector`, `model_name`, `dimensions` |
| **`SentenceTransformersProvider`** | Only concrete provider; lazy `sentence_transformers` import; model loaded once per cached instance |
| **Factory** | `create_embedding_provider`, `get_embedding_provider` (cached), `create_embedding_service`, `get_embedding_service` (cached), `clear_embedding_caches()` |

**Configuration (Phase 4B):**

| Setting | Env var | Default |
|---------|---------|---------|
| Provider | `EMBEDDING_PROVIDER` | `sentence_transformers` (only supported value) |
| Model | `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` |
| Batch size | `EMBEDDING_BATCH_SIZE` | `32` (minimum 1) |

**Design decisions:**

- Dimensions are **provider-derived**, not configured
- Canonical `model_name` for metadata: `sentence-transformers/all-MiniLM-L6-v2` (loads via short name `all-MiniLM-L6-v2`)
- Default service creation reuses cached `get_embedding_provider()` — single model instance per process
- FastAPI wiring for embedding, indexing, and retrieval services added in Phases 4D–4E (`get_embedding_service_dependency`, `get_indexing_service_dependency`, `get_retrieval_service_dependency`)

### Vector Store Layer (Verified — Phase 4C)

Phase 4C introduced a **provider-independent vector-storage layer** with FAISS as the sole Version 1 implementation. It stores embedding vectors together with enough identifier metadata to retrieve corresponding document chunks later, without persisting vectors in SQLite.

**Purpose:** Accept pre-computed embedding vectors keyed by `chunk_id`, index them for nearest-neighbor search, persist the index to disk, and support removal by chunk identifier. Upload orchestration resolved in Phase 4D; ownership filtering and semantic retrieval resolved in Phase 4E (`RetrievalService`, not in `VectorStore`).

```text
EmbeddingProvider.dimensions
        ↓
Vector-store factory (one-time read at construction)
        ↓
FaissVectorStore(dimensions=...)
        ↓
IndexIDMap2(IndexFlatIP)
```

| Component | Role |
|-----------|------|
| **`VectorStore`** | Protocol: `add`, `search`, `remove_by_chunk_ids`, `clear`, `save`, `load`, `dimensions`, `count` |
| **`VectorAddItem`** | Frozen dataclass: `chunk_id`, `vector` |
| **`VectorSearchResult`** | Frozen dataclass: `chunk_id`, `score` (inner product = cosine similarity on normalized vectors) |
| **`FaissVectorStore`** | Only concrete implementation; `IndexIDMap2(IndexFlatIP)`; L2-normalizes vectors on add and search |
| **Factory** | `create_vector_store`, `get_vector_store` (cached), `clear_vector_store_caches()` |

**Configuration (Phase 4C):**

| Setting | Env var | Default |
|---------|---------|---------|
| Provider | `VECTOR_STORE_PROVIDER` | `faiss` (only supported value) |
| Index path | `FAISS_INDEX_PATH` | `data/faiss/chunk_index.faiss` |

**Dimension supply:** There is **no** `VECTOR_STORE_DIMENSIONS` configuration. The factory reads `EmbeddingProvider.dimensions` once when `dimensions` is not supplied explicitly (tests inject `dimensions=` directly). The core vector-store abstraction and FAISS implementation **do not import** the embedding package; only `factory.py` uses an approved lazy import.

**Identifier strategy:**

- **`chunk_id`** (`document_chunks.id`) is the persistent vector identifier in FAISS via `IndexIDMap2`
- FAISS internal sequential IDs are opaque; never exposed to callers
- `document_id`, `user_id`, and chunk text remain in SQLite only

**Similarity strategy:**

- Cosine-style similarity via L2-normalized vectors and inner-product search (`IndexFlatIP`)
- Normalization occurs in `FaissVectorStore` on add and search (idempotent if provider already normalized)
- Higher `score` means more similar (range typically −1 to 1)

**Duplicate-ID policy:**

- `add()` rejects any `chunk_id` already in the index — **including duplicates within the same incoming batch**
- Duplicate IDs indicate orchestration or consistency errors; Version 1 fails loudly rather than silently overwriting

**Persistence lifecycle:**

- **`save()`** — explicit; atomic write via temporary file (`.faiss.tmp`) followed by same-filesystem replacement
- **`load()`** — missing index file produces an empty valid store (clears any in-memory vectors); corrupt, structurally incompatible, or wrong-dimension indexes raise `VectorStoreLoadError`
- Loaded index structure validated: wrapper must be `IndexIDMap2`; inner index downcast must be `IndexFlatIP`

**Concurrency (Version 1):**

- Per-instance `threading.RLock` guards all index operations (intentionally conservative)
- Single-process assumption; multiple workers each hold an independent in-memory index with no cross-process file locking
- Future versions may split read/write synchronization if higher concurrency is needed

**Out of scope (Phase 4C — resolved in later phases):**

- Upload embedding integration (Phase 4D — complete)
- Ownership pre-filtering in search (Phase 4E — complete in `RetrievalService`, not in `VectorStore`)
- Semantic retrieval API (Phase 4E — complete; RAG/Q&A still planned)
- Storing vectors in SQLite

---

## 9. Ownership Boundary for Derived Data

All document-derived data inherits ownership through the parent document:

- Extracted text
- Chunks
- Embedding metadata (`chunk_embeddings`, Phase 4A)
- Embedding vectors in FAISS (Phase 4C)
- Conversations, messages, citations (future)

Chunk queries must not bypass document ownership checks. Services should scope through owned `document_id` values.

---

## 10. Current Architectural Gaps

| Gap | Notes |
|-----|-------|
| Q&A / citations / conversations | Planned |
| Frontend | Planned |
| Production DB, object storage, deployment | Planned |
| Alembic empty-database initialization | Pre-existing debt — must fix before Docker/CI/cloud |
| Pinned dependency manifest | `requirements.txt` pins embedding + FAISS deps; not full backend manifest |
| Legacy document backfill | Not implemented — zero-chunk legacy rows remain valid |
| Index rebuild from chunk_text | Designed but not implemented (Phase 4F) |
| Background/async indexing | Synchronous in upload request (v1) |
| Multi-worker FAISS coordination | Single-process RLock (v1) |

Chunk persistence at upload and normalized-text boundary: **resolved in Phase 3**.

Embedding metadata schema: **resolved in Phase 4A**.

Text-to-vector service layer: **resolved in Phase 4B**.

FAISS vector storage layer: **resolved in Phase 4C**.

Upload indexing orchestration: **resolved in Phase 4D**.

Semantic retrieval / search API: **resolved in Phase 4E**.

---

## 11. Rejected Alternatives (Summary)

| Topic | Rejected | Accepted |
|-------|----------|----------|
| Ownership backfill | `MIN(users.id)`, delete unresolved rows | Assign to `documenttest@example.com` when rows exist; abort otherwise |
| Chunk storage | JSON in `documents` | `document_chunks` table |
| Chunk ownership column | `user_id` on chunks (v1) | Inherit via `document_id` |
| Chunking library (v1) | LangChain splitters | Custom splitter |
| FK verification | Raw sqlite3 default connection | Application SQLAlchemy engine |

---

## 12. Documentation Map

| Document | Role |
|----------|------|
| `ARCHITECTURE.md` | Enduring decisions, flows, data model, rejected options |
| `BUILD_LOG.md` | Chronological history, errors, fixes, verification commands |
| `PROJECT_STATE.md` | Current verified snapshot and next approved step |
| `AI_DEVELOPMENT_PROTOCOL.md` | Stable process rules for AI-assisted work |
