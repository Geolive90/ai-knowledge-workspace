# AI Knowledge Workspace — Engineering Lessons

This document captures durable engineering lessons from Phases 1 through 4D. Each entry explains **what happened**, **why the decision was made**, **alternatives considered**, **the lesson**, and **where it applies in future systems**.

For chronological history see `BUILD_LOG.md`. For enduring architecture see `ARCHITECTURE.md`.

---

## Phase 1 — Document Chunk Schema

### Lesson: Verify SQLite foreign keys through the application engine, not raw connections

**What happened:** Phase 1 verification reported `PRAGMA foreign_keys = 0` when using standalone `sqlite3.connect()` against the database file.

**Why:** SQLite enforces foreign keys per connection. The application enables `PRAGMA foreign_keys=ON` via a SQLAlchemy engine connect listener; a raw connection never runs that listener.

**Alternatives considered:** Trusting the raw `(0,)` result and adding redundant FK logic in application code — rejected because it would have been fixing a non-problem.

**Engineering lesson:** Always validate database behavior through the **same connection path production code uses**. Diagnostic scripts that bypass application initialization are useful for schema inspection but not for proving runtime enforcement.

**Applies to:** Any SQLite deployment, test fixture design, CI database setup, and debugging cascade delete issues.

### Lesson: Separate chunk storage from the document row early

**What happened:** Chunk data was designed as a normalized `document_chunks` table rather than JSON embedded in `documents`.

**Why:** Embeddings, citations, and per-chunk metadata require stable chunk IDs, ordered indexes, and cascade delete semantics that do not fit cleanly in a document blob column.

**Alternatives considered:** JSON/BLOB on `documents` — rejected for poor queryability, harder citation mapping, and coupling chunk lifecycle to document row updates.

**Engineering lesson:** When downstream stages need **addressable units** (chunks, segments, pages), give each unit its own row with a stable primary key before building retrieval or embedding pipelines.

**Applies to:** RAG systems, document pipelines, media segmentation, and any "split then enrich" workflow.

---

## Phase 2 — Custom Chunking Engine

### Lesson: Offsets must index the same string that was chunked

**What happened:** `build_chunks()` normalizes line endings internally. If `documents.extracted_text` stored raw CRLF while offsets referred to LF-normalized text, persisted offsets would be wrong.

**Why:** Offset invariants (`text[start:end] == chunk_text`) only hold when the indexed string and the chunking input are identical.

**Alternatives considered:** Normalizing inside chunking only and storing raw text — rejected because Phase 3 established a single canonical string at orchestration.

**Engineering lesson:** Pick **one canonical text representation** at a defined boundary (orchestration layer) and use it for both persistence and offset computation. Never compute offsets against a different string than the one stored.

**Applies to:** Search highlighting, citation spans, diff engines, and any character-offset-based UI.

### Lesson: Custom deterministic splitters beat library splitters when offsets are first-class

**What happened:** Version 1 rejected LangChain text splitters in favor of a custom recursive character splitter with exact slicing.

**Why:** Deterministic behavior, no new dependency, exact offsets by construction, and easier unit testing outweighed the convenience of a library splitter with post-hoc offset verification.

**Alternatives considered:** LangChain + offset verification — rejected for v1 complexity and non-deterministic edge cases across library updates.

**Engineering lesson:** When offsets or spans are part of the contract, prefer algorithms you can test exhaustively over black-box library behavior.

**Applies to:** Legal document processing, code indexing, genomic interval systems, and citation-backed retrieval.

---

## Phase 3 — Upload Orchestration

### Lesson: One orchestration function owns one persistence transaction

**What happened:** `create_document_with_chunks()` performs normalize → chunk → persist document + chunks → single `commit()`.

**Why:** Upload ingestion is one logical operation. Partial commits (document without chunks, or chunks without document) create recovery nightmares.

**Alternatives considered:** Router-level commits, chunking service writing to DB — rejected to keep routers thin and chunking pure.

**Engineering lesson:** Place `commit()` at the **orchestration boundary** that matches the user's mental model of atomicity. Pure functions (chunking, extraction) should not own transactions.

**Applies to:** Order processing, invoice generation, multi-table domain aggregates, and saga vs local transaction decisions.

### Lesson: Upload is not idempotent in Version 1 — design failure semantics explicitly

**What happened:** Each upload creates a new UUID file and new document row. Failed persistence deletes the file; client must retry the full upload.

**Why:** Simplicity for v1. Content-hash deduplication and resume semantics were explicitly deferred.

**Alternatives considered:** Idempotent upload by content hash — deferred to avoid scope creep before indexing existed.

**Engineering lesson:** Explicitly document **non-idempotent** operations and their retry semantics. Users and API clients need to know whether retry creates duplicates or resumes work.

**Applies to:** File upload APIs, webhook handlers, payment intents, and any "at least once" client retry environment.

### Lesson: Legacy valid states must be first-class in downstream design

**What happened:** Documents uploaded before Phase 3 may have zero chunk rows. This remains valid; no automatic backfill was performed.

**Why:** Backfill is a separate product decision with ownership, cost, and correctness implications.

**Engineering lesson:** New pipeline stages must handle **historical rows in pre-migration shape** until an explicit backfill migration is approved.

**Applies to:** Schema evolution in production systems, feature flags, and incremental rollouts.

---

## Phase 4A — Embedding Metadata Schema

### Lesson: Store embedding metadata separately from vectors

**What happened:** `chunk_embeddings` holds `model_name`, `dimensions`, `created_at` — no vector blob. Vectors live in FAISS.

**Why:** SQLite is the source of truth for relational metadata and ownership; FAISS is optimized for vector search. Mixing large vector blobs into SQLite complicates backup, migration, and dimension changes.

**Alternatives considered:** `vector_blob` in SQLite — rejected for Version 1.

**Engineering lesson:** Separate **metadata you query relationally** from **data you search geometrically**. Use foreign keys for the join key (`chunk_id`), not for co-locating unlike storage formats.

**Applies to:** Any hybrid OLTP + vector search architecture, image feature stores, and recommendation pipelines.

### Lesson: Migration tests must not use the current ORM model to represent legacy schema

**What happened:** Phase 4A migration tests stamp at a prior revision and upgrade. Phase 4D extended this pattern: create a legacy `documents` table **without** indexing columns before upgrading, because `Base.metadata.create_all(Document)` would create columns the migration is supposed to add.

**Why:** If the test schema already includes columns the migration adds, the migration test proves nothing.

**Engineering lesson:** Migration tests require **explicit legacy schema fixtures**, not "create all from current models."

**Applies to:** Alembic, Flyway, Rails migrations, and any additive schema evolution.

---

## Phase 4B — Embedding Service

### Lesson: Cached factory must reuse the same provider instance

**What happened:** Independent review found `create_embedding_service()` could instantiate a second provider if both factory accessors were used, loading the model twice.

**Why:** Sentence-transformers model load is expensive (memory, startup time, Hugging Face cache).

**Fix:** Default service creation reuses cached `get_embedding_provider()`.

**Engineering lesson:** When using `@lru_cache` factories, verify that **dependent singletons share instances** — not just that each accessor is cached independently.

**Applies to:** ML model servers, database connection pools, gRPC clients, and any expensive init resource.

### Lesson: Unit tests must not require network; integration tests opt in

**What happened:** Embedding unit tests use `FakeEmbeddingProvider`. Real model tests require `RUN_EMBEDDING_INTEGRATION=1`.

**Why:** CI speed, determinism, and developer machines without model cache should not block default test runs.

**Engineering lesson:** Split **fast deterministic fakes** from **slow external integration** with explicit environment gates.

**Applies to:** Payment gateways, cloud APIs, LLM calls, and third-party OAuth.

---

## Phase 4C — FAISS Vector Store

### Lesson: Duplicate IDs must fail loudly, including within the same batch

**What happened:** Bugbot review found `add()` could silently overwrite when the same `chunk_id` appeared twice in one batch.

**Why:** Duplicate IDs indicate orchestration bugs (double index, partial retry). Silent overwrite hides drift between SQLite metadata and FAISS.

**Fix:** Track `seen_in_batch`; reject duplicates before any FAISS mutation.

**Engineering lesson:** Vector index **identity is a consistency contract**. Treat duplicate key insertion as an error, not upsert, unless upsert semantics are explicitly designed and tested.

**Applies to:** Search indexes, idempotency keys, distributed caches, and exactly-once processing.

### Lesson: Persist with atomic replace, validate structure on load

**What happened:** FAISS save uses temp file + rename. Load validates wrapper is `IndexIDMap2` and inner index is `IndexFlatIP` via `downcast_index`.

**Why:** Partial writes corrupt indexes; wrong index types would break similarity semantics silently.

**Engineering lesson:** File-based index persistence needs **atomic write** and **structural validation on read** — not just "file exists."

**Applies to:** SQLite WAL alternatives, RocksDB checkpoints, ML model serialization, and config file updates.

### Lesson: Core abstractions should not import their orchestration dependencies

**What happened:** `FaissVectorStore` does not import embedding code. Only `vector_store/factory.py` lazy-imports `get_embedding_provider()` for dimensions.

**Why:** Keeps vector store testable with fake dimensions; prevents circular imports; allows swapping embedding providers without touching FAISS code.

**Engineering lesson:** Factories may bridge packages; **implementations should not**.

**Applies to:** Hexagonal architecture, plugin systems, and microservice boundaries.

---

## Phase 4D — Document Indexing Orchestration

### Architecture decision: Orchestrate existing components; do not redesign them

**What happened:** Phase 4D added `IndexingService` that calls existing `EmbeddingService`, `FaissVectorStore`, and `document_service` helpers without modifying extraction, chunking, embedding internals, or `create_document_with_chunks()`.

**Why:** Phases 1–3 already solved upload → extract → chunk → persist. Phase 4D's job is **index existing chunks**, not re-run ingestion.

**Alternatives considered:** Re-extracting or re-chunking during index — rejected as redundant and riskier.

**Engineering lesson:** Orchestration phases should **compose** stable lower layers, not fork them. Preserve contracts at layer boundaries.

**Applies to:** Workflow engines, CI pipelines, ETL orchestration, and microservice choreography.

### Why the consistency sequence was chosen: FAISS save before `indexed` status

**What happened:** The approved sequence requires `vector_store.save()` to succeed before the database transaction that sets `indexing_status='indexed'` and inserts `chunk_embeddings`.

**Why:** If metadata says "indexed" but FAISS was not saved, retrieval would query an index missing vectors — a **false ready state**. If FAISS saves but metadata commit fails, the document stays `failed` or `processing` and retry can reconcile — a **safe incomplete state**.

**Alternatives considered:**
- Commit metadata before FAISS save — rejected: creates false ready state.
- Two-phase commit across SQLite and FAISS — rejected: no distributed transaction manager in v1.

**Engineering lesson:** Across heterogeneous stores, order operations so **the user-visible "ready" flag is set only after the hardest-to-undo durable artifact exists**. Prefer "not ready but recoverable" over "ready but wrong."

**Applies to:** Object storage + database workflows, search index + DB, CDN purge + config update, and any dual-write problem.

### SQLite vs FAISS transaction limitations

**What happened:** SQLite metadata and FAISS index file are updated in separate systems with no atomic cross-store transaction. Phase 4D uses ordered steps and compensation (purge on failure) instead of 2PC.

**Why:** FAISS has no participation in SQLite transactions. A single `commit()` cannot span both.

**Observed failure modes (test-proven):**
- Metadata commit fails after FAISS save → vectors on disk, status `failed`, retry succeeds.
- FAISS save fails before metadata commit → no false `indexed` status.
- Compensation purge save fails → vectors removed in memory but remain on disk until healthy retry.

**Engineering lesson:** Treat cross-store workflows as **sagas with explicit compensation**, not as one transaction. Document which store is source of truth for each concern.

**Applies to:** Elasticsearch + PostgreSQL, S3 + DynamoDB, Redis + MySQL, and any polyglot persistence.

### Compensation strategy

**What happened:** On indexing failure, `_mark_failed()` attempts idempotent `purge_document_index()` then sets `indexing_status='failed'` with truncated error message.

**Why:** Partial success (vectors in FAISS without metadata, or metadata without vectors) breaks retrieval correctness. Purge attempts to restore a clean retry starting point.

**Improvements during verification:**
- Log compensation purge failures (previously swallowed).
- Append compensation context to `indexing_error`.
- Rollback on failed-status commit failure.

**Alternatives considered:** Leaving partial state for manual cleanup — rejected; retry must be client-simple.

**Engineering lesson:** Compensation should be **best effort, logged, and non-destructive to the primary error**. Do not claim full recovery unless tests prove the compensation path.

**Applies to:** Saga patterns, Kubernetes finalizers, Terraform destroy provisioners, and rollback hooks.

### Delete/index race

**What happened:** Verification found `purge_document_index()` did not share the per-document lock, and delete did not hold the lock through DB deletion. Concurrent index could recreate ghost vectors after purge.

**Why:** Index and delete are separate HTTP requests that can overlap in a multi-threaded server.

**Fix:** `document_lock()` context manager; delete holds blocking lock through purge + `delete_document()`; purge reacquires reentrant RLock safely.

**Alternatives considered:** Optimistic "delete wins" without lock — rejected after race analysis.

**Engineering lesson:** Any **purge-then-mutate** sequence needs the same concurrency guard as the mutate operation itself.

**Applies to:** Cache invalidation + DB update, file delete + metadata delete, and index removal + record deletion.

### Optimistic claim strategy

**What happened:** `_claim_processing()` uses a conditional SQL `UPDATE` that succeeds only when status is `pending`, `failed`, stale `processing`, or (with force) `indexed`. Returns row count; zero rows → conflict.

**Why:** Prevents two workers from both believing they claimed the same document. Combined with in-process `RLock` for same-process concurrency.

**Alternatives considered:** Pessimistic `SELECT FOR UPDATE` — SQLite support limited; row-level locking less portable for future PostgreSQL migration without redesign.

**Engineering lesson:** **Optimistic conditional update + row count check** is a portable claim pattern for job status fields. Pair with in-process locks when multi-threaded single-process is the v1 deployment model.

**Applies to:** Job queues, cron deduplication, migration runners, and lease-based work claiming.

### RLock usage

**What happened:** Per-document `threading.RLock` registry; index entry uses non-blocking acquire (409 on conflict); delete/purge use blocking acquire; nested purge during index uses reentrant acquire on same thread.

**Why:** Same document operations must serialize; different documents must not block each other; compensation purge runs while index holds lock on same thread.

**Version 1 limitation:** Lock registry never evicts — one RLock per document ID ever indexed/deleted. Accepted for single-process v1.

**Alternatives considered:** Global lock — rejected (blocks all documents). No lock — rejected (race defects).

**Engineering lesson:** Use **per-resource reentrant locks** when the same thread may call nested service methods (index → purge → purge in compensation). Document registry growth if locks are permanent.

**Applies to:** In-process caches with invalidation, per-tenant mutexes, and reentrant critical sections.

### Stale-processing recovery

**What happened:** If a worker dies mid-index, document stays `processing` with `indexing_started_at` set. After `INDEXING_STALE_TIMEOUT_SECONDS` (default 300), another claim can reclaim.

**Why:** Without stale reclaim, crashed workers permanently block re-indexing.

**Test-proven:** Failed-status commit failure also leaves `processing` until stale timeout — acceptable v1 behavior, recoverable.

**Alternatives considered:** Heartbeat worker + automatic reset — deferred (no background job system in v1).

**Engineering lesson:** Long-running synchronous operations need **timeout-based lease expiry** on status fields when crash recovery is not automatic.

**Applies to:** Distributed task leases, DB migration locks, and deployment drain timeouts.

### Retry design

**What happened:** Two entry points: upload (auto-index) and `POST /documents/{id}/index` (retry/force). Upload returns HTTP 200 with `indexing_status=failed` and retry path when post-upload indexing fails. Creation failures remain non-2xx.

**Why:** Separates "document exists" from "indexing succeeded." Client can retry indexing without re-uploading.

**Force reindex:** Purges once, then full re-index. Idempotent skip when already `indexed` without force.

**Engineering lesson:** Split **resource creation HTTP semantics** from **derived artifact processing semantics**. Derived processing failure should not roll back the resource if the resource itself is valid.

**Applies to:** Video transcoding after upload, thumbnail generation, search indexing after CMS publish.

### Idempotent purge

**What happened:** `purge_document_index()` removes vectors by document chunk IDs and deletes `chunk_embeddings` rows. Safe to call when neither exists (no-op with zero counts). Called before force reindex, on failure compensation, and on delete.

**Why:** Retries and partial failures leave unpredictable combinations of metadata and vectors. Purge normalizes to clean slate.

**Test-proven scenarios:** metadata only, vectors only, both, neither, double purge, zero chunks, save skipped when nothing removed.

**Engineering lesson:** Design purge as **idempotent relative to desired empty state**, not relative to "something existed."

**Applies to:** Cache eviction, index segment deletion, and GDPR erasure helpers.

### Upload response semantics

**What happened:** Post-upload indexing failure → HTTP 200, document durable, `retry` object in response pointing to index endpoint.

**Why:** Upload succeeded; indexing is a second concern. Non-2xx would confuse clients that already have a `document_id`.

**Engineering lesson:** Match HTTP status to **the operation the client invoked at the HTTP layer**, while using response fields to convey sub-operation status.

**Applies to:** Multi-step API responses, async job IDs in synchronous endpoints, and partial success patterns.

### Deletion ordering trade-off

**What happened:** Delete order: purge FAISS + metadata → delete document (cascade chunks) → delete file (best effort).

**Why:** Ghost vectors in FAISS are worse than a temporarily unsearchable document row if DB delete fails. Ghost vectors could appear in wrong user's search results in Phase 4E.

**Test-proven:** DB delete failure after purge leaves row + file but no vectors; second delete succeeds.

**Engineering lesson:** When choosing delete order across stores, prioritize **preventing invisible data leaks** over **atomic disappearance from all stores**.

**Applies to:** CDN + origin delete, search index + DB delete, and secrets manager + config delete.

### Debugging lessons

**What happened:** Several verification tests initially failed due to: wrong commit count assumptions, same-session ORM state vs durable DB state, SQLite in-memory concurrent claim flakiness, caplog not capturing router logger.

**Fixes:** Use fresh session for durable assertions; sequential claim tests instead of threaded; mock `logger.warning` for delete test; targeted commit hooks for failure injection.

**Engineering lesson:** Failure injection tests must target **specific transaction boundaries**, not arbitrary commit counts. Durable state checks require **new sessions**.

**Applies to:** Any testing of rollback, saga compensation, and ORM identity map confusion.

### Verification lessons

**What happened:** Phase 4D required three verification passes: implementation review, targeted verification (51 tests), gap-closure (11 tests). Several failure paths were explicitly marked "not proven" until gap tests added.

**Why:** Orchestration bugs hide in failure paths, not happy paths. Claims of recovery require tests.

**Engineering lesson:** For orchestration layers, maintain a **failure matrix** and refuse to sign off until each cell is tested or explicitly accepted as v1 limitation.

**Applies to:** Payment flows, auth flows, migration rollbacks, and disaster recovery drills.

---

## Cross-Cutting Principles (Phases 1–4D)

### 1. Thin routers, fat services

HTTP mapping, status codes, and response shaping live in routers. Business logic, transactions, and cross-component sequencing live in services.

### 2. Ownership through parent resources

Chunks and embedding metadata inherit ownership via `document_id` → `user_id`. Never query derived tables without scoping through owned documents.

### 3. Explicit factory caches with test clearing

Singleton factories (`get_embedding_service`, `get_vector_store`, `get_indexing_service`) speed production but require `clear_*_caches()` in test autouse fixtures to prevent state leakage.

### 4. Pin verified dependency versions

Minimum constraints (`>=`) are not reproducible. Pin exact versions after verification (`sentence-transformers==5.6.0`, `faiss-cpu==1.14.3`).

### 5. Document rejected alternatives

Rejected options (LangChain splitters, vector blobs in SQLite, MIN(user_id) backfill, INDEXING_ENABLED flag) prevent re-litigation in future sessions.

### 6. Source of truth must be explicit

Phase 4D: only `indexing_status='indexed'` means ready for retrieval. Metadata rows or FAISS presence alone are insufficient. Phase 4E must enforce this gate.

### 7. Version 1 limitations are intentional trade-offs

Single-process locks, synchronous indexing in upload, no content-hash deduplication, orphaned files on delete failure — each was accepted with documented recovery paths rather than deferred indefinitely without decision.

---

## Documentation Map

| Document | Role |
|----------|------|
| `ARCHITECTURE.md` | Enduring decisions and flows |
| `BUILD_LOG.md` | Chronological history |
| `PROJECT_STATE.md` | Current snapshot |
| `ENGINEERING_LESSONS.md` | This file — transferable lessons |
| `AI_DEVELOPMENT_PROTOCOL.md` | Process rules for AI-assisted development |
