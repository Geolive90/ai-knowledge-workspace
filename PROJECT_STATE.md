# AI Knowledge Workspace — Project State

## 1. Document Purpose

This document records the current state of the AI Knowledge Workspace.

It should describe what exists now, what is being developed, what remains unfinished, and what technical limitations are currently accepted.

It is a current snapshot, not a chronological development history.

The chronological history is maintained in BUILD_LOG.md.

---

## 2. Project Mission

The AI Knowledge Workspace is intended to become a production-oriented web application where users can:

- Register an account
- Log in securely
- Upload documents
- Manage their uploaded documents
- Process and index document content
- Ask questions about their documents
- Receive AI-generated answers grounded in their documents
- View source citations
- Review conversation history
- Use the application through a responsive web interface

The application will eventually be deployed to a real public URL and made available to external users.

---

## 3. Current Version

Current development target:

Version 1

Current status:

Backend development in progress.

The application is not yet a complete end-to-end production deployment.

No precise completion percentage is assigned in this document because completion should be measured against verified features rather than estimated code volume.

---

## 4. Project Location

Project root:

C:\Projects\AI-Knowledge-Workspace

Backend:

C:\Projects\AI-Knowledge-Workspace\02-Projects\backend

Backend application package:

C:\Projects\AI-Knowledge-Workspace\02-Projects\backend\app

---

## 5. Current Backend Structure

The backend currently includes architectural areas such as:

- API or router modules
- Core configuration
- Database configuration
- SQLAlchemy models
- Pydantic schemas
- Service modules
- Utility modules
- Authentication
- Document management
- Alembic migration structure
- Local uploads directory
- SQLite development database

The exact structure must be inspected before any AI assistant makes changes.

---

## 6. Verified Completed Functionality

### Application Foundation

- FastAPI application created
- Uvicorn development server configured
- Root API endpoint previously verified
- Swagger documentation available
- Environment-based configuration established
- SQLAlchemy database engine configured
- SessionLocal configured
- Database dependency created
- Declarative Base configured

### User Model and Database

- User model created
- User email configured as unique
- User password stored as a hash
- User active status included
- User creation timestamp included
- SQLite database used during local development

### Authentication

- User registration endpoint implemented
- Duplicate-email handling implemented
- Duplicate registration returns a controlled 400 response
- User login endpoint implemented
- JWT access token generation implemented
- OAuth2 password flow integrated with Swagger
- Protected endpoints use bearer authentication
- Login successfully returned an access token during testing
- Swagger authorization was successfully completed during testing

### Document Management

- Document model created
- Documents router created
- Documents router included in the FastAPI application
- Document upload endpoint implemented
- Uploaded files stored locally
- Document metadata stored in the database
- Document list endpoint implemented
- Individual document retrieval endpoint implemented
- Document deletion endpoint implemented
- Physical file deletion integrated
- Database record deletion integrated
- Missing document behavior tested
- Repeated deletion returned a not-found response
- Document download endpoint implemented

### Document Ownership and User Isolation

- `documents.user_id` added as a non-nullable indexed foreign key to `users.id`
- Alembic migration `c4a8f2e19061` applied successfully
- `Document.owner` and `User.documents` SQLAlchemy relationships added
- All document service queries scoped by `user_id`
- Upload stores `current_user.id` as the document owner
- List, retrieve, download, and delete endpoints enforce owner-only access
- Cross-user document requests return 404 with the same message as a missing document
- Ownership logic implemented in the service layer; routers remain thin
- Manually verified with multiple users including Alice and ownerb@example.com

### Persistent Extracted Text Storage

- `documents.extracted_text` column added (nullable `Text`) via migration `d7b3a4f29182`
- Upload persists extracted text through `create_document(..., extracted_text=...)`
- Supported extraction formats in code: `.txt`, `.docx`, `.pdf`
- List and retrieve responses do **not** expose full extracted text (`DocumentResponse` unchanged)
- Upload response still returns preview (`text_preview` max 300 chars) and character count
- Legacy document rows may have `extracted_text IS NULL` until re-uploaded

### Document Chunking — Phase 1 (Schema)

- **Status:** complete and approved
- `document_chunks` table defined via migration `e8c5b6a30293`
- `DocumentChunk` model with FK `ON DELETE CASCADE`, unique `(document_id, chunk_index)`
- `Document.chunks` relationship with ORM cascade
- SQLite application connections enforce `PRAGMA foreign_keys=ON` via engine connect listener
- Phase 1 manually verified: migration applied, table columns confirmed, application-engine FK check returned `1`

### Document Chunking — Phase 2 (Engine Only)

- **Status:** complete and approved
- `app/services/chunking_service.py` — custom recursive character splitter (1000 / 200)
- Unit tests in `tests/test_chunking_service.py` — 13 passed

### Document Chunking — Phase 3 (Upload Orchestration)

- **Status:** complete, verified, and approved (July 22, 2026)
- Upload calls `create_document_with_chunks()` — normalizes text, persists document + chunks in one transaction
- `extracted_character_count` and `text_preview` derived from persisted `document.extracted_text`
- Legacy `create_document()` retained for non-upload paths/tests; upload cannot bypass chunk creation
- Automated tests: 29 total (13 Phase 2 + 10 service + 6 integration), all passing at Phase 3 completion

### Embeddings — Phase 4A (Embedding Metadata Schema)

- **Status:** complete, verified, and approved (July 22, 2026)
- `chunk_embeddings` table defined via migration `f3a1b8c45201` (Alembic head)
- `ChunkEmbedding` model in `app/models/chunk_embedding.py` — metadata only; no `vector_blob`
- Columns: `id`, `chunk_id`, `model_name`, `dimensions`, `created_at`
- One-to-one: `DocumentChunk.embedding` ↔ `ChunkEmbedding.chunk` (`uselist=False`, `back_populates`)
- Cascade chain: `Document` → `DocumentChunk` → `ChunkEmbedding` (FK `ON DELETE CASCADE`)
- Development database verified at `f3a1b8c45201 (head)`
- Automated tests: **37 passed**, 0 failed, 3 pre-existing warnings (8 new Phase 4A tests)
- No Phase 4B work, no new dependencies, no upload pipeline changes

### Embeddings — Phase 4B (Embedding Provider and Service)

- **Status:** complete, verified, and approved (July 22, 2026)
- Text-to-vector abstraction: `EmbeddingProvider` Protocol → `EmbeddingService` → `SentenceTransformersProvider`
- Single result type: `EmbeddingVector` (`vector`, `model_name`, `dimensions`)
- Factory with cached `get_embedding_provider()` / `get_embedding_service()` and `clear_embedding_caches()`
- Configuration: `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_BATCH_SIZE`
- Dependency pinned: `sentence-transformers==5.6.0` in `02-Projects/backend/requirements.txt`
- Default model: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, provider-derived)
- Automated tests: **56 passed**, 2 skipped (integration), 0 failed, 3 pre-existing warnings
- No FAISS, upload integration, search, persistence, routers, or `app/dependencies.py` changes

### Embeddings — Phase 4C (Vector Store / FAISS)

- **Status:** complete, verified, and approved (July 22, 2026)
- Provider-independent `VectorStore` Protocol with `FaissVectorStore` as sole Version 1 implementation
- FAISS structure: `IndexIDMap2(IndexFlatIP)`; vectors keyed by `chunk_id`
- Cosine-style similarity via L2-normalized vectors and inner-product search
- Duplicate `chunk_id` rejected (including within same incoming batch)
- Dimensions supplied by factory via `EmbeddingProvider.dimensions` — no `VECTOR_STORE_DIMENSIONS` config
- Core vector-store abstraction and FAISS implementation remain embedding-independent; only `factory.py` lazy-imports embedding
- Explicit `save()` / `load()` lifecycle; atomic save via temp file + replacement
- Missing index file → empty valid store; corrupt/wrong-dimension/incompatible structure → `VectorStoreLoadError`
- Per-instance `RLock`; Version 1 single-process limitation documented
- Configuration: `VECTOR_STORE_PROVIDER`, `FAISS_INDEX_PATH`
- Dependencies pinned: `faiss-cpu==1.14.3` (verified on Windows Python 3.10.5, NumPy 2.2.6)
- **Source files created (6):**
  - `app/services/vector_store/__init__.py`
  - `app/services/vector_store/exceptions.py`
  - `app/services/vector_store/provider.py`
  - `app/services/vector_store/factory.py`
  - `app/services/vector_store/providers/__init__.py`
  - `app/services/vector_store/providers/faiss.py`
- **Test files created (3):**
  - `tests/test_vector_store_factory.py`
  - `tests/test_vector_store_protocol.py`
  - `tests/test_faiss_vector_store.py`
- **Modified:** `app/config.py`, `requirements.txt`, `tests/conftest.py`
- **Total:** 12 files (9 created + 3 modified)
- Manual smoke test passed (add → search → save → reload → remove → save → reload)
- Persistence invariant verified (IDs, ordering, scores within tolerance)
- Defects found and fixed: same-batch duplicate-ID overwrite; loaded inner-index structure validation
- **Final test results:**
  - Targeted vector-store unit: **16 passed**
  - Full default suite: **72 passed**, 22 skipped, 3 pre-existing warnings
  - FAISS integration only (`RUN_FAISS_INTEGRATION=1`): **20 passed**
  - Full suite with FAISS integration: **92 passed**, 2 skipped, 3 pre-existing warnings
- No upload integration, retrieval orchestration, routers, migrations, models, schemas, or `app/dependencies.py` changes

### Service and Utility Foundation

- Document schema created
- Document service module created
- Text extraction service module created
- File handler utility created
- Router and service separation introduced
- Recent work committed and pushed to GitHub

---

## 7. Most Recent Verified Milestone

Milestone:

Embeddings — Phase 4C (Vector Store / FAISS)

- **Implemented, verified, and approved:** July 22, 2026
- **Git commit:** pending in closeout step

The milestone included:

- `app/services/vector_store/` package (6 files) — Protocol, exceptions, factory, `FaissVectorStore`
- 3 new test files; `requirements.txt` with `faiss-cpu==1.14.3`
- Modified `app/config.py`, `tests/conftest.py`
- **9 new files, 3 modified files** (12 total touched)
- Targeted vector-store unit tests: 16 passed
- FAISS integration tests: 20 passed (`RUN_FAISS_INTEGRATION=1`)
- Complete default suite: **72 passed**, 22 skipped
- Complete suite with FAISS: **92 passed**, 2 skipped
- Defects corrected: same-batch duplicate-ID rejection; loaded-index inner FlatIP validation

Previous verified milestones:

- Embeddings — Phase 4B (Embedding Provider and Service) — July 22, 2026
- Embeddings — Phase 4A (Embedding Metadata Schema) — July 22, 2026
- Document Chunking — Phase 3 (Upload Orchestration) — July 22, 2026
- Document Chunking — Phase 2 (Custom Chunking Engine) — July 21–22, 2026
- Document Chunking — Phase 1 (Schema) — July 21, 2026
- Persistent Extracted Text Storage — July 20–21, 2026
- Document Ownership and User Isolation — July 18–20, 2026

---

## 8. Current Development Area

Current area of work:

**Phase 4D — Upload pipeline integration (atomic embed + index)** — next planned milestone; **not started**.

Repository state:

- Document Chunking **Phases 1–3:** complete, verified, and approved
- Embeddings **Phase 4A:** metadata schema in place (`chunk_embeddings`)
- Embeddings **Phase 4B:** text-to-vector service layer complete — `EmbeddingService` + `SentenceTransformersProvider`
- Embeddings **Phase 4C:** FAISS vector storage layer complete — `VectorStore` + `FaissVectorStore`
- Upload persists normalized `extracted_text` and chunk rows atomically (unchanged)
- No upload embedding integration, semantic search, or RAG yet
- Vectors stored in FAISS only (Version 1); `chunk_embeddings` holds metadata only

See `ARCHITECTURE.md` for embedding and vector-store architecture and invariants.

---

## 9. Planned Next Features

The expected implementation sequence is:

1. **Phase 4D — Upload pipeline integration (atomic embed + index)** — next; not started
2. Phase 4E — Semantic retrieval and search API
3. Phase 4F — Deletion consistency and index rebuild
5. Add question-answering endpoint.
6. Add grounded AI responses.
7. Add citations.
8. Add conversation and message history.
9. Add frontend.
10. Add Docker configuration.
11. Add production database migration.
12. Add cloud file storage.
13. Add deployment.
14. Add monitoring, logging, and security hardening.

The sequence may be adjusted after inspecting the current implementation.

---

## 10. Current Technical Debt

The following limitations are currently known:

### Database

SQLite is being used for local development.

A production version should migrate to PostgreSQL.

### Alembic Migration Chain — Empty Database Initialization

The complete Alembic chain **cannot initialize an empty database** because revision `bdc259e18150` assumes an existing `users` table (`ALTER TABLE users ADD COLUMN role`). This is **pre-existing technical debt**, not introduced by Phase 4A.

**Must be repaired before:** Docker deployment, CI fresh-database testing, or cloud deployment.

Phase 4A migration tests work around this by stamping at `e8c5b6a30293` and upgrading only the new revision. See `BUILD_LOG.md` for details.

### File Storage

Uploaded files are stored locally.

A production version should use managed object storage such as Amazon S3 or another suitable service.

### Testing

Testing has largely been manual through Swagger.

Automated unit, integration, authentication, ownership, and document-processing tests are still required.

### Security

Production-level security hardening is incomplete.

Areas still requiring attention include:

- File size limits
- File content validation
- Safe filename handling
- Malware-related controls
- Rate limiting
- CORS restrictions
- Refresh token or session strategy
- Password reset
- Email verification
- Secret rotation
- Logging controls

### Document Processing

- Extracted text **is persisted** on upload in `documents.extracted_text` (nullable for legacy rows).
- Upload normalizes extracted text at orchestration and persists chunk rows atomically (Phase 3).
- Embedding **metadata schema** exists (`chunk_embeddings`, Phase 4A); **text-to-vector service** exists (Phase 4B); **FAISS vector storage** exists (Phase 4C)
- Upload embedding integration, semantic retrieval, and Q&A are unfinished.

### Phase 4C Known Version 1 Limitations

- Single-process RLock; not safe for concurrent multi-worker index sharing without external coordination
- Explicit `save()` required after mutations — no auto-save
- Ownership pre-filtering not in VectorStore — deferred to Phase 4E retrieval layer
- Index recovery from `chunk_text` designed but not implemented (Phase 4F)

### Phase 4A Non-Blocking Observations (Recorded at Review)

- Redundant non-unique index on `chunk_embeddings.id` (PK already indexed; matches `document_chunks` precedent).
- Duplicate uniqueness/index structures on `chunk_embeddings.chunk_id` (`UniqueConstraint` plus unique index).
- Cascade tests confirm final deletion behavior but do not isolate raw SQL `ON DELETE CASCADE` from ORM `delete-orphan`.

### Chunking Test Gaps (Future Additions, Not Current Defects)

- Isolated single-newline separator priority
- Isolated space separator priority
- Longer separator-free input spanning more than two chunks
- Exact-window-boundary separator placement
- Explicit repeat-call determinism
- Database invariant for stored normalized text and chunk offsets

### Legacy Documents Without Chunks

Documents uploaded before Phase 3 may have zero `document_chunks` rows. This is a **valid state**. Future retrieval, embedding, and Q&A phases must handle documents with missing chunks until optional backfill or reprocessing is explicitly approved.

### Dependencies

`02-Projects/backend/requirements.txt` pins `sentence-transformers==5.6.0` (Phase 4B) and `faiss-cpu==1.14.3` (Phase 4C). This is **not** a complete backend dependency manifest — FastAPI, SQLAlchemy, torch (2.13.0 installed transitively), and other runtime packages remain in `.venv` only.

### Background Processing

Long-running document processing currently has no verified background job system.

Large files should eventually be processed asynchronously.

### Frontend

The browser interface has not yet been completed.

### Deployment

The application has not yet been deployed as a complete public production system.

### Monitoring

Centralized logs, error reporting, metrics, and operational alerts are not yet implemented.

---

## 11. Important Previous Issues and Resolutions

### Documents Router Missing from Swagger

Cause:

The FastAPI application imported and included only the authentication, health, and users routers.

Resolution:

The documents router was imported and included in `app/main.py`.

Result:

The Documents section appeared in Swagger.

### Swagger Returned 401 After Server Reload

Cause:

Swagger authorization was lost after Uvicorn reloaded.

Resolution:

The bearer token authorization was completed again in Swagger.

Result:

Protected document requests worked.

### Duplicate Email Initially Caused a Server Error

Cause:

The database unique constraint was reached before a controlled duplicate-email response was returned.

Resolution:

Duplicate-email checking and controlled error handling were added.

Result:

Duplicate registration returned 400 Bad Request with a clear message.

### Incorrect Folder or File Placement

Some files or folders were previously created in incorrect locations.

Resolution:

They were moved or recreated in the proper project structure.

Future summaries must continue documenting incorrect placement, its effect, and its correction.

### Unsaved File and Reload Concerns

Changes may not take effect when a file has not been saved.

Uvicorn reload can also cause Swagger authorization to reset.

Future troubleshooting should check:

- Whether the file was saved
- Whether the server reloaded
- Whether Swagger authorization remains active
- Whether the correct terminal and folder are being used

### Ownership Milestone Was Documented Before It Was Implemented

Earlier documentation and the July 15 build log entry described ownership-aware document access before `user_id` existed in the schema.

Cause:

The ownership requirement was recorded as a goal before the foreign key, service scoping, and migration were implemented.

Resolution:

The Document Ownership and User Isolation milestone (July 18–20, 2026) implemented and verified owner-scoped access in code and database schema.

Result:

Users can only access their own documents; cross-user requests return 404.

### Rejected Migration Backfill Strategy

An initial Alembic draft used `MIN(users.id)` and deleted unresolved document rows.

Cause:

That approach could assign documents to the wrong account and silently delete records.

Resolution:

The migration was rewritten to assign legacy rows only to `documenttest@example.com` when rows exist, abort on unsafe conditions, and never delete document rows.

Result:

Migration `c4a8f2e19061` applied successfully against the development SQLite database.

---

## 12. Current Development Rules

Before the next implementation:

- Confirm the current Git branch.
- Run `git status`.
- Confirm the latest work is committed.
- Inspect existing files before modifying them.
- Do not rebuild the project.
- Do not create a second backend.
- Implement one feature at a time.
- Test before committing.
- Update this document after verified milestones.
- Update BUILD_LOG.md with detailed troubleshooting history.

---

## 13. Version 1 Completion Criteria

Version 1 will be considered complete when a user can:

1. Visit the deployed application.
2. Create an account.
3. Log in.
4. Upload a supported document.
5. See the document in their account.
6. Have the document processed and indexed.
7. Ask a question about the document.
8. Receive a grounded response with citations.
9. Review previous conversations.
10. Delete their document and associated information.
11. Use the application from desktop and mobile browsers.

The system must also include:

- Database persistence
- User data isolation
- Controlled error handling
- Basic automated testing
- Environment-based configuration
- Cloud deployment
- Basic security protections
- GitHub version history
- Operational documentation

---

## 14. Post-Version-1 Learning Phase

After Version 1 is working, the project will be studied from beginning to end.

The study phase will focus on:

- Why each folder exists
- Why each file exists
- How requests travel through the application
- How authentication works
- How database sessions are created and used
- How schemas differ from models
- How routers differ from services
- How uploaded files are processed
- How text becomes chunks
- How chunks become embeddings
- How vector retrieval works
- How retrieved information becomes an AI response
- How citations are generated
- How failures are traced to the correct architectural layer
- How the architecture can be extended safely

The objective is not memorization. The objective is engineering control and transferable understanding.