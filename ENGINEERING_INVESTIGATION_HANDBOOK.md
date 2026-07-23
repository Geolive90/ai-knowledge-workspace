# AI Knowledge Workspace — Engineering Investigation Handbook

## Document role

This handbook is **not a changelog**. It records **how engineering problems were investigated, reasoned about, fixed, and verified** across the AI Knowledge Workspace project.

It **complements** (does not replace):

| Document | Role |
|----------|------|
| [`BUILD_LOG.md`](BUILD_LOG.md) | Chronological history, commands, file lists |
| [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) | Transferable lessons and principles |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | Enduring design decisions and flows |
| [`PROJECT_STATE.md`](PROJECT_STATE.md) | Current snapshot and roadmap |
| [`AI_DEVELOPMENT_PROTOCOL.md`](AI_DEVELOPMENT_PROTOCOL.md) | Process rules for AI-assisted development |

When this handbook and another document disagree, **committed code + migration files + tests** are the tie-breaker. Owner-reported details are labeled explicitly. Inferred or partially reconstructable claims are labeled in the case body.

---

## How to read this document

**Audience:** Engineers reviewing this repository, contributors extending Version 1, and reviewers evaluating investigation discipline.

**What this is:** A catalog of **investigations** — how symptoms were isolated, root causes confirmed, fixes verified, and principles extracted. This is **public engineering documentation** intended to demonstrate investigation discipline, not merely list fixes.

**What this is not:** A chronological build log ([`BUILD_LOG.md`](BUILD_LOG.md)), a transferable-lessons summary ([`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md)), or a current-state snapshot ([`PROJECT_STATE.md`](PROJECT_STATE.md)). [`ARCHITECTURE.md`](ARCHITECTURE.md) records the intended system design; this handbook records how specific engineering failures and risks were investigated.

**Evidence labels used throughout:**

| Label | Meaning |
|-------|---------|
| *Repository-proven* | Committed code, tests, migrations, or BUILD_LOG entries |
| *Owner-confirmed* | Manual validation reported by project owner |
| *Partially reconstructable* | Symptom and resolution known; some paths or timestamps uncertain |
| *Not reconstructable* | Insufficient Git-backed evidence; claim omitted or explicitly labeled |

**Navigation:** Each case includes a **Recognition pattern** (how to spot it again) and **Related** links to source documents. Cross-cutting methodology appears in the [Debugging decision framework](#debugging-decision-framework) and [Permanent safety rules](#permanent-safety-rules). For chronological commands and file lists, follow links into [`BUILD_LOG.md`](BUILD_LOG.md). For durable principles without investigation detail, see [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md).

---

## Standard investigation template

Every case below follows this structure:

| Field | Meaning |
|-------|---------|
| **Case** | Number and title |
| **Phase / date** | Milestone and approximate date where known |
| **System layer** | Router, service, DB, filesystem, test, process, etc. |
| **Initial symptom** | What was observed first |
| **User-visible error** | HTTP status, message, or test failure |
| **Known-good evidence** | What already worked and proved context |
| **Initial hypotheses** | First guesses before isolation |
| **Diagnostic steps** | Ordered checks that narrowed cause |
| **Root cause** | Confirmed failure mechanism |
| **Corrective action** | Fix or accepted workaround |
| **Verification** | How success was proven |
| **Incorrect assumptions / risky alternatives avoided** | Wrong paths not taken |
| **General engineering principle** | Durable takeaway |
| **Recognition pattern** | How to spot this again |
| **Engineering Explanation** | Plain-language summary for mentoring |
| **Related files / tests / commits** | Pointers for deeper reading |
| **Diagnostic Questions** | Questions to ask before revealing the answer |

---

## Table of contents

1. [Cases 1–10 — Foundation, auth, documents, ownership](#cases-110--foundation-auth-documents-ownership)
2. [Cases 11–20 — Phase 4D indexing, concurrency, compensation](#cases-1120--phase-4d-indexing-concurrency-compensation)
3. [Cases 21–30 — Verification and engineering governance](#cases-2130--verification-and-engineering-governance)
4. [Appendix — Earlier-phase investigations (Cases A–F)](#appendix--earlier-phase-investigations-cases-af)
5. [Manual Phase 4D validation walkthrough (Case 26)](#case-26--phase-4d-upload-failure-caused-by-outdated-alembic-schema)
6. [Debugging decision framework](#debugging-decision-framework)
7. [Layer-tracing maps](#layer-tracing-maps)
8. [Permanent safety rules](#permanent-safety-rules)
9. [Handbook accuracy audit](#handbook-accuracy-audit)

---

## Cases 1–10 — Foundation, auth, documents, ownership

### Case 1 — Incorrect workspace / folder context

| Field | Detail |
|-------|--------|
| **Phase / date** | Foundation — July 8–9, 2026 |
| **System layer** | Developer environment / IDE |
| **Initial symptom** | Commands or file edits appeared to have no effect; wrong project opened |
| **User-visible error** | Uvicorn not found; files saved to unexpected locations *(owner-reported)* |
| **Known-good evidence** | Correct root is `C:\Projects\AI-Knowledge-Workspace`; backend is `02-Projects/backend` per `BUILD_LOG.md` and `AI_DEVELOPMENT_PROTOCOL.md` |
| **Initial hypotheses** | Missing dependency; broken code |
| **Diagnostic steps** | Confirm IDE folder root; compare path in terminal `cwd` vs expected backend path; list directory contents |
| **Root cause** | General projects directory opened instead of the specific workspace root *(BUILD_LOG: "Incorrect Folder Selection")* |
| **Corrective action** | Reopen correct project root in VS Code |
| **Verification** | Uvicorn and Python commands run from intended directory |
| **Incorrect assumptions avoided** | Reinstalling Python before verifying folder context |
| **Principle** | **Environment context is the first variable** — wrong folder mimics many unrelated failures |
| **Recognition pattern** | "It worked yesterday" + path confusion + missing modules |
| **Engineering Explanation** | Before debugging code, prove you are in the repository root and the backend subdirectory for server commands. |
| **Related** | `BUILD_LOG.md` § Earlier Foundation; `AI_DEVELOPMENT_PROTOCOL.md` §4 |
| **Diagnostic Questions** | What path is your terminal in? What path is the IDE workspace root? Does `app/main.py` exist relative to your cwd? |

---

### Case 2 — Missing Uvicorn or inactive virtual environment

| Field | Detail |
|-------|--------|
| **Phase / date** | Foundation — July 8–9, 2026 |
| **System layer** | Python environment |
| **Initial symptom** | Server start command fails |
| **User-visible error** | `Uvicorn not found` *(BUILD_LOG)* |
| **Known-good evidence** | `.venv` exists at repository root *(repository-proven in BUILD_LOG)* |
| **Initial hypotheses** | Uvicorn not installed globally |
| **Diagnostic steps** | Check venv activation; `which python` / `Get-Command python`; try `.venv\Scripts\python -m uvicorn` |
| **Root cause** | Virtual environment not active or Uvicorn installed only inside venv |
| **Corrective action** | Activate `.venv`; install Uvicorn in active environment |
| **Verification** | `uvicorn app.main:app --reload` from `02-Projects/backend` succeeds |
| **Incorrect assumptions avoided** | Editing application code when CLI cannot import packages |
| **Principle** | **Prove the active interpreter** before attributing failures to application logic |
| **Recognition pattern** | `ModuleNotFoundError` / command not found immediately after opening new terminal |
| **Engineering Explanation** | FastAPI runs inside a venv; the shell must use that Python, not system Python. |
| **Related** | `BUILD_LOG.md` § Uvicorn Not Found |
| **Diagnostic Questions** | Which Python executable is running? Is the venv activated? Can you import `fastapi` in that shell? |

---

### Case 3 — Database configuration / path verification

| Field | Detail |
|-------|--------|
| **Phase / date** | Foundation / ownership — July 2026 |
| **System layer** | Configuration + SQLite filesystem |
| **Initial symptom** | Migrations or queries appear to hit wrong/empty database |
| **User-visible error** | Unexpected empty tables; migration state mismatch *(inferred from BUILD_LOG inspection steps)* |
| **Known-good evidence** | `DATABASE_URL=sqlite:///./ai_knowledge_workspace.db` in backend `.env` *(BUILD_LOG repository-proven)*; Alembic uses same URL via `alembic.ini` |
| **Initial hypotheses** | Migration not applied; wrong DB file |
| **Diagnostic steps** | `alembic current`; locate `ai_knowledge_workspace.db` relative to backend cwd; inspect tables with sqlite3 |
| **Root cause** | Multiple possible DB files if cwd differs; relative SQLite paths bind to **current working directory** |
| **Corrective action** | Always run Alembic and Uvicorn from `02-Projects/backend`; confirm single DB file path |
| **Verification** | `alembic current` matches expected head; inspection queries match application data |
| **Incorrect assumptions avoided** | Inspecting a DB file in repo root while app writes to backend-relative path |
| **Principle** | **SQLite relative paths are cwd-sensitive** |
| **Recognition pattern** | Schema looks old despite "successful" migration; data disappears between terminals |
| **Engineering Explanation** | The same connection string can point at different files depending on where you start the process. |
| **Related** | `BUILD_LOG.md` ownership pre-migration inspection; `PROJECT_STATE.md` § Alembic debt |
| **Diagnostic Questions** | Where is the `.db` file on disk? From which directory did you run Alembic? Does `alembic current` match the code you deployed? |

---

### Case 4 — Duplicate-email UNIQUE constraint returning HTTP 500

| Field | Detail |
|-------|--------|
| **Phase / date** | Authentication — July 2026 |
| **System layer** | Router / service / SQLite |
| **Initial symptom** | Re-registering existing email crashes request |
| **User-visible error** | HTTP **500** Internal Server Error *(BUILD_LOG)* |
| **Known-good evidence** | First registration succeeds with 201; login returns 200 + token |
| **Initial hypotheses** | Database corruption; auth bug |
| **Diagnostic steps** | Reproduce with same email; read server traceback for `UNIQUE constraint failed` |
| **Root cause** | Application reached DB unique constraint without pre-check or controlled exception mapping |
| **Corrective action** | Duplicate-email check + return **400** with `"A user with this email already exists."` |
| **Verification** | Second registration returns **400** with explicit detail *(BUILD_LOG)* |
| **Incorrect assumptions avoided** | Treating all registration failures as server bugs |
| **Principle** | **Translate expected constraint violations into client errors (4xx)** |
| **Recognition pattern** | 500 on duplicate create/update operations |
| **Engineering Explanation** | Unique violations are often user input problems, not server faults. |
| **Related** | [`BUILD_LOG.md`](BUILD_LOG.md) § Duplicate Email Caused 500 Error; commit `479b77c` area |
| **Diagnostic Questions** | Is this a predictable user mistake? What HTTP status should clients receive? Did the DB error reach the client unchanged? |

---

### Case 5 — Missing documents router in Swagger

| Field | Detail |
|-------|--------|
| **Phase / date** | Document management — July 15, 2026 |
| **System layer** | Application wiring (`main.py`) |
| **Initial symptom** | Swagger UI lacks Documents section |
| **User-visible error** | Endpoints absent from OpenAPI — not a runtime error |
| **Known-good evidence** | Auth and health routes visible; `documents.py` router exists |
| **Initial hypotheses** | Router code broken; Swagger cache |
| **Diagnostic steps** | Read `app/main.py` `include_router` list; compare to `app/routers/documents.py` |
| **Root cause** | `documents.router` not imported/included in FastAPI app *(BUILD_LOG)* |
| **Corrective action** | Import and `app.include_router(documents.router)` |
| **Verification** | Documents section appears in Swagger; upload callable |
| **Incorrect assumptions avoided** | Rewriting document service when wiring was missing |
| **Principle** | **Routers must be registered to exist at runtime** |
| **Recognition pattern** | New module works in isolation but never appears in API docs |
| **Engineering Explanation** | FastAPI only exposes routers you attach to the app object. |
| **Related** | [`BUILD_LOG.md`](BUILD_LOG.md) § Documents Router Missing from Swagger; `app/main.py` |
| **Diagnostic Questions** | Is the router defined? Is it included in `main.py`? Can you hit the path with curl even if Swagger hides it? |

---

### Case 6 — Lost Swagger authorization after Uvicorn reload

| Field | Detail |
|-------|--------|
| **Phase / date** | Document management / ownership — July 2026 |
| **System layer** | Client tooling (Swagger UI) + dev server reload |
| **Initial symptom** | Protected routes suddenly return 401 |
| **User-visible error** | `{"detail":"Not authenticated"}` *(BUILD_LOG)* |
| **Known-good evidence** | Same token worked before reload; login still returns 200 |
| **Initial hypotheses** | JWT secret changed; auth regression |
| **Diagnostic steps** | Re-login; re-authorize OAuth2 in Swagger; inspect `Authorization` header in curl snippet |
| **Root cause** | Swagger UI drops bearer token state on reload *(BUILD_LOG)* — not a server bug |
| **Corrective action** | Re-authorize via OAuth2 password flow after `--reload` |
| **Verification** | Upload succeeds after reauthorization *(owner-reported `832 final paper.docx`)* |
| **Incorrect assumptions avoided** | Changing JWT code when client lost header |
| **Principle** | **Separate client session state from server auth correctness** |
| **Recognition pattern** | 401 immediately after code save triggers reload |
| **Engineering Explanation** | Swagger keeps the token in browser UI state; reload clears it. |
| **Related** | `BUILD_LOG.md` § Swagger 401; engineering lesson in `BUILD_LOG` § Engineering Lessons (July 15) |
| **Diagnostic Questions** | Did the server restart? Is the Authorization header present on the failing request? Does a fresh login fix it? |

---

### Case 7 — Incorrectly placed uploads directory

| Field | Detail |
|-------|--------|
| **Phase / date** | Document management — July 2026 |
| **System layer** | Filesystem / `file_handler` utility |
| **Initial symptom** | Uploaded files not where expected; download fails |
| **User-visible error** | File not found on download *(inferred)*; upload may appear to succeed |
| **Known-good evidence** | `UPLOAD_FOLDER` configured in `app/utils/file_handler.py`; `.gitignore` ignores `02-Projects/backend/uploads/` |
| **Initial hypotheses** | Upload failed silently; DB inconsistent |
| **Diagnostic steps** | Trace `save_uploaded_file()` path; list actual upload directory; compare cwd |
| **Root cause** | Uploads directory created or referenced at wrong path *(BUILD_LOG: owner-reported, resolution details partially summarized)* |
| **Corrective action** | Align storage directory with intended backend location |
| **Verification** | Physical file exists after upload; download returns 200 |
| **Incorrect assumptions avoided** | Database debugging before confirming file on disk |
| **Principle** | **Verify physical storage path independently of DB metadata** |
| **Recognition pattern** | DB row exists; file missing on filesystem |
| **Engineering Explanation** | Upload is two artifacts: DB row and bytes on disk — check both. |
| **Related** | `BUILD_LOG.md` § Uploads Directory Placement; `.gitignore` uploads entry |
| **Diagnostic Questions** | Where does `file_handler` write files? Does that directory exist? Does the stored path in DB match disk? |

---

### Case 8 — Document ownership migration / backfill strategy

| Field | Detail |
|-------|--------|
| **Phase / date** | Ownership — July 18–20, 2026 |
| **System layer** | Alembic migration / data backfill |
| **Initial symptom** | Need `user_id` on existing documents without wrong ownership |
| **User-visible error** | N/A at planning stage; bad migration could cause data loss |
| **Known-good evidence** | Pre-migration inspection: **zero document rows**, four users, `documenttest@example.com` at id 4 *(BUILD_LOG)* |
| **Initial hypotheses** | Use `MIN(users.id)` backfill; delete unresolved rows |
| **Diagnostic steps** | Inspect live DB counts; enumerate users; review rejected strategy |
| **Root cause** | `MIN(user_id)` could assign documents to wrong account when multiple users exist |
| **Corrective action** | Rewritten migration `c4a8f2e19061`: nullable add → conditional backfill to `documenttest@example.com` only if rows exist → abort if unresolved → NOT NULL + FK |
| **Verification** | `alembic upgrade head` success; `alembic current` at `c4a8f2e19061` *(BUILD_LOG)* |
| **Incorrect assumptions avoided** | Silent `DELETE FROM documents WHERE user_id IS NULL` |
| **Principle** | **Data migrations must fail loudly rather than assign/delete ambiguously** |
| **Recognition pattern** | Backfill using aggregate without ownership semantics |
| **Engineering Explanation** | When adding ownership columns, decide explicitly who owns legacy rows — never guess with MIN(id). |
| **Related** | `alembic/versions/c4a8f2e19061_add_user_id_to_documents.py`; [`BUILD_LOG.md`](BUILD_LOG.md) § Migration History; [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) § Phase 3 |
| **Diagnostic Questions** | How many legacy rows exist? Who should own them? What happens if the designated user is missing? |

---

### Case 9 — Document ownership isolation (cross-user access)

| Field | Detail |
|-------|--------|
| **Phase / date** | Ownership — July 18–20, 2026 |
| **System layer** | Service queries + router |
| **Initial symptom** | Any authenticated user could access any document *(pre-fix inspection)* |
| **User-visible error** | Should be **404** `"Document not found."` for cross-user access *(not 403)* |
| **Known-good evidence** | Alice and ownerb manual tests *(BUILD_LOG)*; automated tests in upload integration |
| **Initial hypotheses** | Missing JWT; router bug |
| **Diagnostic steps** | Two users; user B requests user A document id; verify response code and message |
| **Root cause** | Queries filtered by `document_id` only — no `user_id` scope before migration |
| **Corrective action** | `get_document_for_user`, `get_documents_for_user`; upload stores `current_user.id` |
| **Verification** | Alice receives 404 on document ID 1 owned by another user *(BUILD_LOG)* |
| **Incorrect assumptions avoided** | Returning 403 and leaking resource existence |
| **Principle** | **Scope all resource reads through owner id; use 404 for unauthorized access** |
| **Recognition pattern** | IDOR — changing id returns another user's data |
| **Engineering Explanation** | Every document query must include the authenticated user's id in the WHERE clause. |
| **Related** | `document_service.py`; `test_upload_chunk_integration.py::test_cross_user_access_returns_404`; commit `ae1ab11` area |
| **Diagnostic Questions** | Does this query filter by `user_id`? What status code do we return for other users' ids? |

---

### Case 10 — SQLite foreign keys verified via wrong connection path (Phase 1)

| Field | Detail |
|-------|--------|
| **Phase / date** | Chunking Phase 1 — July 21, 2026 |
| **System layer** | Database / test diagnostics |
| **Initial symptom** | `PRAGMA foreign_keys` returns 0 in manual inspection |
| **User-visible error** | False alarm — cascades appear broken |
| **Known-good evidence** | Application engine enables FKs via connect listener in `database.py` *(ENGINEERING_LESSONS.md)* |
| **Initial hypotheses** | FK enforcement disabled project-wide |
| **Diagnostic steps** | Run PRAGMA through SQLAlchemy session/engine used by app; compare to raw `sqlite3.connect` |
| **Root cause** | FK pragma is **per connection**; raw sqlite3 bypasses listener |
| **Corrective action** | Document correct verification path; tests use engine with listener |
| **Verification** | Cascade delete tests in `test_chunk_embedding_model.py` pass |
| **Incorrect assumptions avoided** | Adding redundant application-level FK logic |
| **Principle** | **Validate DB behavior through the production connection path** |
| **Recognition pattern** | PRAGMA differs between CLI and app |
| **Engineering Explanation** | SQLite foreign keys must be enabled on each connection — the app does that in one place. |
| **Related** | [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) § Phase 1 — Document Chunk Schema; `app/database/database.py` |
| **Diagnostic Questions** | How does the app open DB connections? Are you testing through the same path? |

---

## Cases 11–20 — Phase 4D indexing, concurrency, compensation

### Case 11 — Indexing / deletion race and shared document lock

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D — July 22, 2026 |
| **System layer** | Concurrency — `IndexingService` + delete router |
| **Initial symptom** | Concurrent index during delete could recreate vectors after purge |
| **User-visible error** | No single HTTP code — consistency bug |
| **Known-good evidence** | Pre-fix: purge removed vectors and delete removed DB rows independently, but concurrent index could recreate vectors between steps. Post-fix: race proven closed by `test_index_cannot_run_between_purge_and_db_delete` *(repository-proven)* |
| **Initial hypotheses** | FAISS corruption; duplicate indexing |
| **Diagnostic steps** | Threaded delete holding purge window; attempt index on same document id |
| **Root cause** | Delete did not hold document lock through purge + DB delete; index could run between steps |
| **Corrective action** | `document_lock()` on delete path; hold through purge and `delete_document()` |
| **Verification** | `test_index_cannot_run_between_purge_and_db_delete`; `test_delete_flow_acquires_document_lock` |
| **Incorrect assumptions avoided** | Relying on purge alone without serializing index |
| **Principle** | **Purge-then-mutate sequences need the same lock as the mutating operation** |
| **Recognition pattern** | Ghost vectors after delete; intermittent duplicate index state |
| **Engineering Explanation** | Delete and index for the same document must not run concurrently — use one lock. |
| **Related** | `indexing/service.py`; `test_indexing_compensation_gaps.py`; [`BUILD_LOG.md`](BUILD_LOG.md) Phase 4D defects; [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) § Phase 4D |
| **Diagnostic Questions** | What happens if index runs between purge and DB delete? Who acquires the lock today? |

---

### Case 12 — RLock nested acquisition analysis

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D — July 22, 2026 |
| **System layer** | In-process locking |
| **Initial symptom** | Risk of deadlock if purge re-enters lock during index/delete |
| **User-visible error** | Potential hang (theoretical before RLock) |
| **Known-good evidence** | Index holds lock; purge called from within index compensation |
| **Initial hypotheses** | Need separate locks for purge vs index |
| **Diagnostic steps** | Call `purge_document_index()` while already holding `document_lock` on same thread |
| **Root cause** | Same thread re-enters purge during index failure compensation |
| **Corrective action** | `threading.RLock` per document id; `_purge_document_index_unlocked` for inner path |
| **Verification** | `test_purge_reacquires_document_lock_without_deadlock` |
| **Incorrect assumptions avoided** | Non-reentrant Lock causing self-deadlock |
| **Principle** | **Use reentrant locks when nested service calls share a critical section** |
| **Recognition pattern** | Compensation calls same service method that already holds lock |
| **Engineering Explanation** | RLock lets the same thread acquire twice — needed for index → purge → purge compensation. |
| **Related** | `indexing/service.py` `document_lock`, `purge_document_index` |
| **Diagnostic Questions** | Can this code path call purge while already inside index? Is the lock reentrant? |

---

### Case 13 — Locked public purge versus internal unlocked purge

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D — July 22, 2026 |
| **System layer** | Service API design |
| **Initial symptom** | Need purge from delete (locked) and from compensation (already inside lock) |
| **User-visible error** | N/A — design clarity |
| **Known-good evidence** | Public `purge_document_index()` acquires lock; delete uses outer lock |
| **Initial hypotheses** | Single purge implementation always self-locks |
| **Diagnostic steps** | Trace call graph: delete → purge; index fail → `_mark_failed` → purge |
| **Root cause** | Two call contexts — external (needs lock) vs internal (lock already held) |
| **Corrective action** | Public method wraps lock; `_purge_document_index_unlocked` performs work |
| **Verification** | Reentrant tests pass; delete purge tests pass |
| **Incorrect assumptions avoided** | Duplicating purge logic in two methods |
| **Principle** | **Split public synchronized entry from internal worker for nested calls** |
| **Recognition pattern** | Double-lock attempt or skipped lock in compensation |
| **Engineering Explanation** | Outer API takes the lock; inner helper assumes caller synchronized. |
| **Related** | `indexing/service.py` lines 112–151 |
| **Diagnostic Questions** | Who is responsible for acquiring the lock — caller or callee? |

---

### Case 14 — Multi-system compensation across SQLite and FAISS

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D — July 22, 2026 |
| **System layer** | Orchestration / saga |
| **Initial symptom** | Partial index leaves metadata and vectors inconsistent |
| **User-visible error** | `indexing_status=failed` with possible ghost vectors |
| **Known-good evidence** | Approved sequence: FAISS `save()` before `indexed` DB commit *(ARCHITECTURE.md)* |
| **Initial hypotheses** | Single transaction across stores |
| **Diagnostic steps** | Inject failures after add, after save, after metadata commit; inspect both stores |
| **Root cause** | No distributed transaction between SQLite and FAISS file |
| **Corrective action** | Ordered steps + idempotent `purge_document_index()` on failure; status gate for retrieval |
| **Verification** | 51 Phase 4D tests including compensation gap file |
| **Incorrect assumptions avoided** | Two-phase commit; marking indexed before FAISS save |
| **Principle** | **Cross-store workflows are sagas — order commits and compensate** |
| **Recognition pattern** | Metadata says ready but index file missing, or vice versa |
| **Engineering Explanation** | Save vectors to disk before telling the DB indexing succeeded; on failure, purge best-effort. |
| **Related** | [`ARCHITECTURE.md`](ARCHITECTURE.md) Phase 4D consistency; [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) § Phase 4D — Document Indexing Orchestration |
| **Diagnostic Questions** | Which store is source of truth for "ready"? What happens if step 7 fails after step 6 succeeded? |

---

### Case 15 — `_mark_failed()` rollback correction

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D verification — July 22, 2026 |
| **System layer** | SQLAlchemy session |
| **Initial symptom** | Failed-status commit failure leaves session dirty |
| **User-visible error** | Document stuck `processing`; subsequent ops fail |
| **Known-good evidence** | `_mark_failed` updates status then commits |
| **Initial hypotheses** | Compensation incomplete |
| **Diagnostic steps** | Inject exception on failed-status commit; inspect session state |
| **Root cause** | Missing `db.rollback()` on commit failure in `_mark_failed` |
| **Corrective action** | `try/except` around commit with `db.rollback(); raise` |
| **Verification** | `test_failed_status_commit_failure_leaves_processing_until_stale` |
| **Incorrect assumptions avoided** | Assuming SQLAlchemy auto-recovers session after commit error |
| **Principle** | **Always rollback session on commit failure before propagating** |
| **Recognition pattern** | Pending objects after failed commit; weird ORM state in tests |
| **Engineering Explanation** | If marking failed cannot commit, roll back the session so the connection is usable. |
| **Related** | `indexing/service.py` `_mark_failed`; commit `c69ecbf` |
| **Diagnostic Questions** | What happens to the SQLAlchemy session if commit raises? Do you rollback? |

---

### Case 16 — Preservation of primary and compensation errors

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D verification — July 22, 2026 |
| **System layer** | Error reporting |
| **Initial symptom** | Compensation purge failures swallowed — primary error only visible |
| **User-visible error** | `indexing_error` missing compensation context |
| **Known-good evidence** | `_mark_failed` calls purge in try/except |
| **Initial hypotheses** | Purge always succeeds |
| **Diagnostic steps** | Force purge remove/save failure during compensation; read `indexing_error` |
| **Root cause** | Exception caught without logging or appending context |
| **Corrective action** | Log warning with `exc_info`; append `(compensation purge failed: ...)` truncated to max length |
| **Verification** | `test_compensation_purge_remove_failure_preserves_primary_error_context` |
| **Incorrect assumptions avoided** | Replacing primary error with compensation error |
| **Principle** | **Preserve primary failure; add secondary context — do not overwrite** |
| **Recognition pattern** | Silent compensation failures in saga steps |
| **Engineering Explanation** | Users need the root error; ops need to know compensation also failed. |
| **Related** | `indexing/service.py` `_mark_failed`; gap tests |
| **Diagnostic Questions** | If cleanup fails, does the client still see the original error? Is it logged? |

---

### Case 17 — Orphaned stored-file cleanup behavior

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D verification — July 22, 2026 |
| **System layer** | Router / filesystem |
| **Initial symptom** | Stored file delete failure caused HTTP 500 |
| **User-visible error** | **500** despite DB and vectors already purged |
| **Known-good evidence** | Delete succeeds at DB layer; file delete is last step |
| **Initial hypotheses** | Must fail delete if file missing |
| **Diagnostic steps** | Mock `delete_stored_file` to raise; observe HTTP status and logs |
| **Root cause** | Unhandled file deletion exception bubbled to 500 |
| **Corrective action** | Catch, `logger.warning`, return **200** — orphaned file acceptable v1 |
| **Verification** | `test_stored_file_deletion_failure_returns_success_and_logs` |
| **Incorrect assumptions avoided** | Rolling back DB delete because file delete failed |
| **Principle** | **Best-effort cleanup after authoritative state removal** |
| **Recognition pattern** | 500 on last step of multi-step delete |
| **Engineering Explanation** | Once DB and index are clean, a leftover file is less harmful than a false failure. |
| **Related** | `routers/documents.py` delete endpoint; BUILD_LOG Phase 4D defect 4 |
| **Diagnostic Questions** | Which step is source of truth for "document gone"? Should file failure fail the API? |

---

### Case 18 — Partial vector-add failure handling

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D verification — July 22, 2026 |
| **System layer** | Vector store / indexing |
| **Initial symptom** | Failure mid-batch leaves some vectors in FAISS |
| **User-visible error** | `indexing_status=failed` |
| **Known-good evidence** | `vector_store.add()` atomic per call in FaissVectorStore |
| **Initial hypotheses** | Partial add silently continues |
| **Diagnostic steps** | Inject failure after first chunk add; inspect FAISS count and metadata |
| **Root cause** | Orchestration must treat add failure as full failure and compensate |
| **Corrective action** | `_mark_failed` + purge; retry path |
| **Verification** | `test_partial_vector_add_failure_marks_failed`; `test_partial_vector_add_compensation_and_retry` |
| **Incorrect assumptions avoided** | Committing metadata for partial add |
| **Principle** | **Treat vector index mutation as all-or-nothing at orchestration boundary** |
| **Recognition pattern** | count > 0 in FAISS but metadata rows missing |
| **Engineering Explanation** | If adding vectors fails partway, mark failed and purge — don't leave a half index. |
| **Related** | `test_indexing_verification.py`; gap tests |
| **Diagnostic Questions** | Is add atomic? What runs on exception — compensation or leave partial state? |

---

### Case 19 — FAISS remove / save failure handling

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D verification — July 22, 2026 |
| **System layer** | Vector store persistence |
| **Initial symptom** | Purge removes in memory but save fails — disk stale |
| **User-visible error** | Retry may reload old vectors from disk |
| **Known-good evidence** | Purge calls `save()` only if vectors removed |
| **Initial hypotheses** | Memory state always matches disk |
| **Diagnostic steps** | Force save failure on purge; reload FAISS store; compare counts |
| **Root cause** | FAISS persistence is separate step from in-memory remove |
| **Corrective action** | Log compensation failures; document v1 limitation; retry purge when healthy |
| **Verification** | `test_compensation_purge_save_failure_leaves_disk_vectors`; `test_compensation_purge_save_failure_faiss_reload` |
| **Incorrect assumptions avoided** | Assuming purge succeeded because memory count is zero |
| **Principle** | **Persisted index state requires explicit save — verify disk after mutations** |
| **Recognition pattern** | Restart reloads ghost vectors |
| **Engineering Explanation** | Removing vectors in memory isn't enough — save must succeed for disk to match. |
| **Related** | `FaissVectorStore`; gap tests; `ENGINEERING_LESSONS.md` |
| **Diagnostic Questions** | After remove, is save called? What if save fails — what does retry do? |

---

### Case 20 — Stale processing-state recovery

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D — July 22, 2026 |
| **System layer** | Indexing status / claim logic |
| **Initial symptom** | Crashed worker leaves document in `processing` forever |
| **User-visible error** | **409 Conflict** on re-index until timeout |
| **Known-good evidence** | `INDEXING_STALE_TIMEOUT_SECONDS` default 300 |
| **Initial hypotheses** | Manual DB edit required |
| **Diagnostic steps** | Set old `indexing_started_at`; attempt reclaim claim |
| **Root cause** | No heartbeat worker in v1 — timeout-based reclaim only |
| **Corrective action** | Conditional update allows stale `processing` reclaim; failed-status commit failure also leaves processing until stale *(acceptable v1)* |
| **Verification** | `test_index_document_stale_processing_reclaim`; `test_failed_status_commit_failure_leaves_processing_until_stale` |
| **Incorrect assumptions avoided** | Immediate forced reset without timeout policy |
| **Principle** | **Long-running locks need lease expiry on status fields** |
| **Recognition pattern** | Document stuck processing after crash |
| **Engineering Explanation** | If indexing_started_at is too old, another worker can reclaim the job. |
| **Related** | `indexing/service.py` `_claim_processing`; `config.py` |
| **Diagnostic Questions** | How does a client recover a stuck processing document? What timeout applies? |

---

## Cases 21–30 — Verification and engineering governance

### Case 21 — Unreliable commit-failure test hook (count-based patching)

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D verification — July 22, 2026 |
| **System layer** | Test infrastructure |
| **Initial symptom** | Failure-injection tests flaky or targeted wrong transaction |
| **User-visible error** | pytest failures on compensation scenarios |
| **Known-good evidence** | Indexing performs multiple commits (claim, metadata, failed status) |
| **Initial hypotheses** | Production bug vs test bug |
| **Diagnostic steps** | Log commit count during index; compare to hook assumptions |
| **Root cause** | Global `commit_count == N` hooks misaligned with actual commit sequence |
| **Corrective action** | Target specific boundaries (metadata commit vs failed-status commit); use flags for failed-status injection |
| **Verification** | Gap tests pass after hook refinement — `test_indexing_compensation_gaps.py`, `test_indexing_verification.py::test_final_database_commit_failure_marks_failed` *(repository-proven)* |
| **Incorrect assumptions avoided** | Changing production commit order to satisfy tests |
| **Principle** | **Failure injection must target named transaction boundaries, not commit ordinals** |
| **Recognition pattern** | Tests pass individually, fail in suite; wrong status after injection |
| **Engineering Explanation** | Don't fail "the third commit" — fail the metadata commit or the failed-status commit explicitly. |
| **Related** | `test_indexing_compensation_gaps.py`; `test_indexing_verification.py`; [`BUILD_LOG.md`](BUILD_LOG.md) Phase 4D verification |
| **Diagnostic Questions** | Which commit are you trying to fail? How many commits does the workflow actually make? |

---

### Case 22 — Multi-chunk fixture text too short

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D verification — July 22, 2026 |
| **System layer** | Test fixtures |
| **Initial symptom** | Multi-chunk partial-add tests did not create multiple chunks |
| **User-visible error** | Test assertions skipped partial-add path |
| **Known-good evidence** | Chunk size 1000 / overlap 200 *(chunking_service)* |
| **Initial hypotheses** | Partial add logic broken |
| **Diagnostic steps** | Print `len(document.chunks)` for fixture text |
| **Root cause** | Fixture text too short to produce >1 chunk |
| **Corrective action** | Lengthen text (`paragraph + ("word " * 120)` pattern used elsewhere) |
| **Verification** | Partial vector tests pass after fixture fix — `test_partial_vector_add_failure_marks_failed`, `test_partial_vector_add_compensation_and_retry` *(repository-proven)* |
| **Incorrect assumptions avoided** | Weakening assertions instead of fixing fixture |
| **Principle** | **Test fixtures must satisfy preconditions of the behavior under test** |
| **Recognition pattern** | Test name says multi-X but setup creates single X |
| **Engineering Explanation** | If you test partial chunk indexing, create a document with enough text for multiple chunks. |
| **Related** | `chunking_service.py` constants; `test_indexing_verification.py`; [`BUILD_LOG.md`](BUILD_LOG.md) Phase 4D verification |
| **Diagnostic Questions** | How many chunks does this fixture create? What is CHUNK_SIZE? |

---

### Case 23 — Phase boundary violation: implementation before architecture approval

| Field | Detail |
|-------|--------|
| **Phase / date** | July 23, 2026 |
| **System layer** | Engineering governance / milestone workflow |
| **Initial symptom** | Retrieval service packages and `/search` routes appeared in the working tree during a documentation-audit sprint |
| **User-visible error** | N/A — governance failure, not a runtime defect |
| **Known-good evidence** | Phase 4D closed at commit `c69ecbf`; [`PROJECT_STATE.md`](PROJECT_STATE.md) listed Phase 4E semantic retrieval as **not started**; [`AI_DEVELOPMENT_PROTOCOL.md`](AI_DEVELOPMENT_PROTOCOL.md) §9 requires Inspect → Design → Review → **Approve** before Implement |
| **Initial hypotheses** | Continuation after Phase 4D closeout authorized the next phase |
| **Diagnostic steps** | Compare authorized sprint scope (documentation audit only) vs uncommitted files; read `PROJECT_STATE.md` roadmap; confirm no approved Phase 4E design record in architecture docs |
| **Root cause** | **Scope authorization gap** — ambiguous continuation language was treated as permission to implement Phase 4E without passing the architecture approval gate |
| **Corrective action** | Work stopped by project owner; uncommitted Phase 4E files removed via `git restore` and targeted cleanup; repository returned to Phase 4D HEAD without committing unauthorized code |
| **Verification** | Working tree matched Phase 4D HEAD at `c69ecbf`; no retrieval router or service packages in committed tree; `PROJECT_STATE.md` Phase 4E status unchanged *(repository-proven)* |
| **Incorrect assumptions avoided** | Committing unauthorized work to preserve progress; merging a documentation sprint with feature implementation |
| **Principle** | **Milestone boundaries are explicit authorization events — continuation language does not substitute for approved design** |
| **Recognition pattern** | New modules appear during a docs-only or audit sprint while roadmap still marks the phase "not started" |
| **Engineering Explanation** | After closing Phase 4D, the project entered a documentation review sprint. Starting Phase 4E required a separate approved design — ambiguous "continue" is not architecture approval. |
| **Related** | [`AI_DEVELOPMENT_PROTOCOL.md`](AI_DEVELOPMENT_PROTOCOL.md) §9; [`PROJECT_STATE.md`](PROJECT_STATE.md) §8; [`ARCHITECTURE.md`](ARCHITECTURE.md) Phase 4E gaps |
| **Diagnostic Questions** | What phase is authorized right now? Where is the approved design? Does PROJECT_STATE match the working tree? |

---

### Case 24 — Destructive cleanup scope: `git clean -fd` beyond intended targets

| Field | Detail |
|-------|--------|
| **Phase / date** | July 23, 2026 |
| **System layer** | Git hygiene / untracked asset management |
| **Initial symptom** | After reverting unauthorized Phase 4E files, numbered workspace folders (`00-Notes/` through `11-Archive/`) were missing from disk |
| **User-visible error** | N/A — data loss risk for untracked local material |
| **Known-good evidence** | `git clean -fd` stdout listed removed paths including learning and archive directories; those paths were never tracked in Git history *(recovery assessment, July 23)* |
| **Initial hypotheses** | Cleanup removed only the Phase 4E files targeted for revert |
| **Diagnostic steps** | Read `git clean` stdout path list; compare to intended revert scope; run `git log --all -- 00-Notes/` to confirm paths were never committed |
| **Root cause** | **Command scope mismatch** — repository-wide `git clean -fd` removes every untracked file and directory, not only files associated with a specific revert |
| **Corrective action** | Document recovery assessment; adopt allowlist-only cleanup (`git clean -fd -- <path>` or explicit path deletion); migrate important notes into Git-backed docs or tracked structure |
| **Verification** | Committed project files intact at `c69ecbf`; deleted untracked folders not recoverable via Git alone *(repository-proven for commit integrity; local folders not reconstructable)* |
| **Incorrect assumptions avoided** | Assuming `git clean` respects intent rather than literal untracked scope; repeating repository-wide clean without inventory |
| **Principle** | **Destructive Git commands require explicit path scope and a preview of untracked inventory** |
| **Recognition pattern** | Missing local-only directories immediately after cleanup; clean output lists paths beyond intended targets |
| **Engineering Explanation** | `git restore` is scoped to tracked files. `git clean -fd` at repo root deletes all untracked content — including notes never added to Git. Important local material needs backups or tracking before any clean operation. |
| **Related** | [`AI_DEVELOPMENT_PROTOCOL.md`](AI_DEVELOPMENT_PROTOCOL.md) §8 Git Safety Rules; Case 23 (revert context); `.gitignore` policy review |
| **Diagnostic Questions** | What exactly will clean remove? Are important files untracked? Is there a backup? Did you preview with `git clean -fdn`? |

---

### Case 25 — Application startup versus functional validation

| Field | Detail |
|-------|--------|
| **Phase / date** | Ownership migration — July 2026; recurring |
| **System layer** | Verification methodology |
| **Initial symptom** | Team reports "server works" but endpoints fail |
| **User-visible error** | 401/500 on first real request |
| **Known-good evidence** | Uvicorn starts without import errors *(BUILD_LOG post-migration)* |
| **Initial hypotheses** | Complete system healthy |
| **Diagnostic steps** | Hit authenticated endpoint with token; run one upload/delete cycle |
| **Root cause** | Startup proves imports — not auth, migrations, or business flows |
| **Corrective action** | Functional checklist: register → login → authorized request → domain operation |
| **Verification** | Ownership tests (Alice/ownerb); manual Swagger flows documented |
| **Incorrect assumptions avoided** | Closing milestone after `uvicorn` boot only |
| **Principle** | **Smoke boot ≠ end-to-end validation** |
| **Recognition pattern** | "It starts" used as done criteria |
| **Engineering Explanation** | Starting the server only shows Python imports work — test a real authenticated flow. |
| **Related** | `BUILD_LOG.md` § Uvicorn Restart After Migration |
| **Diagnostic Questions** | What is the smallest authenticated operation that proves this milestone? Did you run it? |

---

### Case 26 — Phase 4D upload failure caused by outdated Alembic schema

**Owner-confirmed manual investigation** — July 2026 (post Phase 4D commit deployment to local DB).

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D manual validation |
| **System layer** | Database migration + upload/indexing router |
| **Initial symptom** | DOCX upload returns 500 after successful auth |
| **User-visible error** | HTTP **500** — `"The document could not be saved."` |
| **Known-good evidence** | Registration **201**; login **200** + bearer token |
| **Initial hypotheses** | Extraction failure; ownership bug; chunking error; indexing failure |
| **Diagnostic steps** | 1) Confirm auth works. 2) Check `alembic current` vs head `a7c2d9e48103`. 3) Upgrade if at `f3a1b8c45201`. 4) Retry upload. |
| **Root cause** | Database at revision **`f3a1b8c45201`** while code expects **`a7c2d9e48103`** indexing columns |
| **Corrective action** | `python -m alembic upgrade head` from `02-Projects/backend` |
| **Verification** | **Schema fix:** `alembic upgrade head`; `alembic current` at `a7c2d9e48103`. **Functional API:** upload **200** with `indexing_status=indexed`, `chunk_count=2`, `vectors_indexed=2`; list/download **200**; delete **200**; list `[]`; reindex/download on deleted id **404** *(owner-confirmed)*. **Regression suite:** pytest **120 passed, 25 skipped, 3 warnings, 0 failed**, ~51.88s *(owner-confirmed)* |
| **Incorrect assumptions avoided** | Debugging extraction/parser before checking schema revision |
| **Principle** | **Verify migrations before runtime testing of schema-dependent features** |
| **Recognition pattern** | 500 on persist after pulling new code with old local DB |
| **Engineering Explanation** | New columns like `indexing_status` require migration — code ahead of DB schema causes save failures. |
| **Related** | Migration `a7c2d9e48103`; `routers/documents.py`; [`BUILD_LOG.md`](BUILD_LOG.md) Phase 4D manual validation |
| **Diagnostic Questions** | What is `alembic current`? Does it match the code you checked out? |

---

### Case 27 — Post-deletion verification through list / index / download

| Field | Detail |
|-------|--------|
| **Phase / date** | Document management July 2026; Phase 4D manual validation |
| **System layer** | API verification |
| **Initial symptom** | Uncertainty whether delete fully removed resource |
| **User-visible error** | GET/index/download on deleted id returns **404** |
| **Known-good evidence** | Delete returns **200** |
| **Initial hypotheses** | Soft delete |
| **Diagnostic steps** | GET list (empty); GET by id 404; download 404; POST index 404 |
| **Root cause** | N/A — **correct verification procedure** |
| **Corrective action** | Standard post-delete checklist documented |
| **Verification** | BUILD_LOG deletion testing; manual Phase 4D reindex/download 404 after delete |
| **Incorrect assumptions avoided** | Trusting 200 on delete without follow-up GET |
| **Principle** | **Verify postconditions — absence, not just success response** |
| **Recognition pattern** | Delete returns OK but resource still listable |
| **Engineering Explanation** | After delete, prove the document is gone from list, index, and download paths. |
| **Related** | [`BUILD_LOG.md`](BUILD_LOG.md) § Document Deletion Testing; [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) § Phase 3 |
| **Diagnostic Questions** | What requests prove the resource no longer exists? |

---

### Case 28 — Interrupted pytest run (environment / mid-verification)

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D verification — July 22–23, 2026 |
| **System layer** | Test execution environment |
| **Initial symptom** | Full suite not completed in some sessions |
| **User-visible error** | `No module named pytest` on system Python; mid-suite failures before fixes *(partially reconstructable from BUILD_LOG and PROJECT_STATE)* |
| **Known-good evidence** | Final approved result: **120 passed, 25 skipped** *(owner-confirmed and BUILD_LOG-proven)* |
| **Initial hypotheses** | Code regression |
| **Diagnostic steps** | Confirm venv active; use `.venv\Scripts\python -m pytest`; complete full suite |
| **Root cause** | Wrong interpreter and/or iterative fix cycle — **exact interruption timestamp not fully reconstructable from committed evidence** |
| **Corrective action** | Always run pytest from project venv; complete suite before claiming pass |
| **Verification** | Owner manual run: 120 passed, 25 skipped, 3 warnings, ~51.88s |
| **Incorrect assumptions avoided** | Reporting pass from partial subset during active debugging |
| **Principle** | **Never call a partial test run a pass** |
| **Recognition pattern** | Partial suite counts reported while fixes still in progress |
| **Engineering Explanation** | Run the full default suite from the venv before signing off. |
| **Related** | [`PROJECT_STATE.md`](PROJECT_STATE.md); [`BUILD_LOG.md`](BUILD_LOG.md) Phase 4D verification |
| **Diagnostic Questions** | Which Python ran pytest? Did the full suite finish with exit code 0? |

---

### Case 29 — Final result: 120 passed, 25 skipped, 3 warnings, 0 failed

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4D approval — July 22, 2026; confirmed manual re-run |
| **System layer** | Test suite |
| **Initial symptom** | Need sign-off evidence |
| **User-visible error** | N/A |
| **Known-good evidence** | Default suite excludes opt-in integration unless env gates set |
| **Initial hypotheses** | Skips indicate failures |
| **Diagnostic steps** | Distinguish skipped (integration gates) vs failed; read warning sources |
| **Root cause** | N/A — baseline snapshot |
| **Corrective action** | Record as Phase 4D verification baseline |
| **Verification** | `pytest tests/` → 120 passed, 25 skipped, 3 warnings; all gates → 145 passed |
| **Incorrect assumptions avoided** | Treating skipped integration tests as defects |
| **Principle** | **Report passed / skipped / failed / warnings separately** |
| **Recognition pattern** | "120 tests pass" without mentioning skips |
| **Engineering Explanation** | Skipped tests are opt-in integration — failures are zero; warnings are documented debt. |
| **Related** | [`BUILD_LOG.md`](BUILD_LOG.md) Phase 4D; [`PROJECT_STATE.md`](PROJECT_STATE.md) |
| **Diagnostic Questions** | How many skipped? Why? Any failures or only warnings? |

---

### Case 30 — Pydantic class-based Config deprecation as technical debt

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 3+ — pre-existing |
| **System layer** | Schemas (Pydantic v2 migration) |
| **Initial symptom** | pytest shows 3 warnings every suite |
| **User-visible error** | None — warnings only |
| **Known-good evidence** | Documented since Phase 3: `class Config` in schemas *(BUILD_LOG)* |
| **Initial hypotheses** | New regression |
| **Diagnostic steps** | Run pytest with warnings; locate `schemas/document.py`, `schemas/user.py` |
| **Root cause** | Pydantic v2 prefers `model_config = ConfigDict(...)` over nested `Config` class |
| **Corrective action** | **Deferred** — tracked as technical debt, not a Phase 4D blocker |
| **Verification** | 0 failures with warnings present across 120+ test runs |
| **Incorrect assumptions avoided** | Blocking release for deprecation warnings unrelated to behavior |
| **Principle** | **Separate correctness blockers from deprecation hygiene** |
| **Recognition pattern** | Stable 3 warnings on every run |
| **Engineering Explanation** | Warnings remind us to migrate Pydantic config style — they don't mean tests failed. |
| **Related** | `schemas/document.py`; [`BUILD_LOG.md`](BUILD_LOG.md) Phase 3 warnings note; [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) § Cross-Cutting Principles |
| **Diagnostic Questions** | Is this a failure or a warning? Does behavior match expectations? |

---

## Appendix — Earlier-phase investigations (Cases A–F)

These cases predate Phase 4D but remain relevant for regression awareness, design review, and governance discipline. They use the same investigation template as numbered cases. Letter labels avoid collision with the main Case 1–30 sequence.

### Case A — FAISS same-batch duplicate chunk_id silent overwrite (Phase 4C)

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4C — July 2026 |
| **System layer** | Vector store / FAISS |
| **Initial symptom** | Duplicate chunk IDs within one batch could overwrite silently |
| **User-visible error** | Inconsistent search results; duplicate vectors not rejected |
| **Known-good evidence** | Single-ID duplicates already rejected via `_known_ids` *(repository-proven)* |
| **Initial hypotheses** | FAISS rejects duplicates automatically |
| **Diagnostic steps** | Add two items with same `chunk_id` in one `add()` call; inspect index count |
| **Root cause** | Duplicate IDs in one `add()` batch bypassed `_known_ids` check until batch committed |
| **Corrective action** | `seen_in_batch` set; reject before FAISS mutation |
| **Verification** | `test_duplicate_chunk_id_in_same_batch_raises` |
| **Incorrect assumptions avoided** | Relying on FAISS ID map alone without pre-batch validation |
| **Principle** | **Validate in-batch duplicates before mutating external indexes** |
| **Recognition pattern** | Same chunk_id twice in one add call |
| **Engineering Explanation** | Known-ID set tracks committed IDs; a second set tracks the current batch. |
| **Related** | [`BUILD_LOG.md`](BUILD_LOG.md) Phase 4C Defect 1; commit `c56ac1f`; [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) § Phase 4C |
| **Diagnostic Questions** | Can one API call include duplicate IDs? When is each ID checked? |

---

### Case B — FAISS loaded inner index structure not validated (Phase 4C)

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4C — July 2026 |
| **System layer** | Vector store persistence |
| **Initial symptom** | Valid saved indexes failed type validation on load |
| **User-visible error** | `VectorStoreLoadError` on startup or test reload |
| **Known-good evidence** | New indexes created as `IndexIDMap2(IndexFlatIP)` work correctly |
| **Initial hypotheses** | Corrupt index file |
| **Diagnostic steps** | Load saved index; inspect SWIG proxy type vs inner flat index |
| **Root cause** | SWIG proxy type check failed for valid indexes — needed `faiss.downcast_index()` |
| **Corrective action** | After load, `downcast_index()` must yield `IndexFlatIP` |
| **Verification** | `test_loaded_index_validates_id_map_flat_ip_structure` |
| **Incorrect assumptions avoided** | Rejecting all persisted indexes as corrupt |
| **Principle** | **Validate semantic structure of loaded artifacts, not wrapper types alone** |
| **Recognition pattern** | Load fails after save succeeded; type check on outer object |
| **Engineering Explanation** | FAISS wraps indexes in SWIG proxies — downcast to verify inner structure. |
| **Related** | [`BUILD_LOG.md`](BUILD_LOG.md) Phase 4C Defect 2; [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) § Phase 4C |
| **Diagnostic Questions** | What index type do we expect on disk? How do you verify after load? |

---

### Case C — Embedding factory double model load (Phase 4B)

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 4B — July 2026 |
| **System layer** | Service factory / memory |
| **Initial symptom** | Risk of loading embedding model twice in one process |
| **User-visible error** | Slow startup; elevated memory *(potential, pre-fix)* |
| **Known-good evidence** | Separate factory caches for provider and service existed |
| **Initial hypotheses** | Singleton always shares one model instance |
| **Diagnostic steps** | Trace `get_embedding_service()` vs `get_embedding_provider()` cache paths |
| **Root cause** | Separate cached factories could each trigger model load |
| **Corrective action** | Default service creation reuses `get_embedding_provider()` |
| **Verification** | Factory tests; integration tests with single load expectation |
| **Incorrect assumptions avoided** | Creating parallel singleton caches for related resources |
| **Principle** | **One expensive resource — one cache owner; dependents reuse it** |
| **Recognition pattern** | Two factories for same heavyweight object |
| **Engineering Explanation** | The service factory should ask the provider factory for the model, not load its own. |
| **Related** | [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md) § Phase 4B — Embedding Service; [`BUILD_LOG.md`](BUILD_LOG.md) Phase 4B |
| **Diagnostic Questions** | How many times can this model load per process? Who owns the cache? |

---

### Case D — Alembic empty-database bootstrap debt

| Field | Detail |
|-------|--------|
| **Phase / date** | Pre-Phase 4 — documented debt |
| **System layer** | Database migration chain |
| **Initial symptom** | Fresh database cannot migrate from scratch |
| **User-visible error** | Alembic upgrade fails on empty DB |
| **Known-good evidence** | Existing dev DBs upgrade incrementally *(repository-proven)* |
| **Initial hypotheses** | Missing initial migration |
| **Diagnostic steps** | Create empty DB; run `alembic upgrade head`; read failure revision |
| **Root cause** | Revision `bdc259e18150` assumes existing `users` table |
| **Corrective action** | **Deferred** — documented in PROJECT_STATE; dev uses existing DB |
| **Verification** | Debt recorded; incremental upgrades on populated DB succeed |
| **Incorrect assumptions avoided** | Claiming greenfield bootstrap works without testing |
| **Principle** | **Migration chains must be tested on empty DB, not only incremental upgrade** |
| **Recognition pattern** | First migration references tables not created earlier in chain |
| **Engineering Explanation** | We track empty-DB bootstrap as known debt — production will need a fixed baseline. |
| **Related** | [`PROJECT_STATE.md`](PROJECT_STATE.md) § Alembic Migration Chain; [`BUILD_LOG.md`](BUILD_LOG.md) migration history |
| **Diagnostic Questions** | Can a new developer run migrations on an empty database today? What breaks? |

---

### Case E — Phase 2 verification traceability gap

| Field | Detail |
|-------|--------|
| **Phase / date** | Phase 2 — July 2026 |
| **System layer** | Engineering governance / test evidence |
| **Initial symptom** | BUILD_LOG recorded 13 passed tests; raw pytest stdout not preserved in session artifacts |
| **User-visible error** | N/A — traceability gap, not a runtime defect |
| **Known-good evidence** | Phase 2 tests exist in repository; BUILD_LOG documents intended count *(repository-proven)* |
| **Initial hypotheses** | Tests did not run |
| **Diagnostic steps** | Re-run Phase 2 tests from venv; compare to BUILD_LOG claim; review session record completeness |
| **Root cause** | **Evidence preservation gap** — verification outcome logged without durable stdout capture |
| **Corrective action** | Later phases record full pytest summaries in BUILD_LOG and PROJECT_STATE; handbook cites repository tests as tie-breaker |
| **Verification** | Phase 2 tests pass on re-run *(repository-proven)*; BUILD_LOG traceability note documents discrepancy |
| **Incorrect assumptions avoided** | Treating missing stdout as proof tests failed |
| **Principle** | **Verification claims require reproducible evidence — log full test output for milestones** |
| **Recognition pattern** | Round test counts in docs without command output or commit reference |
| **Engineering Explanation** | We distinguish code defects from traceability gaps — the tests exist and pass; the session log was incomplete. |
| **Related** | [`BUILD_LOG.md`](BUILD_LOG.md) § Traceability / Process Discrepancy — July 22 Documentation Audit |
| **Diagnostic Questions** | Can you reproduce the claimed test result today? Where is the stdout? |

---

### Case F — Dependency manifest verification failure (requirements.txt)

| Field | Detail |
|-------|--------|
| **Phase / date** | Foundation — July 18, 2026 |
| **System layer** | Dependency management / verification discipline |
| **Initial symptom** | Session reported `requirements.txt` missing during dependency audit |
| **User-visible error** | Incorrect status report — file existed at `02-Projects/backend/requirements.txt` |
| **Known-good evidence** | File present in repository; contents were empty at time of inspection *(repository-proven)* |
| **Initial hypotheses** | File never created |
| **Diagnostic steps** | Direct read of path; shell `Test-Path` / `ls`; distinguish missing vs empty |
| **Root cause** | **Verification method gap** — reliance on search/glob without direct file read and shell confirmation |
| **Corrective action** | Always verify dependency manifests with direct read; treat empty and missing as different failure modes; pin versions after verification per BUILD_LOG |
| **Verification** | Subsequent sessions read file directly; dependency pins added after package verification |
| **Incorrect assumptions avoided** | Installing packages without recording pins because file was assumed absent |
| **Principle** | **Dependency audits require direct artifact inspection — empty and missing are different failure modes** |
| **Recognition pattern** | "File not found" reports that contradict repository tree |
| **Engineering Explanation** | Before claiming a requirements file is missing, read it directly. An empty file is a different problem than an absent one. |
| **Related** | [`BUILD_LOG.md`](BUILD_LOG.md) dependency sections; [`AI_DEVELOPMENT_PROTOCOL.md`](AI_DEVELOPMENT_PROTOCOL.md) §7 Phase 1 Inspect |
| **Diagnostic Questions** | Did you read the file directly? Is it missing or empty? Where are pins recorded? |

---

## Debugging decision framework

### HTTP status quick reference

| Status | First checks | Common project causes |
|--------|--------------|----------------------|
| **400** | Request body/query | Duplicate email registration |
| **401** | Authorization header | Missing/expired JWT; Swagger not re-authorized after reload |
| **403** | *(Rare in v1)* | Project uses **404** for cross-user document access instead |
| **404** | Resource id + ownership scope | Wrong id; other user's document; deleted document |
| **409** | Concurrent operation | Active indexing (`IndexingConflictError`) |
| **422** | Validation / extraction | Empty embedding input; unsupported file type; extraction errors |
| **500** | Server logs / traceback | Unhandled DB errors; schema mismatch (**Case 26**); unmapped service failures |

### Application startup failures

1. Confirm workspace root and `02-Projects/backend` cwd  
2. Activate `.venv` — prove `import fastapi`  
3. Check import errors in traceback (missing package)  
4. Verify `.env` exists and required settings present  
5. **Do not** mark milestone complete until one authenticated endpoint succeeds  

### Environment / dependency failures

1. Identify active Python executable  
2. Compare to `.venv` path used in BUILD_LOG commands  
3. Check `requirements.txt` pins vs installed packages  
4. Integration tests: confirm env gates (`RUN_FAISS_INTEGRATION=1`, etc.)  

### Database migration mismatches

1. `alembic current` vs latest revision in `alembic/versions/`  
2. Compare ORM model columns to DB schema (`PRAGMA table_info`)  
3. Apply `alembic upgrade head` from backend directory  
4. Restart Uvicorn after schema change  
5. See **Case 26** for upload 500 pattern after schema drift  

### Filesystem failures

1. Confirm upload directory exists and matches `file_handler`  
2. Verify file on disk after upload  
3. On delete: distinguish DB purge success vs file delete failure (**Case 17**)  

### Transaction / session failures

1. Check whether commit failure was followed by rollback  
2. Use fresh session to verify durable state vs identity map  
3. Count commits when writing failure-injection tests (**Case 21**)  

### Concurrency races

1. Identify shared resource (document id)  
2. Map lock acquisition order (index vs delete vs purge)  
3. Reproduce with threaded tests  
4. Prefer per-resource `RLock` over global lock  

### Multi-storage consistency (SQLite + FAISS)

1. Determine source of truth for "ready" (`indexing_status='indexed'`)  
2. Check order: FAISS save before indexed commit  
3. On failure inspect both stores  
4. Test compensation purge paths  

### Test failure triage (implementation vs test defect)

| Signal | Likely test defect | Likely implementation defect |
|--------|-------------------|------------------------------|
| Single test fails after hook change | Commit injection target wrong | — |
| Fixture produces 0 chunks for multi-chunk test | Text too short (**Case 22**) | — |
| New failure across many tests | Environment/import | Broad regression |
| Failure only in integration gate | Missing env flag / faiss | Real integration bug |
| Same-session assertion wrong | ORM cache | — |

---

## Layer-tracing maps

### Authentication

```text
POST /auth/register | /auth/login
  → router (auth.py)
  → password hash / verify (security.py)
  → user query (SQLAlchemy)
  → JWT encode (python-jose + settings)
  → 201 / 200 + access_token
```

**Failure hotspots:** duplicate email (Case 4); missing credentials (401).

### Upload and indexing

```text
POST /documents/upload
  → get_current_user (JWT)
  → save_uploaded_file (file_handler → disk)
  → extract_text (text_extraction_service)
  → create_document_with_chunks (document_service → single DB commit)
  → IndexingService.index_document
       → document RLock (non-blocking)
       → claim processing (optimistic DB update)
       → optional purge
       → embed_texts (EmbeddingService)
       → vector_store.add + save (FAISS)
       → insert chunk_embeddings + indexing_status=indexed (DB commit)
  → 200 + DocumentResponse + indexing fields
```

**Failure hotspots:** schema mismatch (**Case 26**); extraction 422; indexing soft-fail 200 with retry; lock 409.

### Deletion

```text
DELETE /documents/{id}
  → get_current_user
  → get_document_for_user (404 if not owned)
  → document_lock (blocking, holds through purge + DB delete)
  → purge_document_index (FAISS remove + save, chunk_embeddings delete)
  → delete_document (cascade chunks)
  → delete_stored_file (best effort, log warning)
  → 200
```

**Failure hotspots:** purge failure 500; index/delete race (Case 11); orphaned file (Case 17).

### Semantic search (Phase 4E — not implemented at HEAD)

Not present in committed codebase. Future layer: embed query → FAISS search → ownership post-filter → hydrate chunks. See `ARCHITECTURE.md` gaps table.

---

## Permanent safety rules

1. **Preview before destructive commands** — especially `git clean`, `git reset`, `git push --force`.  
2. **Never use repository-wide `git clean -fd` without an explicit path allowlist** — Case 24.  
3. **Never keep important knowledge only in untracked directories** — Git-backed docs or tracked placeholders.  
4. **Verify `alembic current` before runtime testing** after pulling code — Case 26.  
5. **Preserve full error context** — primary + compensation (Case 16).  
6. **Do not begin a new phase without architecture approval** — Case 23.  
7. **Never call a partial test run a pass** — Case 28.  
8. **Report passed / skipped / failed / warnings separately** — Case 29.  
9. **Re-authorize Swagger after Uvicorn reload** — Case 6.  
10. **Run Alembic and Uvicorn from `02-Projects/backend`** — Case 3.  
11. **Separate startup smoke from functional validation** — Case 25.  

---

## Handbook accuracy audit

| Claim category | Validation method | Result |
|----------------|-------------------|--------|
| Phase 4D defects (4 items) | `BUILD_LOG.md`, `indexing/service.py`, tests | Supported |
| Manual Case 26 sequence | Owner-provided evidence in sprint prompt | Supported as owner-confirmed |
| Numbered folder deletion | Recovery assessment + `git clean` output | Supported — Case 24 |
| Phase 4E boundary violation | `PROJECT_STATE.md`, HEAD at `c69ecbf`, Case 23 | Supported |
| Interrupted pytest exact timestamp | BUILD_LOG + PROJECT_STATE partial | **Not fully reconstructable** — labeled in Case 28 |
| Uploads directory exact wrong path | BUILD_LOG summary only | **Partially reconstructable** — symptom/resolution known, exact paths not in Git |
| July 8 numbered folder contents | Never tracked | **Not reconstructable** from Git |

Unsupported claims were omitted. Owner-reported items are labeled. Code references verified against HEAD `c69ecbf`.

---

## Document map

| Need | Read |
|------|------|
| What happened when | [`BUILD_LOG.md`](BUILD_LOG.md) |
| Why decisions were made | [`ENGINEERING_LESSONS.md`](ENGINEERING_LESSONS.md), [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Current state | [`PROJECT_STATE.md`](PROJECT_STATE.md) |
| How to investigate | **This handbook** |
| Process rules | [`AI_DEVELOPMENT_PROTOCOL.md`](AI_DEVELOPMENT_PROTOCOL.md) |

Cases in this handbook link to BUILD_LOG and ENGINEERING_LESSONS where a chronological or lesson-oriented view adds context. Start here for investigation reasoning; follow links for history and principles.

---

*Handbook version: Documentation Audit Sprint — revised from Git-backed evidence at commit `c69ecbf`.*
