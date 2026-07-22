# AI Knowledge Workspace — Build Log

## Purpose

This document preserves the chronological development history of the AI Knowledge Workspace.

Each entry should include:

- Date
- Objective
- Files created
- Files modified
- Full-file replacements
- Dependencies installed
- Configuration changes
- Commands executed
- Tests performed
- Errors encountered
- Causes of errors
- Fixes applied
- Verification results
- Remaining work

This log should preserve troubleshooting details, including incorrect file placement, unsaved files, incorrect terminal use, server reload effects, duplicate execution, authentication loss, and other mistakes that contributed to learning.

---

# Earlier Foundation — July 8–9, 2026

## Objective

Create the initial project structure and start the FastAPI backend.

## Project Location

The project was created under:

C:\Projects\AI-Knowledge-Workspace

The backend was established under:

C:\Projects\AI-Knowledge-Workspace\02-Projects\backend

## Work Completed

- Created the project folders.
- Opened the project in VS Code on Windows 11 **(owner-reported)**.
- Created a Python virtual environment at repository-root `.venv` **(repository-proven: directory exists)**.
- Installed FastAPI and Uvicorn-related dependencies.
- **(Owner-reported)** Python-related VS Code extensions installed.
- **(Owner-reported)** `pip` upgrade activity; warnings or conflicts may have been observed.
- Created the initial FastAPI application.
- Added a root endpoint returning `{"message": "AI Knowledge Workspace API is running."}` **(repository-proven)**.
- Started the Uvicorn development server.
- **(Owner-reported)** Verified API at `http://127.0.0.1:8000`.
- Created environment configuration (`backend/.env`) **(repository-proven)**.
- Added the SQLite database URL.
- Created SQLAlchemy engine configuration.
- Created SessionLocal.
- Created the database dependency.
- Added declarative Base.
- Created initial user and document model foundations.

## Issues Encountered

### Incorrect Folder Selection

The wrong folder was initially opened or selected during setup.

Cause:

The distinction between the general projects directory and the specific AI Knowledge Workspace folder was not yet clear.

Resolution:

The correct project root was opened in VS Code.

### Uvicorn Not Found

Cause:

Uvicorn was not installed or the correct environment was not active.

Resolution:

The proper virtual environment was activated and Uvicorn was installed.

### Database Location Confusion

There was uncertainty about where the SQLite database was created and how to inspect it.

Resolution:

The database path and configuration were verified, and DB Browser for SQLite was used.

### Possible Duplicate Execution

A database-related issue may have been caused by clicking an execution action more than once.

This possibility was recorded so that duplicate execution can be considered during future troubleshooting. **Status: reported possibility only — not proven as root cause.**

### Terminal Confusion

**(Owner-reported)** Multiple terminals were open during early setup, causing uncertainty about which session was running Uvicorn or executing Python commands.

## Verification

The FastAPI root endpoint successfully returned a response, confirming that the initial backend application was running.

---

# Authentication and User Management — July 13, 2026

## Objective

Implement user registration, password hashing, login, JWT authentication, and duplicate-email handling.

## Dependencies Installed

- email-validator
- python-jose[cryptography]
- python-multipart

## Configuration Changes

The following authentication settings were added to the backend environment configuration:

- SECRET_KEY
- ALGORITHM=HS256
- ACCESS_TOKEN_EXPIRE_MINUTES=30

The configuration module was updated to load authentication settings.

## Work Completed

- Created or updated user schemas.
- Added password hashing.
- Added user registration.
- Added login.
- Added JWT access-token creation.
- Added OAuth2 bearer authentication.
- Integrated Swagger authorization.
- Protected routes using the authenticated user dependency.
- Added controlled duplicate-email handling.

## Issues Encountered

### bcrypt Compatibility Warning

A warning involving an unavailable bcrypt version attribute appeared.

Password hashing still operated, but the warning indicated a compatibility concern between installed packages.

This remains relevant for future dependency cleanup and testing.

### Duplicate Email Caused 500 Error

Initial behavior:

Registering an existing email reached the database unique constraint and caused an internal server error.

Cause:

The application did not return a controlled duplicate-email response before the database failure.

Resolution:

Duplicate-email checking and controlled exception handling were added.

Verification:

Submitting an existing email returned:

400 Bad Request

with:

`{"detail":"A user with this email already exists."}`

### Alembic Configuration Confusion

Alembic was initialized, but there was concern about the location or visibility of `alembic.ini`.

The Alembic environment file was updated to:

- Add the project path
- Import Base
- Import application models
- Set `target_metadata = Base.metadata`

## Verification

- User registration worked.
- Login returned 200 OK.
- A bearer access token was returned.
- Swagger OAuth2 authorization worked.
- Duplicate registration returned a controlled 400 response.

---

# Document Management — July 15, 2026

## Objective

Implement authenticated document upload, listing, individual retrieval, and deletion.

## Testing Account

A Swagger testing user was registered:

Email:

documenttest@example.com

The testing password must not be treated as a production credential.

## Work Completed

- Added the documents router.
- Added document upload.
- Added local file storage.
- Added database metadata creation.
- Added document listing.
- Added individual document retrieval.
- Added document deletion.
- Added physical file removal.
- Added database record removal.
- Document ownership enforcement was **not yet implemented in schema or queries** at this milestone; the July 15 entry originally described ownership as present, but that was a **design goal** rather than verified code (see BUILD_LOG correction under Document Ownership milestone).

## Issues Encountered

### Documents Router Missing from Swagger

Initial condition:

The Documents section did not appear in Swagger.

Cause:

`app/main.py` imported and included only the authentication, health, and users routers.

Resolution:

The documents router was imported and included in the FastAPI application.

Result:

The Documents section appeared in Swagger.

### Swagger Returned 401 Unauthorized

Initial response:

`{"detail":"Not authenticated"}`

Cause:

Uvicorn reloaded after the application files changed. Swagger lost its previous bearer authorization state.

Resolution:

Swagger authorization was completed again using a valid access token.

Result:

The upload endpoint worked.

### Uploads Directory Placement

There was an earlier issue involving the uploads folder being created or expected in an incorrect location.

Resolution:

The directory was corrected to the intended backend storage location and verified.

### Document Deletion Testing

Deletion was deliberately tested in multiple stages:

1. Retrieve an existing document.
2. Delete the document.
3. Request the same document again.

Result:

The first deletion succeeded.

The later request returned a not-found response, confirming that deletion had occurred.

A second delete attempt also confirmed controlled missing-resource behavior.

## Verification

The following endpoints were verified through Swagger:

- POST /documents/upload
- GET /documents
- GET /documents/{id}
- DELETE /documents/{id}

The uploaded file was saved physically and document metadata was stored in SQLite.

**(Owner-reported)** Successful upload of `832 final paper.docx` after Swagger reauthorization.

**(Owner-reported)** Deletion testing intentionally used document ID 2 before deleting ID 1 so the only test record was not destroyed too early.

**(Owner-reported)** Invalid document ID behavior was tested or requested for verification.

## Engineering Lessons

- Register all routers in `app/main.py` before expecting Swagger sections to appear.
- After Uvicorn reload, reauthorize Swagger before testing protected routes.
- Confirm the correct terminal and working directory (`02-Projects/backend`) before running Alembic or Uvicorn.
- Save files before testing; unsaved editor buffers cause “changes not applied” confusion.

---

# Document Service and Text Extraction Foundation — July 17, 2026

## Objective

Preserve the current working state and introduce a cleaner document service and text extraction foundation before expanding AI-assisted development.

## Git Safety Review

The computer had previously closed, so the project was reopened in VS Code.

The virtual environment was active.

`git status` was executed before making further changes.

Git reported modified and untracked files.

## Modified Files Identified

- 02-Projects/backend/app/main.py
- 02-Projects/backend/app/routers/__init__.py
- 02-Projects/backend/app/routers/documents.py
- 02-Projects/backend/app/schemas/__init__.py

## New Files Identified

- 02-Projects/backend/app/schemas/document.py
- 02-Projects/backend/app/services/document_service.py
- 02-Projects/backend/app/services/text_extraction_service.py
- 02-Projects/backend/app/utils/file_handler.py

## Git Commands Executed

```text
git status
git add .
git status
git commit -m "Milestone: Document services and text extraction foundation"
git push
```

---

# Document Ownership and User Isolation — July 18–20, 2026

## Objective

Implement document ownership and user isolation so every document belongs to an authenticated user and users can only list, retrieve, download, and delete their own documents.

## Implementation

- Added `documents.user_id` as a non-nullable indexed foreign key to `users.id`.
- Added `Document.owner` and `User.documents` SQLAlchemy relationships.
- Updated `document_service.py` so all document queries are scoped by `user_id`.
- Updated upload, list, retrieve, download, and delete endpoints.
- New uploads store `current_user.id` as the document owner.
- Cross-user document requests return the same 404 response as a missing document.
- Routers remain thin; ownership filtering and business logic remain in the service layer.

## Files Modified

- `02-Projects/backend/app/models/document.py`
- `02-Projects/backend/app/models/user.py`
- `02-Projects/backend/app/services/document_service.py`
- `02-Projects/backend/app/routers/documents.py`

## Files Created

- `02-Projects/backend/alembic/versions/c4a8f2e19061_add_user_id_to_documents.py`

## Dependencies Installed

None for this milestone.

## Configuration Changes

None.

## Migration History

### Revision Details

- Revision: `c4a8f2e19061`
- Down revision: `bdc259e18150`
- Migration file: `alembic/versions/c4a8f2e19061_add_user_id_to_documents.py`

### Initial Proposal (Rejected)

The first migration draft used:

- `SELECT MIN(id) FROM users` to backfill existing document rows
- `DELETE FROM documents WHERE user_id IS NULL` for unresolved rows

That strategy was rejected because:

- `MIN(users.id)` could assign documents to the wrong account when multiple users exist
- Unresolved rows would be silently deleted

### Pre-Migration Database Inspection

Database file:

`C:\Projects\AI-Knowledge-Workspace\02-Projects\backend\ai_knowledge_workspace.db`

Inspection results:

- Four existing users were present
- `documenttest@example.com` existed at user ID 4
- Zero document rows existed
- The `documents` table had no `user_id` column
- Alembic current revision was `bdc259e18150`

### Rewritten Migration (Approved and Applied)

The migration was rewritten to be non-destructive:

- Adds `user_id` as nullable first using SQLite `batch_alter_table`
- Counts existing document rows
- If the count is zero, performs no backfill
- If document rows exist, finds the user whose email is exactly `documenttest@example.com`
- If that user does not exist, raises `RuntimeError` and aborts the migration
- Assigns all existing NULL `user_id` rows to that user
- Counts remaining NULL rows; if any remain, raises `RuntimeError`
- Never deletes document rows
- After validation, sets `user_id` to non-nullable, adds the foreign key to `users.id`, and adds the index on `user_id`

Legacy rows are assigned to `documenttest@example.com` because it is the documented account used for existing document upload tests.

### Commands Executed

```text
alembic current
alembic upgrade head
alembic current
uvicorn app.main:app --reload
```

### Migration Verification

- Migration applied successfully
- `alembic current` returned `c4a8f2e19061 (head)`

## Issues Encountered

### Swagger Returned 401 Not Authenticated

Initial condition:

Protected document requests returned:

`{"detail":"Not authenticated"}`

Cause:

The bearer token was not attached in Swagger after server restart or session change.

Resolution:

Reauthorized through the OAuth2 password flow in Swagger.

Result:

The `Authorization: Bearer` header appeared in generated curl requests and protected endpoints worked.

### Uvicorn Restart After Migration

Cause:

The application was restarted after the schema change to verify startup against the migrated database.

Resolution:

Uvicorn restarted successfully with no import, relationship, SQLAlchemy, or startup errors.

## Tests Performed

### Authentication

- Registration and login for Van succeeded
- Registration and login for Ben succeeded

### Ownership Isolation

- Alice received an empty document list when another user owned document ID 1
- Alice received `404 {"detail":"Document not found."}` for retrieve, download, and delete attempts against document ID 1
- `ownerb@example.com` received 200 for login, list, retrieve, download, and delete of its own document
- Deletion returned `{"message":"Document deleted successfully."}`
- The owner-side deletion removed the test document at the end of verification

## Verification Results

- Document ownership and user isolation milestone is complete and manually verified
- Authentication identifies users; authorization isolates document resources by owner
- Document existence is not leaked across accounts via 403 responses

## Remaining Work at That Milestone

The next milestone after ownership was persistent extracted-text storage, followed by document chunking.

---

# Persistent Extracted Text Storage — July 20–21, 2026

## Objective

Persist extracted document text in the database at upload time while preserving ownership, upload response shape, and failure cleanup behavior.

## Context

Text extraction already ran at upload and returned a preview in the API response, but text was discarded after the request. Chunking and embeddings require stored source text tied to each document row.

## Design Decision

- Add nullable `extracted_text` column (`Text`) to `documents`.
- Do not expose full extracted text on list or retrieve endpoints (`DocumentResponse` unchanged).
- Legacy rows remain `NULL` until re-uploaded; no destructive backfill.

## Files Modified (Repository-Proven)

- `02-Projects/backend/app/models/document.py` — added `extracted_text = Column(Text, nullable=True)`
- `02-Projects/backend/app/services/document_service.py` — `create_document(..., extracted_text: str)`
- `02-Projects/backend/app/routers/documents.py` — passes `extracted_text` into `create_document()`

## Files Created (Repository-Proven)

- `02-Projects/backend/alembic/versions/d7b3a4f29182_add_extracted_text_to_documents.py`

## Migration

| Field | Value |
|-------|--------|
| Revision | `d7b3a4f29182` |
| Down revision | `c4a8f2e19061` |
| Strategy | SQLite `batch_alter_table`; add nullable column; no backfill; no row deletion |

## Supported File Types (Repository-Proven)

From `text_extraction_service.py`:

- `.txt` — UTF-8 read
- `.docx` — `python-docx`
- `.pdf` — `pypdf`

## Upload Behavior Preserved

- `ValueError` (unsupported type) → delete file → **400**
- Other extraction errors → delete file → **422**
- DB failure → rollback → delete file → **500**
- Response shape unchanged: `message`, `document_id`, `filename`, `extracted_character_count`, `text_preview` (300 chars)

## Verification

**Historical report supplied by project owner:** milestone implemented, migration applied, and upload persistence manually verified before Document Chunking design began.

**Repository-proven:** code and migration file exist; `create_document` persists `extracted_text`.

## Engineering Lesson

Persist the canonical extracted string before chunking or embedding work so downstream stages reference one database field (`documents.extracted_text`).

---

# Project Protocol, Cursor Rules, and Documentation Foundation — July 18–21, 2026

## Objective

Establish durable AI-assisted development governance and project documentation.

## Files Created (Repository-Proven)

Root documentation:

- `AI_DEVELOPMENT_PROTOCOL.md`
- `PROJECT_STATE.md`
- `ARCHITECTURE.md`
- `BUILD_LOG.md`

Cursor project rules (repository-proven):

- `.cursor/rules/01-project-governance.mdc`
- `.cursor/rules/02-backend-standards.mdc`
- `.cursor/rules/03-implementation-workflow.mdc`
- `.cursor/rules/04-testing-and-review.mdc`
- `.cursor/rules/05-documentation-and-git.mdc`

## Process Rules Adopted

- Extend the existing project; do not recreate it.
- Workflow: **Inspect → Design → Review → Approve → Implement → Test → Document**
- Prefer **full-file replacements** when the project owner applies changes manually.
- Document errors, false assumptions, and unsuccessful tests—not only final successes.
- **Historical report supplied by project owner:** later Cursor sessions must not run Git operations during feature implementation unless explicitly authorized (distinct from earlier owner Git activity on July 17).

## Git History Note

**Repository-proven (July 17 BUILD_LOG entry):** owner executed `git commit` and `git push` for the document services milestone.

**Historical report supplied by project owner:**

- Git installed/configured through VS Code.
- GitHub username `Geolive90` used.
- Files appeared untracked (`U`) during early development.
- GitHub Copilot disabled globally.

## Engineering Lesson

Separate **stable process rules** (`AI_DEVELOPMENT_PROTOCOL.md`, Cursor rules) from **chronological history** (`BUILD_LOG.md`) and **current snapshot** (`PROJECT_STATE.md`).

---

# Document Chunking — Design Phase — July 21, 2026

## Objective

Design chunk storage and splitting strategy between persisted extracted text and future embeddings.

## Context

Pipeline stage:

```text
upload → extract → persist extracted_text → chunk → embed → retrieve → answer
```

## Design Options Considered

| Option | Decision |
|--------|----------|
| Chunks inside `documents` (JSON/BLOB) | **Rejected** — poor normalization, complicates embeddings and citations |
| Separate `document_chunks` table | **Approved** |
| `user_id` on chunks | **Rejected for v1** — ownership via parent `document_id` |
| Embeddings in chunk table now | **Deferred** — separate future storage |
| `langchain-text-splitters` + offset verification | **Rejected for v1** |
| Custom recursive character splitter | **Approved for v1** |

## Approved Schema — `document_chunks`

- `id` (PK)
- `document_id` (FK → `documents.id`, **ON DELETE CASCADE**)
- `chunk_index`
- `chunk_text`
- `character_start` (inclusive)
- `character_end` (exclusive)
- `token_count` (nullable)
- `created_at`
- Unique constraint: `(document_id, chunk_index)`

## Approved Splitter Parameters

- Chunk size: **1000 characters**
- Overlap: **200 characters**
- Separator priority: `\n\n`, `\n`, ` `, character fallback
- Empty or whitespace-only text → **zero chunks**, upload must not fail
- Offsets must satisfy: `text[start:end] == chunk_text` by construction
- No post-hoc `find()` for offsets

## Rationale for Custom Splitter

- No unnecessary dependency (`requirements.txt` still empty at repo root)
- Deterministic behavior
- Exact offsets by slicing source text
- Easier unit testing and debugging
- Schema independent of splitting library

## Next Approved Implementation Phases

1. **Phase 1:** model + migration + SQLite FK enforcement (schema only)
2. **Phase 2:** `chunking_service.py` + unit tests (no DB writes, no upload changes)
3. **Phase 3 (future):** upload orchestration + transactional chunk persistence

---

# Document Chunking — Phase 1 (Schema) — July 21, 2026

## Objective

Create `document_chunks` table, ORM model, relationships, SQLite FK enforcement; **no chunking service or upload integration**.

## Files Created (Repository-Proven)

- `02-Projects/backend/app/models/document_chunk.py`
- `02-Projects/backend/alembic/versions/e8c5b6a30293_create_document_chunks_table.py`

## Files Modified (Repository-Proven)

- `02-Projects/backend/app/models/document.py` — `chunks` relationship with `cascade="all, delete-orphan"`, `order_by="DocumentChunk.chunk_index"`
- `02-Projects/backend/app/models/__init__.py` — exports `DocumentChunk`
- `02-Projects/backend/app/database/database.py` — connect listener sets `PRAGMA foreign_keys=ON`

## Migration (Repository-Proven)

| Field | Value |
|-------|--------|
| Revision | `e8c5b6a30293` |
| Down revision | `d7b3a4f29182` |
| Creates | `document_chunks` with FK `ON DELETE CASCADE`, unique `(document_id, chunk_index)`, indexes on `id` and `document_id` |

## Explicitly Not Changed in Phase 1

- No `chunking_service.py` (at time of Phase 1 completion)
- No router or `document_service.py` upload changes
- No Git operations by Cursor
- Migration file created; execution performed by project owner during verification

---

# Document Chunking — Phase 1 Verification — July 21–22, 2026

## Verification Sequence (Historical Report Supplied by Project Owner)

### 1. Alembic current (before upgrade)

```text
d7b3a4f29182
```

### 2. Alembic upgrade head

```text
d7b3a4f29182 -> e8c5b6a30293
```

Succeeded.

### 3. Alembic current (after upgrade)

```text
e8c5b6a30293 (head)
```

### 4. PRAGMA table_info(document_chunks)

Columns confirmed:

- `id`
- `document_id`
- `chunk_index`
- `chunk_text`
- `character_start`
- `character_end`
- `token_count`
- `created_at`

### 5. Misleading raw SQLite foreign-key check (Investigation — Not a Code Defect)

**Observed result:**

```text
PRAGMA foreign_keys → (0,)
```

using standalone `sqlite3.connect()` against the database file.

**Root cause:**

SQLite enforces foreign keys **per connection**. The standalone `sqlite3.connect()` connection did not execute `PRAGMA foreign_keys=ON`. This result did **not** prove the application configuration was broken.

**Corrective action:**

No code change was made based on `(0,)` alone.

**Follow-up verification (Repository-Proven):**

Application engine check:

```powershell
cd C:\Projects\AI-Knowledge-Workspace\02-Projects\backend
.\.venv\Scripts\python.exe -c "from app.database.database import engine; conn = engine.connect(); print('PRAGMA foreign_keys =', conn.exec_driver_sql('PRAGMA foreign_keys').scalar()); conn.close()"
```

**Result:** `PRAGMA foreign_keys = 1`

**Final verification:** `SessionLocal` uses the same engine; application connections enforce foreign keys. Phase 1 approved.

## Engineering Lesson

When verifying SQLite foreign keys, always use the **same connection path as the application** (SQLAlchemy engine), not a raw standalone connection.

---

# Document Chunking — Phase 2 (Custom Chunking Engine) — July 21, 2026

## Implementation Date

- **Phase 2 implementation** occurred on **July 21, 2026** (repository filesystem timestamps: `chunking_service.py` created ~8:55 PM; test file created ~8:55 PM, corrected ~8:56 PM; transcript/session-proven owner authorization at 8:54 PM).
- **July 22, 2026** was the **documentation audit** and **independent test re-verification** date — not the implementation date. Do not conflate the two when labeling Phase 2 events.

## Objective

Implement and unit-test the custom recursive character splitter **without** database writes or upload integration.

## Files Created (Repository-Proven)

- `02-Projects/backend/app/services/chunking_service.py`
- `02-Projects/backend/tests/test_chunking_service.py`

## Algorithm Implemented (Repository-Proven)

Constants: `CHUNK_SIZE=1000`, `CHUNK_OVERLAP=200`, `SEPARATORS=["\n\n", "\n", " ", ""]`

1. Normalize line endings once (`\r\n` / `\r` → `\n`).
2. If `not text.strip()` → return `[]`.
3. Window loop: compute `max_end = min(start + 1000, len(text))`.
4. If not final segment, `_find_break_point()` recursively searches backward for separator priority.
5. Chunk text = `text[start:end]` (**by construction**).
6. Next window: `start = end - 200` (or `start = end` if no forward progress).

## Normalization and Offset Semantics (Repository-Proven)

- `build_chunks()` normalizes CRLF and CR line endings to LF before chunking.
- `character_start` and `character_end` refer to positions in that **normalized** text, not necessarily the raw input string passed in.
- The slice invariant enforced by tests is:

  ```python
  normalized_text[character_start:character_end] == chunk_text
  ```

- `text_extraction_service.py` does **not** currently guarantee normalization before `documents.extracted_text` is persisted (repository-proven: no line-ending normalization in extraction code).
- **Phase 3 must establish a single canonical normalized-text boundary.**
- **Recommended Phase 3 rule:** normalize extracted text **before both** document persistence and chunk construction, so stored offsets index directly into `documents.extracted_text`.
- Phase 3 must **not** persist raw text while creating offsets from a separately normalized copy.

## Milestone Review Status

Three distinct states must not be conflated:

| State | Phase 2 status |
|-------|----------------|
| **Implemented** | Yes — July 21, 2026 (repository-proven files) |
| **Tests passing** | Yes — 13/13 (session-proven July 21; independently re-verified July 22) |
| **Formally reviewed and approved** | Not recorded immediately after the July 21 implementation summary; supplied by the **July 22 provenance and implementation audit**; following that audit and these documentation corrections, Phase 2 is marked **reviewed and approved** |

## Tests

### July 21 Implementation Session (Transcript/Session-Proven)

- Cursor executed `pytest tests/test_chunking_service.py` during the Phase 2 implementation session.
- One original paragraph-boundary test **failed** because it incorrectly assumed 1002 characters (900 + `\n\n` + 100) fit in a single chunk.
- The test was corrected by separating the intended scenarios: a single-chunk case under 1000 characters, and a separate split-at-`\n\n` case when text exceeds the chunk size.
- Cursor then reported **13 passing tests** (session-reported execution time ~0.18s).
- **Original raw pytest stdout was not preserved** in the conversation transcript (tool results excluded from transcript JSONL).

### July 22 Provenance Audit (Independently Re-Verified)

Command:

```powershell
Set-Location C:\Projects\AI-Knowledge-Workspace\02-Projects\backend
& C:\Projects\AI-Knowledge-Workspace\.venv\Scripts\python.exe -m pytest tests/test_chunking_service.py -v --tb=short
```

**Actual re-verification result:** 13 passed, 0 failed, no warnings, pytest-reported time **0.06 seconds**.

## Test Coverage (Repository-Proven)

**Currently covered:** empty text, whitespace-only text, short text, exactly 1000 characters, 1001 characters with overlap, long multiline text, paragraph boundaries (`\n\n` preserved and split), repeated text overlap geometry, Unicode, line-ending normalization before chunking, sequential chunk indexes, character-level fallback (`test_large_paragraph_splits_with_space_or_character_fallback` uses `"x" * 1500` — **character fallback only**).

**Not adequately covered (future test additions, not current defects):**

- Isolated single-newline (`\n`) separator priority over space
- Isolated space separator priority
- Longer separator-free input spanning more than two chunks
- Exact-window-boundary separator placement
- Explicit repeat-call determinism assertion
- Database invariant: stored normalized `documents.extracted_text` aligns with persisted chunk offsets

## Traceability / Process Discrepancy — July 22 Documentation Audit

The documentation-audit prompt issued on **July 22, 2026** instructed: **“Do not begin Document Chunking Phase 2.”**

At that time, Phase 2 code **already existed** from the preceding evening (July 21 implementation session).

**Root cause:** The reviewed conversation sequence had not captured or acknowledged the earlier Phase 2 completion summary, creating a mismatch between the audit instruction and repository state.

**Classification:** Traceability/process discrepancy — **not a code defect**.

## Slice Invariant

Every test uses:

```python
normalized[chunk.character_start:chunk.character_end] == chunk.chunk_text
```

where `normalized` is the line-ending-normalized source string.

## Engineering Lesson — Normalization Boundary

Chunk offsets are only trustworthy against the same string used for chunking. If `documents.extracted_text` retains CRLF while `build_chunks()` normalizes internally, persisted offsets will not index correctly into the stored column. Phase 3 must normalize once at a defined boundary and use that canonical string for both persistence and offset assignment.

## Not Yet Integrated (Repository-Proven)

- `document_service.py` does not call `build_chunks()`
- Upload does not persist chunk rows
- No chunk API endpoints

## Dependencies Note

`pytest` was installed in `.venv` to run tests (session-proven during July 21 implementation). Root `requirements.txt` remains empty (repository-proven).

---

# Document Chunking — Phase 3 (Upload Orchestration) — July 22, 2026

## Status

**Complete, verified, and approved** (July 22, 2026).

## Objective

Integrate `build_chunks()` into the upload pipeline so every uploaded document automatically generates and persists its chunks within a single database transaction.

## Design Review (Pre-Implementation)

Independent architecture review (July 22, 2026) approved the design with seven clarifications incorporated into `ARCHITECTURE.md` (orchestration contract, flush lifecycle, transaction ownership, idempotency policy, invariants, verification expansion, legacy-document policy).

## Files Modified (Repository-Proven)

| File | Change |
|------|--------|
| `02-Projects/backend/app/services/document_service.py` | Added `create_document_with_chunks()` |
| `02-Projects/backend/app/routers/documents.py` | Upload calls orchestration; response uses `document.extracted_text` |

## Files Created (Repository-Proven)

| File | Purpose |
|------|---------|
| `02-Projects/backend/tests/conftest.py` | Shared in-memory SQLite fixtures |
| `02-Projects/backend/tests/test_document_service_chunks.py` | Service-layer Phase 3 tests (10 tests) |
| `02-Projects/backend/tests/test_upload_chunk_integration.py` | Upload integration tests (6 tests) |

## Files Not Modified (Repository-Proven)

- Models, migrations, `chunking_service.py`, `text_extraction_service.py`, schemas, `main.py`

## Implementation Summary

`create_document_with_chunks()`:

1. Normalizes extracted text via `normalize_line_endings()`.
2. Persists canonical text in `Document.extracted_text`.
3. Calls `build_chunks(canonical_text)`.
4. Appends `DocumentChunk` rows via `document.chunks` relationship.
5. Performs exactly one `db.commit()` (no explicit `flush()`).
6. Returns refreshed `Document`.

Upload router uses `document.extracted_text` for `extracted_character_count` and `text_preview`. Legacy `create_document()` retained (no upload call sites); used in tests for legacy zero-chunk scenarios.

## Verification (Independently Re-Verified — July 22, 2026)

Command:

```powershell
Set-Location C:\Projects\AI-Knowledge-Workspace\02-Projects\backend
& C:\Projects\AI-Knowledge-Workspace\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

**Result:** 29 passed, 0 failed in 12.22s.

Breakdown:

- Phase 2 regression: 13 passed (`test_chunking_service.py`)
- Phase 3 service tests: 10 passed (`test_document_service_chunks.py`)
- Phase 3 integration tests: 6 passed (`test_upload_chunk_integration.py`)

Warnings (pre-existing, not introduced by Phase 3): Starlette TestClient/httpx deprecation; Pydantic class-based `Config` deprecation in schemas.

## Verified Behaviors

- Normalized `extracted_text` persisted; CRLF removed
- Persisted slice invariant for all chunks
- Whitespace-only and empty text → document with zero chunks
- Sequential `chunk_index` (`0..N-1`); `token_count` NULL
- Simulated commit failure → no durable document or chunk rows
- Document deletion cascades to chunks
- Authenticated `.txt` and `.docx` upload persists chunks
- Upload response shape unchanged; count/preview from persisted text
- List/retrieve/download/delete and cross-user 404 unchanged
- Legacy documents with zero chunks remain accessible

## Not in Phase 3 Scope (Confirmed)

No embeddings, vector DB, background jobs, backfill, new migration, or unrelated refactoring.

---

# Historical Backfill — Environment and Workflow Details

The following items supplement earlier milestones. Items marked **(owner-reported)** are not independently provable from the current repository snapshot alone.

## A. Initial Workspace and Environment (July 8–9, 2026)

**(Owner-reported unless noted)**

- Windows 11 development environment.
- Project root: `C:\Projects\AI-Knowledge-Workspace`
- Backend working directory: `02-Projects\backend`
- Early VS Code folder confusion: general projects directory vs specific workspace root — corrected.
- Python virtual environment created at repo-root `.venv` **(repository-proven: `.venv/` exists)**.
- **(Owner-reported)** `pip` upgrade warnings/conflicts may have appeared during setup.
- Uvicorn initially unavailable — resolved by activating venv and installing Uvicorn **(documented in earlier BUILD_LOG entry)**.
- **(Owner-reported)** Python-related VS Code extensions installed.
- **(Repository-proven)** `GET /` returns `{"message": "AI Knowledge Workspace API is running."}` in `app/main.py`.
- **(Owner-reported)** Uvicorn verified at `127.0.0.1:8000`.
- **(Owner-reported)** Possible duplicate Execute click may have contributed to an early crash — recorded as reported possibility, not proven root cause.
- **(Owner-reported)** Multiple open terminals caused confusion about which session was running the server.

## B. Configuration and Database Foundation

**(Mixed evidence)**

- **(Repository-proven)** `02-Projects/backend/.env` exists with `DATABASE_URL=sqlite:///./ai_knowledge_workspace.db` and JWT settings.
- **(Repository-proven)** `app/config.py` uses Pydantic Settings; `app/database/database.py` creates engine and `SessionLocal`; `dependencies.get_db` yields sessions.
- **(Owner-reported)** `engine.url` verified from a second terminal.
- **(Owner-reported)** DB Browser for SQLite installed and used during database path confusion.
- **(Owner-reported)** Wrong placement, unsaved files, or execution-order issues may have affected early table creation visibility.

## C. Alembic Migration Chain (Repository-Proven File Contents)

| Order | Revision | Description |
|-------|----------|-------------|
| 1 | `bdc259e18150` | Add `users.role` (default `user`) |
| 2 | `c4a8f2e19061` | Add `documents.user_id` FK, index; non-destructive backfill rules |
| 3 | `d7b3a4f29182` | Add nullable `documents.extracted_text` |
| 4 | `e8c5b6a30293` | Create `document_chunks` table |

**Repository-proven:** `alembic/env.py` imports `Base` and `from app.models import *`.

**(Owner-reported)** `alembic.ini` visibility confusion during early Alembic setup; `sys.path` and metadata wiring corrected in `env.py`.

## D. Document Management — Additional Details (July 15, 2026)

**(Owner-reported unless noted)**

- Swagger test user: `documenttest@example.com`
- Documents router missing from Swagger until included in `app/main.py` **(repository-proven: main.py includes documents router)**.
- After Uvicorn reload, Swagger lost bearer token → **401** `{"detail":"Not authenticated"}` until reauthorized.
- **(Owner-reported)** Upload of `832 final paper.docx` succeeded; file in `uploads/`; metadata in SQLite.
- **(Owner-reported)** Deletion testing used document ID 2 before deleting ID 1 to avoid losing the only test record too early.
- **(Owner-reported)** Full-file replacement workflow: clear file, paste complete contents, save; unsaved files caused behavior not updating.

## E. Full-File Replacement Protocol

**(Owner-reported, now reflected in AI_DEVELOPMENT_PROTOCOL.md rule 19 and Cursor rules)**

- Specify exact file paths.
- Provide complete final file contents.
- Save before testing; Uvicorn reload resets Swagger auth.
- **(Owner-reported)** Difficulty clearing highlighted editor contents before paste occurred at least once.

## F. Current Alembic Head and Implementation Gap

**Repository-proven code state after Phase 3 upload orchestration:**

- Models: `User`, `Document`, `DocumentChunk`
- Services: `document_service` (includes `create_document_with_chunks()`), `text_extraction_service`, `chunking_service`
- Upload persists normalized `extracted_text` and chunk rows atomically via `create_document_with_chunks()`
- Legacy documents may have zero chunk rows until re-uploaded
- **Next implementation step:** embedding generation (deferred)

---