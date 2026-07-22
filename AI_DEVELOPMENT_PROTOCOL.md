# AI Development Protocol

## 1. Project Identity

Project name: AI Knowledge Workspace

The AI Knowledge Workspace is a production-oriented web application that allows users to create accounts, authenticate securely, upload documents, process document content, search their knowledge base, and interact with an AI assistant that answers questions using uploaded information with citations.

This is an existing project. It must be extended from its current working state. It must not be recreated as a separate application unless the project owner explicitly authorizes a complete redesign.

---

## 2. Primary Development Objective

The immediate objective is to complete Version 1 as a functioning end-to-end application.

Version 1 is expected to support:

- User registration
- User login
- JWT authentication
- Protected API routes
- Document upload
- Document listing
- Individual document retrieval
- Document deletion
- Text extraction from supported documents
- Text chunking
- Embedding generation
- Vector storage
- Semantic retrieval
- AI question answering
- Source citations
- Conversation history
- Frontend interface
- Local and cloud deployment
- Basic security, testing, logging, and error handling

Future versions may add:

- Voice input
- Image input
- OCR
- Image generation
- Administrative tools
- Object storage
- Advanced monitoring
- Team workspaces
- Subscription and monetization features
- Larger-scale production infrastructure

---

## 3. Current Technology Stack

The current or planned technology stack includes:

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- Pydantic
- Alembic
- JWT authentication
- SQLite during initial development
- PostgreSQL for production migration

### AI and Retrieval

- Document text extraction
- Text chunking
- Embedding models
- FAISS or PostgreSQL with pgvector
- Retrieval-augmented generation
- Large language model API integration
- Citation-based responses

### Frontend

- React
- Vite
- Responsive browser interface

### Infrastructure

- Git
- GitHub
- Python virtual environment
- Docker
- Docker Compose
- Cloud deployment platform
- Object storage in a later production phase

---

## 4. Existing Project Location

The existing project root is:

C:\Projects\AI-Knowledge-Workspace

The backend is located at:

C:\Projects\AI-Knowledge-Workspace\02-Projects\backend

All development must continue inside the existing project.

No AI assistant should create a replacement project in another folder without explicit authorization.

---

## 5. Architectural Principles

The project should follow a layered architecture.

### Routers

Routers handle HTTP concerns such as:

- Request parameters
- Request bodies
- Authentication dependencies
- HTTP status codes
- Response objects

Routers should remain thin.

Business logic should not be placed directly inside routers when it can be placed inside a service.

### Services

Services contain application and business logic.

Examples include:

- Document storage
- Document deletion
- Text extraction
- Text chunking
- Embedding generation
- Retrieval
- AI response generation

### Models

SQLAlchemy models represent database tables and relationships.

### Schemas

Pydantic schemas validate API input and shape API output.

### Dependencies

Dependencies provide reusable functionality such as:

- Database sessions
- Authenticated users
- Authorization checks

### Utilities

Utility modules should contain small reusable technical functions that do not represent complete business workflows.

### Configuration

Environment-specific values must come from configuration and environment variables.

Secrets must not be hard-coded.

---

## 6. Non-Negotiable Rules for AI Assistants

Every AI assistant working on this project must follow these rules:

1. Do not recreate the project.

2. Do not delete working code merely to replace it with a preferred style.

3. Inspect the existing architecture before proposing modifications.

4. Preserve working authentication, document management, database, and routing behavior.

5. Implement only the requested feature.

6. Avoid unrelated refactoring.

7. Make the smallest complete change required.

8. Follow the current folder structure and naming conventions.

9. Keep routers thin and place business logic in services.

10. Keep database access controlled through the existing database session pattern.

11. Preserve authenticated ownership checks so users cannot access another user's documents.

12. Do not expose passwords, tokens, secret keys, API keys, or private configuration values.

13. Do not commit `.env`, databases, uploaded user documents, virtual environments, cache folders, or generated secret files.

14. Explain which files will be changed before implementation.

15. Explain why each changed file must be modified.

16. Do not modify a file that is unrelated to the requested feature.

17. Do not silently install dependencies.

18. State every new dependency and why it is required.

19. Use full-file replacement instructions when presenting code to the project owner.

20. Keep the application runnable after each development step.

21. Update project documentation after a verified milestone.

22. Never claim that a feature works unless it has been tested.

23. Clearly distinguish implemented functionality from planned functionality.

24. Do not mark work complete when unresolved errors remain.

25. Preserve backward compatibility unless a deliberate breaking change has been approved.

---

## 7. Required AI Workflow

Every AI-assisted development task must follow this process:

### Phase 1 — Inspect

Review:

- Relevant folders
- Relevant files
- Existing architecture
- Current project state
- Existing dependencies
- Existing tests
- Potential impact on working functionality

### Phase 2 — Plan

Before changing code, identify:

- The requested outcome
- Files that need modification
- Files that need creation
- Dependencies required
- Database changes required
- Tests required
- Risks to existing functionality

### Phase 3 — Implement

Implementation must:

- Follow existing architecture
- Avoid unrelated changes
- Use clear naming
- Include reasonable error handling
- Preserve user ownership and authentication rules
- Keep code maintainable

### Phase 4 — Test

Test the new feature as well as related existing features.

Testing may include:

- Application startup
- Swagger endpoint tests
- Successful request cases
- Invalid input cases
- Unauthorized access
- Missing resource cases
- Duplicate request cases
- Database verification
- Physical file verification
- Regression tests

### Phase 5 — Review

Review for:

- Security
- Correctness
- Data isolation
- Error handling
- Maintainability
- Unnecessary complexity
- Architectural fit
- Scalability concerns

### Phase 6 — Document

Update:

- PROJECT_STATE.md
- BUILD_LOG.md
- ARCHITECTURE.md when architecture changes
- Dependency files when packages change
- Environment examples when configuration changes

### Phase 7 — Commit

Only commit after:

- The feature works
- Relevant tests pass
- Documentation is updated
- Git status has been reviewed
- No secret or unnecessary file is staged

---

## 8. Git Safety Rules

The stable version of the project must always be recoverable through Git.

Before major AI-assisted changes:

1. Run `git status`.
2. Commit existing verified work.
3. Push the verified commit to GitHub.
4. Use a feature branch for risky or extensive changes.
5. Review the diff before committing.
6. Never force-push unless there is a deliberate and understood reason.
7. Never use destructive Git commands without explaining their effect first.

Recommended milestone workflow:

```text
Inspect current state
        ↓
Run and test application
        ↓
git status
        ↓
git add .
        ↓
git commit
        ↓
git push
        ↓
Begin next feature
```

---

## 9. Cursor-Assisted Development Policy (Clarification)

This section clarifies how Cursor-assisted sessions relate to the Git rules above.

### Two Git Contexts

| Context | Policy |
|---------|--------|
| **Project owner manual workflow** | Commit and push verified milestones when ready (see Section 8). |
| **Cursor feature implementation sessions** | **Do not** commit, push, reset, or rewrite Git history unless the project owner explicitly authorizes it in that session. |

Earlier project history includes owner-executed commits (for example, the July 17, 2026 document services milestone). Later Cursor rules and `.cursor/rules/` reinforce **no unauthorized Git operations during AI implementation**.

### Required Workflow Alignment

Cursor-assisted work follows:

```text
Inspect → Design → Review → Approve → Implement → Test → Document
```

Teaching-heavy interruptions should wait until Version 1 unless required to prevent architectural damage.

### Full-File Replacement

When the project owner applies changes manually:

- Use complete file contents, not fragments.
- Specify exact paths under `02-Projects/backend/`.
- Save files before testing.
- Reauthorize Swagger after Uvicorn reload when testing protected routes.

---

## 10. Documentation Standards

### Document Roles

| File | Contents |
|------|----------|
| `BUILD_LOG.md` | Chronological engineering history: implementation, tests, errors, investigations, fixes, lessons |
| `PROJECT_STATE.md` | Current verified state and next approved step only |
| `ARCHITECTURE.md` | Enduring architecture, decisions, rejected alternatives |
| `AI_DEVELOPMENT_PROTOCOL.md` | Stable process rules (this file) — not a chronological event log |

### Required Detail for Milestones

Each verified milestone should be documented with:

- Objective and context
- Design options and decision rationale (when applicable)
- Files created/modified
- Dependencies and configuration changes
- Commands and tests run
- Errors, misleading results, root-cause analysis, corrective action
- Final verification
- Engineering lessons
- Explicit distinction between **repository-proven** facts and **historical report supplied by project owner**

### Do Not Omit Failed Paths

Documentation must preserve:

- Unsuccessful attempts and reverted strategies (for example, rejected ownership migration backfill).
- Misleading verification results (for example, SQLite `PRAGMA foreign_keys = 0` on a raw connection that did not use the application engine).
- Documentation that claimed features existed before code did (for example, ownership before `user_id`).

### After Architecture Changes

Update `ARCHITECTURE.md` when schema, ownership boundaries, or processing pipelines change.

Update `PROJECT_STATE.md` and `BUILD_LOG.md` after verified milestones.

---

## 11. Evidence and Accuracy Rules

1. **Do not invent events.**
2. Mark unverifiable historical details as **historical report supplied by project owner**.
3. Mark file contents, migrations, and code behavior provable from the repository as **repository-proven**.
4. Preserve chronology; do not replace detailed logs with short summaries.
5. Separate **design**, **implementation**, **test**, **error**, **investigation**, **fix**, **verification**, and **lesson learned** in build log entries where practical.