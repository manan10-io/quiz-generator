# Final Audit Report — QuizGen AI

**Date:** 2026-07-14
**Scope:** Full-stack audit of `quiz-generator` (FastAPI backend + Next.js frontend), covering functional correctness, production readiness, error handling, and security.
**Commit:** `7c23d81` — "Initial QuizGen AI with Claude audit fixes"

This report consolidates two audit passes:

1. An earlier functional-correctness pass (parser, questions CRUD, exports) plus a live-bug investigation of a 500 error on export download.
2. This pass: production readiness, error handling, frontend E2E, and security — run after the export bug fix landed.

No code was modified during this second pass except where noted in [Fixes Shipped](#fixes-shipped-this-audit). Everything else is documented for the maintainer to triage; see `KNOWN_ISSUES.md` and `PRODUCTION_CHECKLIST.md`.

---

## 1. Fixes Shipped (this audit)

### 1.1 Export download 500 — naive/aware datetime comparison

**Symptom:** `GET /api/v1/export/download/{record_id}` returned `500 Internal Server Error`.

**Root cause:** `ExportRecord.expires_at` is declared `DateTime(timezone=True)`, but SQLite (via aiosqlite) does not preserve tzinfo on read — the value comes back naive. `backend/app/routers/exports.py` compared this naive value directly against `datetime.now(timezone.utc)` (aware), which raises `TypeError: can't compare offset-naive and offset-aware datetimes`. This was uncaught, producing an unhandled 500.

Confirmed via the live server's traceback log (`/private/tmp/quizgen-backend.log`) and reproduced directly against the database (`expires_at` read back with `tzinfo: None`).

**Fix:** Added `_as_aware_utc()` helper in `backend/app/routers/exports.py` (mirrors the existing pattern already used correctly in `backend/app/utils/signed_url.py`), applied at both comparison sites:
- `get_download_url` (was line 112, now ~123)
- `download_file` (was line 157, now ~168)

**Verification:**
- Restarted the backend, minted a JWT for the record's owning user, and replayed the exact request that had crashed (`GET /export/download/{record_id}`) → now returns `200 OK`.
- Followed the resulting signed URL through `GET /export/file/{token}` → returned the actual PDF bytes (16671 bytes, valid PDF per `file` command).
- Full backend test suite: **197/197 passing**, no regressions.
- Confirmed no new errors appear in the backend log after the fix.

This fix is committed in `HEAD` (`7c23d81`).

### 1.2 Prior session's fixes (carried forward, not re-verified in this pass per instruction)

- `backend/app/services/parser_service.py` — OCR adaptive-threshold block size was hardcoded to `11`; changed to resolution-scaled.
- `backend/app/routers/questions.py` — fixed a duplicate-endpoint bug where `question_number` wasn't copied correctly.
- `backend/app/routers/questions.py` — fixed a delete-renumbering bug by adding `await db.flush()` before requery (required because `AsyncSessionLocal` is configured with `autoflush=False`).
- `alembic stamp head` executed to reconcile migration state.
- 197 backend tests passing at that checkpoint.
- Manually verified: login flow, project CRUD, text parsing, PDF parsing, OCR, Google Forms graceful failure, export generation.

This pass did not re-audit these modules, per instruction. The one related finding worth flagging: the audit below found the *same class* of naive/aware datetime bug pattern also present (but currently defensively guarded) on `User.token_expires_at` — see `KNOWN_ISSUES.md` #7.

---

## 2. Audits Performed This Pass

### 2.1 Production Readiness Audit

Reviewed: config/secrets management, database (SQLite vs. Postgres), Docker/deployment, logging, CORS, background jobs, frontend build config, rate limiting.

**Headline findings:**
- `JWT_SECRET` has an insecure hardcoded fallback with no startup validation forcing it to be overridden in production.
- `RATE_LIMIT_PER_MINUTE` is defined in config but never enforced anywhere in the app.
- `Base.metadata.create_all` runs on every startup in addition to Alembic migrations — can silently mask schema drift.
- Export cleanup runs as a single in-process asyncio task; unsafe beyond one replica (already flagged in `DEPLOYMENT.md`, but not enforced).
- No resource limits (`mem_limit`/`cpus`) on any `docker-compose.yml` service.
- Local disk storage for uploads/exports doesn't persist or share across restarts/multi-instance deploys.
- No validation preventing SQLite from being used in a `production` environment.
- No structured logging / explicit log-level configuration.

Full detail with file:line references in `KNOWN_ISSUES.md` (Production Readiness section).

### 2.2 Error Handling Audit

Reviewed: all routers and services for unhandled exceptions, broad except clauses, async/autoflush pitfalls, input validation, resource leaks, error-message leakage, Google API error handling.

**Headline findings:**
- Synchronous, blocking I/O (Tesseract OCR subprocess calls, PyMuPDF rendering, blocking Anthropic API calls) is invoked directly inside async route handlers with no `run_in_threadpool`/`asyncio.to_thread` — a single large OCR job stalls the entire event loop, freezing unrelated requests.
- Raw exception text (`str(e)`) is returned directly to API clients in several endpoints beyond the already-known `exports.py` case (`google_forms.py`, `parser.py`) — leaks internal library/stack detail.
- The in-memory parse-job store (`parser.py`) is unbounded, non-persistent, and invisible across multiple worker processes.
- The same naive/aware `DateTime(timezone=True)` SQLite behavior that caused the export bug also affects `User.token_expires_at` — currently *not* broken because `is_token_expired()` defensively re-normalizes it, but fragile against any future direct comparison.
- A handful of medium/low findings: unguarded `OSError` on export file write, silent per-page OCR render failures not surfaced to the end user, missing network-error handling in `drive_api.py` (currently masked by its only caller).
- Confirmed **not** broken: pagination bounds, path traversal protections, post-mutation flush ordering elsewhere in the codebase, PDF export's graceful fallback to TXT, Tesseract error handling.

Full detail in `KNOWN_ISSUES.md` (Error Handling section).

### 2.3 Frontend E2E Verification

**Method and limitation:** No browser automation tool was available in this environment, so verification was performed at the route/API-contract level rather than via actual UI interaction (clicking, form-filling, visual inspection). This is a real gap — it confirms the frontend *can* correctly reach and consume the backend, not that the rendered UI behaves correctly for a human user.

What was verified:
- All frontend routes return expected HTTP status codes with no error content: `/`, `/login` → 200; `/dashboard`, `/history`, `/projects`, `/projects/new` → 307 redirect to `/login` when unauthenticated (correct NextAuth middleware behavior).
- The frontend's API service layer (`frontend/src/services/index.ts`, `frontend/src/services/api.ts`) was cross-checked against actual backend router prefixes (`backend/app/main.py`) — every call site (`/export/*`, `/parse/*`, `/forms/*`) matches a real, correctly-prefixed backend endpoint. No integration drift found.
- The export-download URL resolution chain — the exact flow behind the bug fixed in this session — was verified end-to-end: `exportService.getDownloadUrl()` correctly resolves the backend's relative `/api/v1/export/file/{token}` response against `NEXT_PUBLIC_API_URL` via `new URL(...)`, matching what was manually confirmed working via direct API calls (mint signed URL → fetch file → valid PDF returned).

What was **not** verified (recommend before shipping): actual browser rendering, click-through user flows (login via Google OAuth, drag-and-drop file upload, question editor interactions, PDF/DOCX visual output, responsive layout, accessibility). Recommend running this manually or wiring up Playwright/Cypress before production release — see `PRODUCTION_CHECKLIST.md`.

### 2.4 Security Review

Reviewed: secrets management, JWT/auth implementation, IDOR/authorization, SQL injection, path traversal, CORS, XSS, dependency versions, rate limiting/brute-force protection.

**Headline findings:**
- Same `JWT_SECRET` fallback issue as above, sharper implication here: this secret is reused raw for **both** JWT signing and HMAC export-download token signing — a misconfigured deployment lets an attacker forge both credentials from one leaked/default value.
- No rate limiting anywhere, notably exposing the unauthenticated `/export/file/{token}` and `/parse/jobs/{job_id}` endpoints to unlimited automated requests.
- `GET /parse/jobs/{job_id}` has no authentication at all — the one inconsistent endpoint in an otherwise-consistent per-user auth model. Low practical risk (UUIDv4 job IDs) but worth fixing for consistency.
- Export-download tokens are valid bearer credentials for the full 24h lifetime with no session/IP binding — an accepted tradeoff for shareable links, but should be documented as intentional.
- CORS config is currently safe (explicit origin allowlist) but combines `allow_credentials=True` with wildcard methods/headers — a latent risk if origins are ever loosened.
- Unescaped HTML interpolation in the PDF generator — confirmed **not exploitable** (WeasyPrint doesn't execute embedded scripts/JS; frontend confirmed to use only safe JSX rendering, zero `dangerouslySetInnerHTML` found anywhere).

**Confirmed sound, no action needed:**
- `.env` / `.env.local` are correctly gitignored and were **never** committed to git history (verified via `git log --all --full-history`) — exposure is local-disk-only, not a leaked-secret incident.
- JWT uses HS256 explicitly with the algorithm hardcoded on decode (not read from the token header) — no `alg:none` bypass possible.
- Exhaustive check of every router found correct ownership scoping on all by-ID lookups — no IDOR found.
- Zero raw/string-interpolated SQL anywhere — 100% parameterized via SQLAlchemy's query builder.
- No path traversal risk — all storage paths are UUID-prefixed server-side, sanitized filenames only.
- Dependency versions (FastAPI 0.109.2, pydantic 2.6.1, python-jose 3.3.0, Next.js 14.1.0, next-auth 4.24.5) are all reasonably current; recommend `pip-audit`/`npm audit` for CVE-level precision.

Full detail in `KNOWN_ISSUES.md` (Security section).

---

## 3. Test Suite Status

```
197 passed in 14.17s
```
Re-run after the export fix landed — no regressions.

---

## 4. Overall Assessment

The application is **functionally correct and free of the specific bug reported** (export download 500). The core golden-path flows (auth, project CRUD, parsing, OCR, export generation and download) work end-to-end as verified via live API testing against the running dev server.

It is **not yet production-ready** in its current configuration, primarily due to:
1. An insecure default JWT secret with no startup enforcement (Critical — full auth bypass risk if misconfigured).
2. No rate limiting anywhere in the API (Critical — brute-force/abuse/cost exposure).
3. A cluster of deployment-scaling gaps (in-process cleanup job, local disk storage, no resource limits) that are fine for a single-instance/dev deployment but will break or become unsafe under horizontal scaling.

None of these block continued development or a single-instance internal deployment. They **do** block a public multi-instance production launch. See `PRODUCTION_CHECKLIST.md` for the concrete go/no-go list, and `KNOWN_ISSUES.md` for the full itemized backlog.
