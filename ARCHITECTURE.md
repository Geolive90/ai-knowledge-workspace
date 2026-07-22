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
Document Processing (extract → persist text → chunk → embed)
  ↓
Embeddings and Vector Retrieval (planned)
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

### Upload — `POST /documents/upload` (Verified — Phase 3)

```text
Client (Bearer + file)
  → get_current_user
  → file_handler.save_uploaded_file          (disk first — not idempotent)
  → text_extraction_service.extract_text     (raw text)
  → document_service.create_document_with_chunks(...)
       normalize once → build_chunks → persist Document + DocumentChunk rows (single commit)
  → JSON: message, document_id, filename, extracted_character_count, text_preview
       (count and preview use persisted document.extracted_text)
```

### Upload — Pre-Phase 3 (Historical)

Previously used `document_service.create_document()` without chunk persistence. Legacy documents may have zero chunk rows until re-uploaded.

### List / Retrieve / Download / Delete

All use `get_document_for_user` or `get_documents_for_user` — owner-scoped. See prior verified flows in repository routers.

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
| `EmbeddingProvider` / `EmbeddingService` | **Deferred (Phase 4B)** |
| `VectorStore` / FAISS | **Deferred (Phase 4C)** |
| Upload embedding integration | **Deferred (Phase 4D)** |
| Semantic retrieval / search API | **Deferred (Phase 4E)** |
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
| **FAISS index file (planned Phase 4C)** | Vector data keyed by `chunk_id` |

Version 1 design decisions (approved):

- No `vector_blob` in SQLite — FAISS is the sole vector store in Version 1
- Index recovery regenerates embeddings from `chunk_text`
- `EmbeddingProvider` → `EmbeddingService` → `VectorStore` abstraction chain (Phase 4B+)

---

## 9. Ownership Boundary for Derived Data

All document-derived data inherits ownership through the parent document:

- Extracted text
- Chunks
- Embedding metadata (`chunk_embeddings`, Phase 4A)
- Embedding vectors in FAISS (planned Phase 4C)
- Conversations, messages, citations (future)

Chunk queries must not bypass document ownership checks. Services should scope through owned `document_id` values.

---

## 10. Current Architectural Gaps

| Gap | Notes |
|-----|-------|
| `EmbeddingProvider` / `EmbeddingService` | Phase 4B — metadata schema ready |
| FAISS vector storage / semantic retrieval | Phase 4C–4E |
| Q&A / citations / conversations | Planned |
| Frontend | Planned |
| Production DB, object storage, deployment | Planned |
| Alembic empty-database initialization | Pre-existing debt — must fix before Docker/CI/cloud |
| Pinned dependency manifest | `requirements.txt` empty at repo root |
| Automated integration tests beyond upload/chunking/embedding schema | Expanded through Phase 4A; broader suite still planned |
| Legacy document backfill | Not implemented — zero-chunk legacy rows remain valid |

Chunk persistence at upload and normalized-text boundary: **resolved in Phase 3**.

Embedding metadata schema: **resolved in Phase 4A**.

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
