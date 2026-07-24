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

# Embeddings — Phase 4A (Embedding Metadata Schema) — July 22, 2026

## Status

**Complete, verified, and approved** (July 22, 2026).

## Objective

Add `chunk_embeddings` table and `ChunkEmbedding` ORM for embedding metadata only. Vectors remain in FAISS (Version 1, Phase 4C+). No embedding services, upload changes, or new dependencies.

## Design Decisions (Approved)

| Decision | Verdict |
|----------|---------|
| Store vectors in SQLite (`vector_blob`) | **Rejected** |
| Metadata-only table referencing `chunk_id` | **Approved** |
| FAISS as sole Version 1 vector store | **Approved** |
| Index recovery from `chunk_text` | **Approved** |
| One-to-one `DocumentChunk` ↔ `ChunkEmbedding` | **Approved** |

## Files Created (Repository-Proven)

| File | Purpose |
|------|---------|
| `02-Projects/backend/app/models/chunk_embedding.py` | `ChunkEmbedding` ORM |
| `02-Projects/backend/alembic/versions/f3a1b8c45201_create_chunk_embeddings_table.py` | Migration |
| `02-Projects/backend/tests/test_chunk_embedding_model.py` | Phase 4A tests (8 tests) |

## Files Modified (Repository-Proven)

| File | Change |
|------|--------|
| `02-Projects/backend/app/models/document_chunk.py` | Added `embedding` one-to-one relationship |
| `02-Projects/backend/app/models/__init__.py` | Export `ChunkEmbedding` |
| `02-Projects/backend/tests/conftest.py` | Import `ChunkEmbedding` for test metadata |

## Files Not Modified (Confirmed)

- Upload pipeline, routers, services, config, dependencies
- No `EmbeddingProvider`, `EmbeddingService`, or `VectorStore`
- No new packages installed

## Schema — `chunk_embeddings`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | Integer | PK, indexed |
| `chunk_id` | Integer | FK → `document_chunks.id` ON DELETE CASCADE, NOT NULL, UNIQUE, indexed |
| `model_name` | String(128) | NOT NULL |
| `dimensions` | Integer | NOT NULL |
| `created_at` | DateTime | NOT NULL, default UTC (application-level) |

**Metadata only** — no `vector_blob`.

## Relationships

- `DocumentChunk.embedding` → one-to-one, `uselist=False`, `back_populates="chunk"`, `cascade="all, delete-orphan"`
- `ChunkEmbedding.chunk` → `back_populates="embedding"`

## Cascade Chain

```text
DELETE Document → CASCADE DocumentChunk → CASCADE ChunkEmbedding
```

## Migration (Repository-Proven)

| Field | Value |
|-------|--------|
| Revision | `f3a1b8c45201` |
| Down revision | `e8c5b6a30293` |
| Creates | `chunk_embeddings` with FK ON DELETE CASCADE, unique `chunk_id`, indexes |

## Migration Verification

### Development database

```text
alembic current
```

**Result:** `f3a1b8c45201 (head)`

```text
alembic heads
```

**Result:** `f3a1b8c45201 (head)` — single head, no branch conflict.

### Automated migration test

`test_migration_upgrade_and_downgrade` stamps at `e8c5b6a30293`, upgrades to head, verifies table/columns via raw `sqlite3`, downgrades to `e8c5b6a30293`, confirms table removed.

**Note:** Full `alembic upgrade head` from an **empty** database fails at `bdc259e18150` (`ALTER TABLE users ADD COLUMN role`) because no `users` table exists. This is **pre-existing technical debt** — not introduced by Phase 4A. Must be repaired before Docker deployment, CI fresh-database testing, or cloud deployment.

## Test Verification (Independently Re-Verified — July 22, 2026)

Command:

```powershell
Set-Location C:\Projects\AI-Knowledge-Workspace\02-Projects\backend
& C:\Projects\AI-Knowledge-Workspace\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

**Result:** 37 passed, 0 failed, 3 pre-existing warnings in ~20s.

Breakdown:

- Phase 4A (`test_chunk_embedding_model.py`): 8 passed
- Phase 2 regression: 13 passed
- Phase 3 service: 10 passed
- Phase 3 integration: 6 passed

### Phase 4A test coverage

1. `ChunkEmbedding` persisted for a chunk
2. One-to-one relationship from chunk → embedding
3. One-to-one relationship from embedding → chunk
4. Second embedding for same chunk rejected (`IntegrityError`)
5. Deleting chunk removes embedding
6. Deleting document cascades through chunks to embeddings
7. Migration module structurally valid (revision chain, callable upgrade/downgrade)
8. Migration upgrade and downgrade (Alembic + raw sqlite3 verification)

## Final Read-Only Review Findings (Non-Blocking)

Recorded at Phase 4A pre-commit review:

1. **Redundant index on `chunk_embeddings.id`** — non-unique index duplicates PK index; matches `document_chunks` precedent (`ix_document_chunks_id`).
2. **Duplicate uniqueness on `chunk_id`** — migration defines both `UniqueConstraint` and a separate unique index; functionally correct, structurally redundant.
3. **Cascade tests confirm final behavior only** — tests use ORM `delete()`; they do not isolate raw SQL `ON DELETE CASCADE` from ORM `delete-orphan`. FK definitions are correct; optional raw-SQL test deferred.

**Recommendation:** Approve Phase 4A as-is; observations are cosmetic or test-coverage gaps, not blockers.

## Engineering Lessons

- Embedding metadata belongs in a separate table referencing `chunk_id`, not on `document_chunks`.
- Phase 4A migration tests must stamp at a prior head (`e8c5b6a30293`) because the full Alembic chain cannot bootstrap from empty.
- SQLite FK enforcement (`PRAGMA foreign_keys=ON`) is required in both application engine and test fixtures for cascade tests to be meaningful.

## Not in Phase 4A Scope (Confirmed)

No `EmbeddingProvider`, `EmbeddingService`, `VectorStore`, FAISS, upload integration, search API, new dependencies, or Phase 4B+ work.

---

# Embeddings — Phase 4B (Embedding Provider and Service) — July 22, 2026

## Status

**Complete, verified, and approved** (July 22, 2026).

## Objective

Introduce the application's text-to-vector abstraction layer without adding vector storage, upload orchestration, semantic search, or RAG behavior.

## Purpose

Convert chunk or query text into numeric embedding vectors through a replaceable provider interface. Persistence of vectors (FAISS) and `ChunkEmbedding` metadata rows during upload remain deferred to Phases 4C and 4D.

## Architecture (Repository-Proven)

```text
EmbeddingService
    ↓ depends on
EmbeddingProvider (Protocol)
    ↓ implemented by
SentenceTransformersProvider
```

Factory provides cached singletons: `get_embedding_provider()`, `get_embedding_service()`, and `clear_embedding_caches()` for tests.

## Files Created (11 New Files)

### Embedding package (7 files)

| File | Purpose |
|------|---------|
| `02-Projects/backend/app/services/embedding/__init__.py` | Public exports |
| `02-Projects/backend/app/services/embedding/exceptions.py` | Exception hierarchy |
| `02-Projects/backend/app/services/embedding/provider.py` | `EmbeddingProvider` Protocol |
| `02-Projects/backend/app/services/embedding/service.py` | `EmbeddingService`, `EmbeddingVector` |
| `02-Projects/backend/app/services/embedding/factory.py` | Provider/service factory + cache |
| `02-Projects/backend/app/services/embedding/providers/__init__.py` | Provider package |
| `02-Projects/backend/app/services/embedding/providers/sentence_transformers.py` | `SentenceTransformersProvider` |

### Tests (3 files)

| File | Purpose |
|------|---------|
| `02-Projects/backend/tests/test_embedding_service.py` | Service unit tests (13) |
| `02-Projects/backend/tests/test_embedding_factory.py` | Factory/config tests (6) |
| `02-Projects/backend/tests/test_sentence_transformers_provider.py` | Opt-in integration tests (2) |

### Dependency file (1 file)

| File | Purpose |
|------|---------|
| `02-Projects/backend/requirements.txt` | Pins `sentence-transformers==5.6.0` |

## Files Modified (2 Files)

| File | Change |
|------|--------|
| `02-Projects/backend/app/config.py` | `embedding_provider`, `embedding_model`, `embedding_batch_size` |
| `02-Projects/backend/tests/conftest.py` | Fake providers, autouse cache clearing |

**Total touched:** 11 new + 2 modified = **13 files**

**File count correction:** An earlier implementation report incorrectly stated "10 files under `app/services/embedding/`." The embedding package contains **7 files**, not 10.

## Core Implementation Details

- **`EmbeddingProvider` Protocol:** `embed_text`, `embed_texts`, `model_name`, `dimensions`
- **`EmbeddingService`:** input validation, batching, vector count/dimension validation, provider error normalization
- **`EmbeddingVector`:** single result type (`vector`, `model_name`, `dimensions`)
- **`SentenceTransformersProvider`:** lazy import, lazy model load, Python lists at boundary
- **Canonical model name:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, provider-derived)
- **Configuration:** `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_BATCH_SIZE` only

## Dependencies

| Package | Version | Notes |
|---------|---------|-------|
| `sentence-transformers` | **5.6.0** | Pinned in `requirements.txt` |
| `torch` | **2.13.0** | Installed transitively; **not** pinned |

`requirements.txt` records only the newly managed embedding dependency. It is **not** a complete backend dependency manifest and does not guarantee full environment reproducibility.

## Initial Implementation

Completed without execution errors. Unit tests passed with fake providers before real-provider verification.

## Independent Review — Defects Found and Corrected

### 1. Factory cache bypass

**Issue:** `create_embedding_service()` called `create_embedding_provider(settings)` directly, allowing two provider/model instances if both `get_embedding_provider()` and `get_embedding_service()` were used.

**Fix:** Default service creation reuses cached `get_embedding_provider()` when no explicit provider or settings override is supplied.

**Verified:** `get_embedding_service()._provider is get_embedding_provider()` → `True`.

### 2. Dependency constraint

**Issue:** `sentence-transformers>=2.2.0` was a minimum constraint, not a verified pin.

**Fix:** Replaced with `sentence-transformers==5.6.0` after installation verification.

### 3. Deprecated dimension API

**Issue:** `get_sentence_embedding_dimension()` produced a `FutureWarning` on sentence-transformers 5.6.0.

**Fix:** Provider prefers `get_embedding_dimension()` with legacy fallback.

## Test Verification

### Embedding unit tests

```powershell
pytest tests/test_embedding_service.py tests/test_embedding_factory.py -v
```

**Result:** 19 passed, 0 failed

### Real-provider integration tests

```powershell
$env:RUN_EMBEDDING_INTEGRATION='1'
pytest tests/test_sentence_transformers_provider.py -v
```

**Result:** 2 passed, 0 failed

Verified:

- Model loaded successfully
- `model_name` = `sentence-transformers/all-MiniLM-L6-v2`
- `dimensions` = 384
- One text → one vector; two texts → two vectors
- Vectors returned as Python lists of float-compatible values
- Cached factory service and provider share the same provider instance

### Complete default suite

```powershell
pytest tests/ -v
```

**Result:** 56 passed, 2 skipped (integration), 0 failed, 0 deselected, 3 pre-existing warnings

## Model-Download Behavior

- First real-provider integration run downloaded the model from Hugging Face (~48s)
- Subsequent run loaded from local Hugging Face cache (~27s)
- Windows emitted a symlink-degraded cache warning (non-blocking)
- Unauthenticated Hub notice appeared (non-blocking)

## Non-Blocking Considerations (Not Phase 4B Blockers)

1. `EmbeddingVector` is frozen but its `list` remains internally mutable
2. Integration tests could add stronger explicit batch-order assertions later
3. `torch` is not directly pinned in `requirements.txt`
4. `requirements.txt` is incomplete as a full project dependency manifest

## Not in Phase 4B Scope (Confirmed)

No FAISS, vector storage, `ChunkEmbedding` persistence, upload integration, search, RAG, LLM calls, routers, `app/dependencies.py`, `document_service.py`, database models, migrations, frontend, or OpenAI provider.

## Engineering Lessons

- Default service factory must reuse cached provider to avoid duplicate model loads
- Pin exact verified dependency versions; minimum constraints are not reproducible pins
- Phase 4B unit tests must not require network or model download; integration tests opt-in via `RUN_EMBEDDING_INTEGRATION=1`

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
| 1 | `bdc259e18150` | Add `users.role` (default `user`) — **requires pre-existing `users` table** |
| 2 | `c4a8f2e19061` | Add `documents.user_id` FK, index; non-destructive backfill rules |
| 3 | `d7b3a4f29182` | Add nullable `documents.extracted_text` |
| 4 | `e8c5b6a30293` | Create `document_chunks` table |
| 5 | `f3a1b8c45201` | Create `chunk_embeddings` table (metadata only) |

**Pre-existing technical debt:** The chain cannot initialize an empty database (revision 1 assumes existing tables). Must be repaired before Docker, CI fresh-database testing, or cloud deployment.

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

**Repository-proven code state after Phase 4C vector store / FAISS:**

- Models: `User`, `Document`, `DocumentChunk`, `ChunkEmbedding`
- Services: `document_service`, `text_extraction_service`, `chunking_service`, `embedding` package, `vector_store` package (`FaissVectorStore`)
- Upload persists normalized `extracted_text` and chunk rows atomically via `create_document_with_chunks()`
- Text-to-vector conversion available via `EmbeddingService`; FAISS vector storage available via `VectorStore` / `FaissVectorStore`
- Not yet wired: upload orchestration embed + metadata + index (Phase 4D)
- `chunk_embeddings` metadata schema in place; Alembic head `f3a1b8c45201`
- `requirements.txt` pins `sentence-transformers==5.6.0` and `faiss-cpu==1.14.3`
- **Next implementation step:** Phase 4D — upload pipeline integration (atomic embed + index)

**Updated after Phase 4D closeout (July 22, 2026):**

- Upload indexing orchestration wired (Phase 4D complete)
- Alembic head `a7c2d9e48103`
- **Next implementation step:** Phase 4E — semantic retrieval and search API

---

# Embeddings — Phase 4C (Vector Store / FAISS) — July 22, 2026

## Status

**Complete, verified, and approved** (July 22, 2026).

## Objective

Design and implement a provider-independent vector-storage layer with FAISS as the sole Version 1 concrete implementation. Store embedding vectors keyed by `chunk_id` without persisting vectors in SQLite, upload integration, semantic retrieval, or RAG behavior.

## Chronology

| Step | Event |
|------|-------|
| 1 | Architecture proposal for `VectorStore` Protocol + `FaissVectorStore` |
| 2 | Independent review — refinements: remove `VECTOR_STORE_DIMENSIONS`, expand duplicate-ID rationale, clarify RLock concurrency, add persistence invariant |
| 3 | Final architecture approval |
| 4 | Implementation of vector-store package, config, tests |
| 5 | `faiss-cpu==1.14.3` installed and verified (Windows Python 3.10.5, NumPy 2.2.6) |
| 6 | Initial test results: 70 passed default; 84 passed with FAISS integration |
| 7 | Independent review (Bugbot): same-batch duplicate-ID overwrite defect found |
| 8 | Fix + tests for same-batch duplicate rejection |
| 9 | Targeted verification pass requested before final approval |
| 10 | Manual smoke test executed outside pytest — passed |
| 11 | Git file-count reconciliation: **12 files** (9 created + 3 modified) |
| 12 | Missing edge-case tests added (zero-norm query, batch no-mutation, missing-file clears memory, save-failure cleanup, factory cache refresh, etc.) |
| 13 | Loaded FAISS inner-index structure validation defect found and fixed |
| 14 | Final test results: 16 / 72+22 / 20 / 92+2 |
| 15 | Final approval granted |

## Architecture (Repository-Proven)

```text
EmbeddingProvider.dimensions
        ↓
Vector-store factory (one-time read at construction)
        ↓
FaissVectorStore(dimensions=...)
        ↓
IndexIDMap2(IndexFlatIP)
```

- **`chunk_id`** is the persistent vector identifier
- Cosine-style similarity via L2-normalized vectors + inner-product search
- Duplicate `chunk_id` rejected loudly (including within same batch)
- Core abstraction and FAISS implementation do **not** import embedding; only `factory.py` lazy-imports `get_embedding_provider()`
- Explicit `save()` / `load()`; atomic save via `.faiss.tmp` + replacement
- Missing file → empty valid store; corrupt/wrong-dimension/incompatible structure → `VectorStoreLoadError`
- Per-instance `RLock`; Version 1 single-process limitation

## Files Created (9 New Files)

### Vector store package (6 files)

| File | Purpose |
|------|---------|
| `02-Projects/backend/app/services/vector_store/__init__.py` | Public exports |
| `02-Projects/backend/app/services/vector_store/exceptions.py` | Exception hierarchy |
| `02-Projects/backend/app/services/vector_store/provider.py` | `VectorStore` Protocol, `VectorAddItem`, `VectorSearchResult` |
| `02-Projects/backend/app/services/vector_store/factory.py` | Factory + cached singleton |
| `02-Projects/backend/app/services/vector_store/providers/__init__.py` | Provider package |
| `02-Projects/backend/app/services/vector_store/providers/faiss.py` | `FaissVectorStore` |

### Tests (3 files)

| File | Purpose |
|------|---------|
| `02-Projects/backend/tests/test_vector_store_factory.py` | Factory/config tests (6) |
| `02-Projects/backend/tests/test_vector_store_protocol.py` | Protocol unit tests via `FakeVectorStore` (10) |
| `02-Projects/backend/tests/test_faiss_vector_store.py` | Opt-in FAISS integration tests (20) |

## Files Modified (3 Files)

| File | Change |
|------|--------|
| `02-Projects/backend/app/config.py` | `vector_store_provider`, `faiss_index_path` |
| `02-Projects/backend/requirements.txt` | Added `faiss-cpu==1.14.3` |
| `02-Projects/backend/tests/conftest.py` | `FakeVectorStore`, autouse vector-store cache clearing |

**Total touched:** 9 new + 3 modified = **12 files**

**File count correction:** An earlier Cursor display showed "11 Files Changed." The actual Git working tree contained **12 files** — the under-count likely omitted `providers/__init__.py` or grouped the untracked directory.

## Dependencies

| Package | Version | Notes |
|---------|---------|-------|
| `faiss-cpu` | **1.14.3** | Pinned in `requirements.txt`; verified on Windows cp310 wheel |
| `sentence-transformers` | **5.6.0** | Unchanged from Phase 4B |
| `numpy` | **2.2.6** | Existing in `.venv`; compatible with faiss-cpu 1.14.3 wheel |

Install verification:

```powershell
pip install faiss-cpu==1.14.3
python -c "import faiss; print(faiss.__version__)"
```

**Result:** `1.14.3`

## Defect 1 — Same-Batch Duplicate `chunk_id` Overwrite

**What:** `FaissVectorStore.add()` checked duplicates only against `_known_ids`, not within the incoming batch. Two items with the same `chunk_id` in one call could pass validation; FAISS would silently overwrite.

**Why it mattered:** Approved architecture requires duplicate IDs to fail loudly — duplicates indicate orchestration bugs (double upload, retry after partial failure, inconsistent rebuild). Silent overwrite would mask drift between SQLite and FAISS.

**Fix:** Added `seen_in_batch` set; reject if `chunk_id in _known_ids or chunk_id in seen_in_batch` before any FAISS mutation.

**Verified:** `test_duplicate_chunk_id_in_same_batch_raises` (protocol + FAISS integration).

## Defect 2 — Loaded Inner Index Not Validated as `IndexFlatIP`

**What:** After `faiss.read_index()`, the inner index is returned as a generic `Index` SWIG proxy — `isinstance(loaded.index, faiss.IndexFlatIP)` fails even for valid indexes saved from `IndexIDMap2(IndexFlatIP)`.

**Why it mattered:** A corrupt or wrong-type index file could load without detecting structural incompatibility with the approved inner-product design.

**Fix:** Added `faiss.downcast_index(loaded.index)` validation in `load()`; raise `VectorStoreLoadError` if inner structure is not `IndexFlatIP`.

**Verified:** `test_loaded_index_validates_id_map_flat_ip_structure`; all persistence tests still pass.

## Manual Smoke Test (Outside pytest)

Executed with temporary path (cleaned up afterward):

```powershell
# Sequence: add → search → save → new instance → load → search → remove → save → new instance → load → verify
```

| Field | Result |
|-------|--------|
| Dimensions | 4 |
| IDs added | `[10, 20, 30]` |
| Before save | `[(10, 1.0), (30, 0.993884), (20, 0.0)]` |
| After reload | Identical IDs, ordering, scores (delta `[0.0, 0.0, 0.0]`) |
| Removed count | 1 (ID 10) |
| Final count | 2 |
| After removal IDs | `[30, 20]` |
| Default index untouched | `data/faiss/chunk_index.faiss` did not exist before or after |

## Test Verification

### Targeted vector-store unit tests

```powershell
pytest tests/test_vector_store_factory.py tests/test_vector_store_protocol.py -q
```

**Result:** 16 passed in ~30s

### Full default suite

```powershell
pytest tests/ -q
```

**Result:** 72 passed, 22 skipped, 3 pre-existing warnings in ~51s

(22 skipped = 20 FAISS integration + 2 embedding integration)

### FAISS integration only

```powershell
$env:RUN_FAISS_INTEGRATION='1'
pytest tests/test_faiss_vector_store.py -q
```

**Result:** 20 passed in ~0.3s

### Full suite with FAISS integration

```powershell
$env:RUN_FAISS_INTEGRATION='1'
pytest tests/ -q
```

**Result:** 92 passed, 2 skipped (embedding integration only), 3 pre-existing warnings in ~47s

## Persistence Invariant Verified

After `add()` → `save()` → new `FaissVectorStore` → `load()` → `search()`:

- Identical chunk IDs
- Identical neighbor ordering
- Scores within `1e-5` tolerance

Test: `test_persistence_invariant_across_reload`

## Known Version 1 Limitations

- Single-process RLock; multi-worker deployments each hold independent index copies
- Explicit `save()` required — no auto-save on mutation
- Ownership pre-filtering not in VectorStore (Phase 4E)
- Index rebuild from `chunk_text` designed but not implemented (Phase 4F)
- `search(k<=0)` returns `[]` without acquiring lock (no index access — acceptable)

## Not in Phase 4C Scope (Confirmed)

No upload embedding integration, semantic retrieval API, RAG, routers, migrations, model/schema changes, `app/dependencies.py` wiring, or Phase 4D orchestration.

---

# Embeddings — Phase 4D (Document Indexing Orchestration) — July 22, 2026

## Status

**Complete, verified, and approved** (July 22, 2026).

## Objective

Implement the orchestration layer connecting existing components: after upload/chunking, embed chunks → persist `chunk_embeddings` metadata → add vectors to FAISS → save index → update document indexing status. Phases 1–3 already handle upload → extract → chunk → persist; Phase 4D indexes **existing persisted chunks**.

## Chronology

| Step | Event |
|------|-------|
| 1 | Architecture proposal for `IndexingService`, status columns, upload/index/delete integration |
| 2 | Independent architecture review — approved consistency sequence, entry points, deletion order, concurrency model |
| 3 | Implementation: indexing package, migration, service helpers, DI wiring, router integration |
| 4 | Unit tests with fakes; API tests; FAISS integration tests |
| 5 | Independent implementation review — architectural fidelity confirmed |
| 6 | Targeted verification pass — 8 gap areas identified as unproven |
| 7 | Gap-closure verification — 11 compensation/deletion tests added |
| 8 | Defects discovered and fixed: delete/index race, compensation error context, failed-status rollback, stored-file delete logging |
| 9 | Final test suites: 120 passed default; 145 passed all gates |
| 10 | Final approval granted for closeout |

## Architecture (Repository-Proven)

```text
IndexingService (EmbeddingService + VectorStore + stale timeout)
        ↓
claim processing (optimistic DB + RLock)
        ↓
optional purge → embed → add → save → metadata commit
```

**Consistency sequence (definitive):**

1. In-process document lock + conditional DB update → `processing`
2. Purge prior artifacts if retry/force/stale reclaim
3. Zero chunks → mark `indexed` immediately
4. Embed texts
5. `vector_store.add()` (in-memory)
6. `vector_store.save()` (**disk before indexed status**)
7. DB commit: `chunk_embeddings` + `indexing_status=indexed` + `indexed_at` (same transaction)
8. On failure: idempotent purge attempt + `failed` status

## Files Created (10 New Files)

### Indexing service package (5 files)

| File | Purpose |
|------|---------|
| `02-Projects/backend/app/services/indexing/__init__.py` | Public exports |
| `02-Projects/backend/app/services/indexing/exceptions.py` | Exception hierarchy |
| `02-Projects/backend/app/services/indexing/result.py` | `IndexingResult`, `PurgeResult` |
| `02-Projects/backend/app/services/indexing/service.py` | `IndexingService` orchestration |
| `02-Projects/backend/app/services/indexing/factory.py` | Factory + cached singleton |

### Migration (1 file)

| File | Purpose |
|------|---------|
| `02-Projects/backend/alembic/versions/a7c2d9e48103_add_document_indexing_fields.py` | Indexing lifecycle columns on `documents` |

### Tests (5 files)

| File | Purpose |
|------|---------|
| `02-Projects/backend/tests/test_indexing_service.py` | Unit tests with fakes (12) |
| `02-Projects/backend/tests/test_indexing_api.py` | API tests (5) |
| `02-Projects/backend/tests/test_indexing_faiss_integration.py` | FAISS integration (1) |
| `02-Projects/backend/tests/test_indexing_verification.py` | Independent review verification (22) |
| `02-Projects/backend/tests/test_indexing_compensation_gaps.py` | Compensation/deletion gap closure (11) |

## Files Modified (9 Files)

| File | Change |
|------|--------|
| `02-Projects/backend/app/models/document.py` | Indexing lifecycle columns |
| `02-Projects/backend/app/services/document_service.py` | Indexing chunk helpers |
| `02-Projects/backend/app/config.py` | `indexing_stale_timeout_seconds` |
| `02-Projects/backend/app/dependencies.py` | `get_indexing_service_dependency()` |
| `02-Projects/backend/app/routers/documents.py` | Upload/index/delete integration |
| `02-Projects/backend/app/schemas/document.py` | Indexing response schemas |
| `02-Projects/backend/tests/conftest.py` | Fake indexing service, cache clearing |
| `02-Projects/backend/tests/test_chunk_embedding_model.py` | Legacy-table migration test fix |
| `02-Projects/backend/tests/test_upload_chunk_integration.py` | Upload indexing fields |

**Total touched:** 10 new + 9 modified = **19 files**

## Migration

| Field | Value |
|-------|--------|
| Revision | `a7c2d9e48103` |
| Down revision | `f3a1b8c45201` |
| Adds | `indexing_status`, `indexing_error`, `indexed_at`, `indexing_started_at` |

## API Changes

| Endpoint | Change |
|----------|--------|
| `POST /documents/upload` | Indexing after chunk persist; indexing fields in response |
| `POST /documents/{document_id}/index` | **New** — retry / force reindex |
| `DELETE /documents/{document_id}` | Purge before DB delete; document lock |
| `GET /documents*` | `indexing_status`, `indexed_at` on `DocumentResponse` |

## Dependency Changes

None new. Uses Phase 4B/4C dependencies.

## Defects Found and Fixed During Verification

1. **Delete/index race** — document lock through purge + DB delete
2. **Compensation error swallowed** — log + append to `indexing_error`
3. **Failed-status commit rollback** — `db.rollback()` on commit failure
4. **Stored-file delete HTTP 500** — catch, log warning, return 200

## Final Test Results

| Suite | Result |
|-------|--------|
| Phase 4D indexing tests | 51 passed |
| Default `pytest tests/` | 120 passed, 25 skipped |
| All gates | 145 passed, 0 skipped |

## Known Version 1 Limitations

Documented in `ARCHITECTURE.md` and `PROJECT_STATE.md`. See `ENGINEERING_LESSONS.md` for detailed lessons.

---

# Embeddings — Phase 4E (Semantic Retrieval and Search API) — July 23, 2026

## Status

**Complete, verified, and approved** (July 23, 2026). Documentation closeout only at this step — application code and tests were implemented and verified earlier; not yet committed.

## Objective

Implement owner-scoped semantic search over indexed document chunks via `POST /search`. Thin router / fat `RetrievalService` boundary. Global FAISS search with bounded over-fetch and application-layer ownership plus `indexing_status='indexed'` filtering. No LLM answering, RAG response generation, citations, or conversation history.

## Inspection Findings (Pre-Implementation)

- Phase 4D indexing orchestration complete and committed at prior HEAD
- No retrieval package, search router, or search schemas at inspection time
- FAISS index global; `VectorStore.search()` ownership-agnostic (Phase 4C invariant)
- FAISS chunk IDs aligned with `document_chunks.id`
- `indexing_status='indexed'` required as retrieval readiness gate
- `DocumentResponse` on list/detail endpoints does not include `chunk_count` or `vectors_indexed`

## Approved Architecture

```text
POST /search (JWT)
        ↓
RetrievalService.search()
        ↓
validate query → embed query → bounded over-fetch
        ↓
VectorStore.search() (global FAISS)
        ↓
get_indexed_searchable_chunks_by_ids() (ownership + indexed gate)
        ↓
rank and limit → SearchResponse
```

**Explicit Phase 4E boundary:** retrieval only — no LLM, no RAG, no citations, no conversations.

## Implementation Plan

Two-commit sequence:

1. **Commit 1 — Retrieval core:** `RetrievalService`, exceptions, factory, document-service hydration helper, config, unit tests
2. **Commit 2 — HTTP API:** search schemas, router, DI wiring, main registration, API tests, conftest fakes

## Commit 1 — Retrieval Core

### Files Created (6)

| File | Role |
|------|------|
| `02-Projects/backend/app/services/retrieval/__init__.py` | Package exports |
| `02-Projects/backend/app/services/retrieval/exceptions.py` | `RetrievalError` hierarchy |
| `02-Projects/backend/app/services/retrieval/result.py` | Immutable `SearchHit` and `SearchResult` dataclasses |
| `02-Projects/backend/app/services/retrieval/service.py` | `RetrievalService.search()` orchestration |
| `02-Projects/backend/app/services/retrieval/factory.py` | Factory and cache helpers |
| `02-Projects/backend/tests/test_retrieval_service.py` | Unit tests (12) |

### Files Modified (2)

| File | Change |
|------|--------|
| `02-Projects/backend/app/config.py` | Retrieval settings (top_k, over-fetch, max query length) |
| `02-Projects/backend/app/services/document_service.py` | `SearchableChunkRecord`, `get_indexed_searchable_chunks_by_ids()` |

### Retrieval Configuration Defaults

| Setting | Default |
|---------|---------|
| `search_default_top_k` | 10 |
| `search_max_top_k` | 50 |
| `search_over_fetch_multiplier` | 5 |
| `search_over_fetch_min_buffer` | 20 |
| `search_max_fetch_k` | 200 |
| `search_max_query_length` | 4000 |

### RetrievalService Behavior

- Query validation (non-empty, max length) → `RetrievalValidationError`
- Query embedding via `EmbeddingService` → `RetrievalEmbeddingError`
- Bounded over-fetch: `fetch_k = min(index_count, search_max_fetch_k, max(top_k, top_k × multiplier, top_k + buffer))`
- Global FAISS search via `VectorStore.search()` — ownership-agnostic
- Hydrate via `get_indexed_searchable_chunks_by_ids(chunk_ids, user_id, document_id?)`
- Ownership filtering: only chunks belonging to authenticated user
- Indexing-status gate: only `indexing_status='indexed'` documents (literal string in document service)
- Optional document scope: `document_id` restricts to one owned indexed document → `RetrievalNotFoundError` if missing or not owned
- Rank by FAISS score; return at most `top_k` results (may be fewer after filtering)

### Commit 1 Test Results

| Suite | Result |
|-------|--------|
| Phase 4E retrieval unit tests | **12 passed** |
| Full default suite | **132 passed**, 25 skipped |

## Commit 2 — HTTP API

### Files Created (3)

| File | Role |
|------|------|
| `02-Projects/backend/app/schemas/search.py` | `SearchRequest`, `SearchResponse`, result item schemas |
| `02-Projects/backend/app/routers/search.py` | `POST /search` thin router |
| `02-Projects/backend/tests/test_search_api.py` | API tests (13) |

### Files Modified (3)

| File | Change |
|------|--------|
| `02-Projects/backend/app/dependencies.py` | `get_retrieval_service_dependency()` |
| `02-Projects/backend/app/main.py` | Registered `search.router` |
| `02-Projects/backend/tests/conftest.py` | `fake_retrieval_service`, `clear_retrieval_caches()` in autouse |

### Exception Hierarchy and HTTP Mappings

| Exception | HTTP | Response detail |
|-----------|------|-----------------|
| `RetrievalValidationError` | 422 | Validation message from service |
| `RetrievalNotFoundError` | 404 | `"Document not found."` |
| `RetrievalEmbeddingError` | 500 | `"Search could not be completed."` |
| `RetrievalVectorStoreError` | 500 | `"Search could not be completed."` |
| `RetrievalError` (base) | 500 | `"Search could not be completed."` |

Missing or invalid JWT → **401** (existing auth dependency).

### Commit 2 Test Results

| Suite | Result |
|-------|--------|
| Phase 4E search API tests | **13 passed** |
| Full default suite | **145 passed**, 25 skipped, 0 failed, 3 pre-existing warnings |

## Files Summary (Phase 4E Total)

**Created (9):** retrieval package (5), `schemas/search.py`, `routers/search.py`, `tests/test_retrieval_service.py`, `tests/test_search_api.py`

**Modified (5):** `config.py`, `document_service.py`, `dependencies.py`, `main.py`, `tests/conftest.py`

**Total touched:** 14 files. No new migrations. No new runtime dependencies.

## Manual Verification (July 23, 2026)

| Item | Value |
|------|-------|
| Alembic head | `a7c2d9e48103` (unchanged — no Phase 4E migration) |
| Manual test user | `phase4e-manual@example.com` |
| Manual document ID | 4 |
| Manual document filename | `phase4e-search.txt` |
| Indexing status | `indexed` |
| Upload response `chunk_count` | 1 |
| Upload response `vectors_indexed` | 1 |
| Search query | `neural networks verification` |
| Successful score | `0.5060461163520813` |

**Verified scenarios:**

- **HTTP 200** — global semantic search returned one expected chunk with score (single result; not used to verify multi-result ordering)
- **HTTP 200** — document-scoped semantic search (`document_id=4`) returned the same single chunk
- **422** — empty/invalid query rejected
- **401** — unauthenticated request rejected
- **404** — scoped search on non-owned or missing document
- Document list, get, and download regression checks passed
- Delete intentionally skipped to preserve search test document

**Pre- and post-test Git status:** Limited to expected Phase 4E application and documentation changes only.

## Manual Verification Expectation Correction

During manual verification, an additional check expected `chunk_count` and `vectors_indexed` on `GET /documents` (list/detail).

**Finding:** Those fields were absent because the existing `DocumentResponse` contract does not include them. They belong to upload and indexing outcome responses (e.g. `POST /documents/upload`).

**Upload verification confirmed both values:** `chunk_count=1`, `vectors_indexed=1`.

**Disposition:** Classified as a **verification-expectation mismatch**, not a code regression. No production-code change made. Richer document metadata on list/detail endpoints recorded as a possible future enhancement only.

## Final Automated Test Baseline

| Suite | Result |
|-------|--------|
| Phase 4E retrieval unit tests | 12 passed |
| Phase 4E search API tests | 13 passed |
| Full default suite | **145 passed**, 25 skipped, 0 failed, 3 pre-existing warnings |

## Not in Phase 4E Scope (Confirmed)

- LLM answering and RAG response generation
- Citations and conversation history
- Changes to `DocumentResponse` or document list/detail/download endpoints
- Index rebuild from `chunk_text` (Phase 4F)
- New migrations or runtime dependencies

---
