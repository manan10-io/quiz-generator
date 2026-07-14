# Known Issues — QuizGen AI

Generated 2026-07-14 from a production-readiness, error-handling, and security audit. None of these have been fixed — this is a documentation-only pass (see `FINAL_AUDIT_REPORT.md` §1 for the one exception, the export-download 500 fix, which *was* shipped this session).

Severity legend: **Critical** (exploitable/breaks prod outright) · **High** (should fix before public launch) · **Medium** (should fix soon, not launch-blocking alone) · **Low** (nice-to-have / hardening).

Each entry lists where the issue lives, so PRODUCTION_CHECKLIST.md items can reference these by number.

---

## Critical

### C1. Insecure hardcoded JWT_SECRET fallback with no startup validation
**File:** `backend/app/config.py:26`
**Issue:** `JWT_SECRET` defaults to the literal string `"change-this-secret-in-production-minimum-32-chars"` if the env var is unset. The app starts silently with this value — nothing fails loudly.
**Why it's critical:** This same secret is reused raw for HMAC-signing export-download tokens (`backend/app/utils/signed_url.py:35`). A deployment that forgets to set `JWT_SECRET` lets anyone who reads this public source file forge valid JWTs for any user (`sub=<any_user_id>`) *and* forge valid export-download tokens.
**Fix:** Add a startup validator (e.g. Pydantic `model_validator`) that raises if `ENVIRONMENT == "production"` and `JWT_SECRET` is unset, equals the default, or is under ~32 chars. Consider deriving the signed-URL HMAC key via HKDF from `JWT_SECRET` with a distinct context string instead of reusing the raw secret for two purposes.

### C2. No rate limiting enforced anywhere
**Files:** `backend/app/config.py:59` (dead config), `backend/app/main.py` (no middleware)
**Issue:** `RATE_LIMIT_PER_MINUTE` is defined but never read by any code — confirmed via grep, zero references outside its own definition. No `slowapi`/limiter middleware exists in `main.py` or `requirements.txt`.
**Why it's critical:** Exposes every endpoint to unlimited automated requests, notably:
- `POST /auth/google` — brute-force/credential-stuffing surface (mitigated somewhat by Google OAuth being the actual credential, but still allows abuse of the endpoint itself).
- `GET /export/file/{token}` — intentionally unauthenticated; unlimited guessing of tokens becomes cheap without rate limiting.
- `GET /parse/jobs/{job_id}` — also unauthenticated (see H3), compounding the exposure.
- Parsing/OCR/export-generation endpoints — unbounded requests can drive real cost (Anthropic API calls, Tesseract CPU, WeasyPrint PDF rendering).
**Fix:** Wire up `slowapi` (or equivalent) using the existing `RATE_LIMIT_PER_MINUTE` setting, applied globally at minimum, with tighter limits on unauthenticated endpoints.

---

## High

### H1. `Base.metadata.create_all` runs alongside Alembic on every startup
**File:** `backend/app/main.py:47-49`
**Issue:** The app calls `Base.metadata.create_all` in its lifespan startup, in addition to `alembic upgrade head` already running in `Dockerfile:51`.
**Risk:** If the ORM models and Alembic migration history ever drift, `create_all` will silently patch over the mismatch (creating missing tables/columns) rather than surfacing the drift as a migration failure. Currently `001_initial_schema.py` matches `models.py` column-for-column, so no drift exists today — but this masks future drift instead of catching it.
**Fix:** Drop `create_all` from the lifespan in favor of relying solely on Alembic; if kept as a dev convenience, gate it behind `settings.is_dev`.

### H2. Blocking synchronous I/O inside async route handlers stalls the event loop
**Files:** `backend/app/routers/parser.py:157,223` calling `backend/app/services/parser_service.py` (Tesseract subprocess, PyMuPDF rendering) and `backend/app/services/ai_service.py:86` (blocking Anthropic API call)
**Issue:** `parser_service.parse_text()`/`parse_file()` are synchronous and called directly with no `await run_in_threadpool(...)` or `asyncio.to_thread(...)` wrapping.
**Risk:** Under concurrent load, one large OCR/parsing job blocks the single-threaded asyncio event loop for its full duration — freezing **all other requests**, including unrelated ones (login, project listing, unrelated exports), not just other parse jobs.
**Fix:** Wrap the synchronous parser_service calls in `await run_in_threadpool(...)`.

### H3. `GET /parse/jobs/{job_id}` has no authentication
**File:** `backend/app/routers/parser.py:259-266`
**Issue:** Unlike every other endpoint in the app, this one has no `Depends(get_current_user)` and doesn't verify the caller owns the job.
**Risk:** Job status responses include warnings and question counts. Job IDs are UUIDv4 (low guessability), so practical exploitation requires either leaking a job ID or brute-forcing — the latter is currently unmitigated by rate limiting (see C2), which compounds this.
**Fix:** Add `Depends(get_current_user)`, store `user_id` on the job record, and verify ownership before returning status.

### H4. Export cleanup job is unsafe beyond a single replica
**Files:** `backend/app/services/export_cleanup.py`, scheduled in `backend/app/main.py:29-43`
**Issue:** Runs as a single in-process `asyncio` task on a fixed interval (documented in `DEPLOYMENT.md:102` as a known limitation, but not enforced in code).
**Risk:** Each additional replica/worker double-sweeps with no locking. A process crash-loop within the cleanup interval means expired exports never get cleaned up. Not currently a problem at single-instance scale, but a landmine for anyone who scales `--workers` or adds a second container without reading the deployment doc.
**Fix:** Move to Celery beat (dependency already present in the project) before any horizontal scaling.

### H5. No resource limits on any Docker Compose service
**File:** `docker-compose.yml`
**Issue:** No `deploy.resources`, `mem_limit`, or `cpus` constraints on postgres/redis/backend/frontend services.
**Risk:** A runaway OCR job or large PDF export (both CPU/memory-heavy via opencv/weasyprint) can OOM the host with no backpressure, potentially taking down co-located services.
**Fix:** Add memory/CPU limits, especially for the `backend` service.

### H6. Local disk storage doesn't survive restarts or scale across instances
**Files:** `UPLOAD_DIR` config (`backend/app/config.py`), export storage (`backend/app/routers/exports.py:36-37`)
**Issue:** Uploads and generated exports are written to local temp/disk paths. Already flagged as a known limitation in `DEPLOYMENT.md:103`.
**Risk:** A hard blocker (not just a "nice to have") for any real multi-instance production deployment — a file written by instance A is invisible to a request served by instance B, and everything is lost on container restart.
**Fix:** Move to object storage (S3-compatible) before deploying more than one backend instance.

---

## Medium

### M1. Raw exception text (`str(e)`) returned directly to API clients
**Files:**
- `backend/app/routers/exports.py` (export generation failure — known from prior session)
- `backend/app/routers/google_forms.py:96` — `detail=f"Google Forms API error: {str(e)}"`
- `backend/app/routers/parser.py:164,257` — `detail=f"...: {str(e)}"`
**Risk:** Leaks internal library/stack detail (Google API internals, pdfplumber/pytesseract internals, file paths) to API clients. Low severity since these aren't secrets, but violates least-information-disclosure practice.
**Fix:** Log the full exception server-side (already done via `logger.error`), return a generic client-facing message instead of interpolating `str(e)` into the HTTP response.

### M2. In-memory parse-job store is unbounded and non-persistent
**File:** `backend/app/routers/parser.py:37` (`_jobs` dict)
**Risk:** Never evicted — slow memory leak under sustained traffic. Also invisible across multiple worker processes (a job created on worker A can't be queried from worker B), which will silently break job-status polling under any multi-worker deployment.
**Fix:** Move job state to the database or Redis (already a dependency in the stack).

### M3. `User.token_expires_at` shares the same naive/aware datetime fragility as the fixed export bug
**File:** `backend/app/models/models.py:43` (column), guarded in `backend/app/google/oauth.py:80-81` (`is_token_expired()`)
**Issue:** Same `DateTime(timezone=True)` column type that caused the export-download 500 (SQLite drops tzinfo on read). Currently **not** broken because `is_token_expired()` explicitly re-attaches `tzinfo=timezone.utc` before comparing — but any future code path that compares `user.token_expires_at` directly against an aware datetime without going through that helper will reproduce the exact bug that was just fixed elsewhere.
**Fix:** Apply the same `_as_aware_utc()` helper pattern (from `backend/app/routers/exports.py`) here for consistency/defense-in-depth. Consider centralizing it in a shared utils module since it's now needed in two places.

### M4. Unhandled `OSError` on export file write
**File:** `backend/app/routers/exports.py` (`out_path.write_bytes(file_bytes)`, in `export_project`)
**Risk:** A disk-full or permission error after successful export *generation* raises an unhandled `OSError`, producing a raw 500 with no graceful handling.
**Fix:** Wrap the write in try/except, return a clear "export storage failed" error.

### M5. Silent per-page OCR render failures not surfaced to the end user
**File:** `backend/app/ocr/pdf_renderer.py:74-80`
**Issue:** Per-page render failures are logged and skipped; `render_pages()` only raises if *all* pages fail. Partial failures (e.g. "3 of 10 pages failed") are dropped with only a server-side log line.
**Fix:** Surface a "N of M pages failed to render" warning in the parse response so the user knows their result may be incomplete.

### M6. No SQLite-vs-production guard
**File:** `backend/app/config.py:19` (default `DATABASE_URL`), `backend/app/database.py:15-18`
**Issue:** SQLite is the default `DATABASE_URL`. Nothing prevents or warns if `ENVIRONMENT=production` while `DATABASE_URL` still points at SQLite (e.g. someone deploying via the root `Dockerfile` to a platform like Railway without setting `DATABASE_URL`). Under concurrent writes SQLite will throw `database is locked` errors.
**Fix:** Validate the DB driver against `ENVIRONMENT` at startup and fail loudly if they mismatch.

### M7. No network-error handling in Google Drive API client
**File:** `backend/app/google/drive_api.py`
**Issue:** Only HTTP-status errors are handled (`_raise_for_status`); no handling for `httpx.RequestError` (timeouts, connection errors).
**Risk:** Currently masked because the only caller (`backend/app/routers/google_forms.py:103-112`) wraps the whole block in try/except and degrades gracefully — but the module itself has no defense if called from anywhere else in the future.
**Fix:** Add explicit `httpx.RequestError` handling within the module itself, not just at the call site.

### M8. PII (full email) logged at INFO level
**File:** `backend/app/services/auth_service.py:70,83`
**Issue:** Logs `"New user registered: %s (%s)"` including full email + google_id at INFO level on every login/signup.
**Risk:** Minor GDPR-adjacent compliance concern if logs are shipped to a third-party log aggregator with no redaction policy.
**Fix:** Log user ID only, or move to DEBUG level.

### M9. No structured logging / explicit log-level configuration
**Files:** all modules use bare `logging.getLogger(__name__)`, no `logging.basicConfig`/`dictConfig` anywhere.
**Risk:** Relies entirely on Uvicorn's default root logger config. In production this can mean the app's own INFO logs are silently swallowed depending on how `--log-level` propagates.
**Fix:** Add explicit logging config in `main.py` (level driven by settings, structured/JSON output in production).

### M10. Export-download tokens are long-lived bearer credentials with no binding
**File:** `backend/app/utils/signed_url.py`, `backend/app/routers/exports.py`
**Issue:** Signed download tokens are valid for the full 24h export lifetime and are bearer-only — no binding to the requesting session/IP.
**Risk:** Anyone who intercepts or is forwarded a link can download for up to 24h. This is a reasonable, intentional tradeoff for shareable links (and the HMAC signing is otherwise sound — constant-time comparison, tamper-proof), but it should be a documented decision, not an implicit one.
**Fix:** No code change required if the shareable-link behavior is intended. If exports may contain sensitive question banks, consider shortening expiry or adding single-use semantics.

---

## Low

### L1. Unescaped HTML interpolation in PDF generator (confirmed not currently exploitable)
**File:** `backend/app/routers/exports.py` (PDF generator, `q.question_text`/`q.explanation`/option text interpolated into HTML fed to WeasyPrint)
**Status:** Verified **not exploitable** — WeasyPrint is a static HTML→PDF renderer with no JS execution, so injected `<script>` tags don't execute. Frontend was also checked and confirmed to use only safe JSX rendering (zero `dangerouslySetInnerHTML` in `frontend/src`).
**Residual risk:** Malformed HTML could break PDF layout; a future renderer change or format addition (e.g. SVG-with-scripts, CSS injection via `url()`) could reopen this.
**Fix:** Apply `html.escape()` to interpolated fields as defense-in-depth. Low urgency.

### L2. CORS combines `allow_credentials=True` with wildcard methods/headers
**File:** `backend/app/main.py:73-78`, origin allowlist in `backend/app/config.py:53-56`
**Status:** Currently safe — origins are an explicit allowlist (`localhost:3000`, `https://quizgen.ai`), not `"*"`.
**Risk:** Latent footgun: if the origin allowlist is ever accidentally widened to `"*"` while `allow_credentials=True` remains set, that becomes a full CSRF/credential-theft vulnerability.
**Fix:** No immediate action; consider narrowing `allow_methods`/`allow_headers` from wildcard as additional hardening.

### L3. CORS default value hardcodes a specific production domain
**File:** `backend/app/config.py:53-56`
**Issue:** The default value for `CORS_ORIGINS` includes a specific hardcoded domain (`https://quizgen.ai`) alongside localhost. `docker-compose.yml:68` and `DEPLOYMENT.md:47` already correctly override this explicitly in every real deployment path, so it's not currently exploited — just an odd default.
**Fix:** Default to localhost-only; require the production origin to be set explicitly via env everywhere it's deployed.

### L4. Malformed request options silently discarded
**File:** `backend/app/routers/parser.py:209`
**Issue:** A bare `except Exception:` swallows malformed `options` JSON from the client and silently falls back to `ParseOptions()` defaults with no log or client-facing warning.
**Fix:** Add a `logger.debug` call at minimum so silently-ignored malformed requests are traceable.

### L5. Narrow exception list in AI cleanup could miss unexpected response shapes
**File:** `backend/app/services/ai_service.py:105`
**Issue:** Catches `(anthropic.APIError, json.JSONDecodeError, KeyError)` specifically (good practice — not a broad catch-all), but a `TypeError` from an unexpected response shape (e.g. empty/non-text content) isn't caught at this level.
**Status:** Low risk in practice — it does propagate up to `parser.py:157`'s outer try/except and gets caught there, just without the same graceful-skip logging treatment as the other handled cases.
**Fix:** Optionally add `TypeError` to the caught exception tuple for consistent logging.

### L6. Frontend Dockerfile missing a HEALTHCHECK directive
**File:** `frontend/Dockerfile`
**Issue:** The backend `Dockerfile` has a `HEALTHCHECK`; the frontend one doesn't — a parity gap, not a functional bug (orchestrators can still be configured with external health checks).
**Fix:** Add a `HEALTHCHECK` directive for consistency with the backend image.

---

## Confirmed Sound — No Action Needed

These were specifically checked and found correct; listed so they aren't re-audited unnecessarily in the future:

- **Secrets never entered git history.** `.env`/`.env.local` are gitignored and `git log --all --full-history` shows zero commits containing either file. Current exposure of the checked-in-locally secrets is local-disk only.
- **JWT implementation is sound.** HS256 explicitly hardcoded on decode (not read from token header) — no `alg:none` bypass possible. Signature verified via `python-jose`, expiry enforced by the library.
- **No IDOR found.** Every router (`projects.py`, `questions.py`, `exports.py`, `google_forms.py`, `settings_dashboard.py`) scopes every by-ID fetch to `current_user.id`/`project.user_id`.
- **No SQL injection surface.** Exhaustive grep for raw `.execute(text(...))` or string-formatted SQL found nothing — 100% of DB access goes through SQLAlchemy's parameterized query builder.
- **No path traversal risk.** All storage paths are UUID-prefixed server-side; sanitized filenames only; upload filenames are never used to construct filesystem paths.
- **Dependency versions are reasonably current** (FastAPI 0.109.2, pydantic 2.6.1, python-jose 3.3.0, Next.js 14.1.0, next-auth 4.24.5, axios 1.6.5). Recommend `pip-audit`/`npm audit` for precise CVE-level scanning, not manually eyeballed here.
- **Alembic migrations match models exactly.** `001_initial_schema.py` matches `models.py` column-for-column across all 6 tables — no drift.
- **Pagination is bounded everywhere** via `Query(le=...)` constraints in projects/questions/exports routers.
- **Post-mutation flush ordering is correct** in `projects.py`/`questions.py` (the class of bug fixed in the prior session's questions.py delete-renumbering fix does not recur elsewhere).
- **PDF export gracefully degrades to TXT** on WeasyPrint failure rather than 500ing.
- **Tesseract/OCR error handling** consistently returns structured `OCRResult` objects with warnings rather than raising.
