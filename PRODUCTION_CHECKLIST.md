# Production Checklist — QuizGen AI

Derived from the 2026-07-14 audit. Each unchecked item links to its full writeup in `KNOWN_ISSUES.md`. Check items off as they're fixed and verified — don't check based on intent alone.

Legend: 🔴 blocks any public multi-instance production launch · 🟡 should fix before launch · 🟢 hardening / can follow launch.

---

## 🔴 Must-fix before production launch

- [ ] **Enforce a real `JWT_SECRET` in production** — fail startup if unset/default/too short. *(KNOWN_ISSUES.md → C1)*
- [ ] **Turn on rate limiting** — wire up the already-defined `RATE_LIMIT_PER_MINUTE` setting with real middleware (e.g. slowapi), especially on unauthenticated endpoints (`/export/file/{token}`, `/parse/jobs/{job_id}`). *(C2)*
- [ ] **Move export/upload storage off local disk** to object storage (S3-compatible) — required before running more than one backend instance. *(H6)*
- [ ] **Move export-cleanup off in-process asyncio** to Celery beat (dependency already present) before scaling beyond one replica. *(H4)*
- [ ] **Add resource limits** (`mem_limit`/`cpus`) to every service in `docker-compose.yml`, especially `backend`. *(H5)*

## 🟡 Should fix before launch

- [ ] **Add authentication to `GET /parse/jobs/{job_id}`** — currently the only unauthenticated endpoint outside the intentionally-open `/export/file/{token}`. *(H3)*
- [ ] **Wrap synchronous parser/OCR calls in `run_in_threadpool`** so large jobs don't stall the event loop for all concurrent requests. *(H2)*
- [ ] **Drop `Base.metadata.create_all` from startup lifespan** (or gate behind dev-only) — rely solely on Alembic so schema drift surfaces instead of being silently patched. *(H1)*
- [ ] **Move parse-job state out of the in-process dict** into DB/Redis so it survives restarts and works across multiple workers. *(M2)*
- [ ] **Add a startup guard against SQLite-in-production** — fail loudly if `ENVIRONMENT=production` and `DATABASE_URL` still points at SQLite. *(M6)*
- [ ] **Stop returning raw `str(e)` in HTTP error responses** across `exports.py`, `google_forms.py`, `parser.py` — log full detail server-side, return generic messages to clients. *(M1)*
- [ ] **Apply the `_as_aware_utc()` fix pattern to `User.token_expires_at` comparisons** for defense-in-depth, even though `is_token_expired()` currently guards it correctly. *(M3)*
- [ ] **Wrap the export file write in try/except** so a disk-full/permission error doesn't produce a raw unhandled 500. *(M4)*
- [ ] **Add explicit logging configuration** (level + structured/JSON output) instead of relying on Uvicorn defaults. *(M9)*
- [ ] **Run real browser-based E2E tests** (Playwright/Cypress or manual click-through) covering: Google OAuth login, file upload + parsing, question editor, export download for every format, Google Forms generation and its failure path. This audit only verified API-contract correctness, not actual rendered UI behavior — see `FINAL_AUDIT_REPORT.md` §2.3 for what was and wasn't covered.

## 🟢 Hardening — can follow initial launch

- [ ] Redact PII (full email) from INFO-level auth logs, or move to DEBUG. *(M8)*
- [ ] Surface partial OCR page-render failures to the end user instead of only logging them. *(M5)*
- [ ] Add `httpx.RequestError` handling directly inside `drive_api.py` rather than relying on the caller's try/except. *(M7)*
- [ ] Document (or shorten) the 24h bearer-token export-download window as an intentional design decision. *(M10)*
- [ ] Apply `html.escape()` to interpolated fields in the PDF generator as defense-in-depth (confirmed not currently exploitable). *(L1)*
- [ ] Narrow CORS `allow_methods`/`allow_headers` from wildcard now that credentials are allowed. *(L2)*
- [ ] Change the `CORS_ORIGINS` default to localhost-only instead of hardcoding a specific production domain. *(L3)*
- [ ] Log a debug line when malformed `options` JSON is silently discarded in `parser.py`. *(L4)*
- [ ] Add `TypeError` to the caught exceptions in `ai_service.py`'s cleanup call for consistent logging. *(L5)*
- [ ] Add a `HEALTHCHECK` directive to `frontend/Dockerfile` for parity with the backend image. *(L6)*
- [ ] Run `pip-audit` and `npm audit` for CVE-level dependency scanning (versions were only eyeballed as reasonably current). *(KNOWN_ISSUES.md → Confirmed Sound)*

---

## Already Verified Working — No Action Needed

- [x] Export-download 500 bug fixed and verified end-to-end (naive/aware datetime comparison). 197/197 backend tests passing.
- [x] Secrets confirmed never committed to git history.
- [x] JWT implementation confirmed sound (HS256 hardcoded, no algorithm-confusion bypass).
- [x] No IDOR found across any router — all by-ID lookups scoped to the authenticated user.
- [x] No SQL injection surface — 100% parameterized queries via SQLAlchemy.
- [x] No path traversal risk in file storage.
- [x] Alembic migrations match ORM models exactly, no drift.
- [x] Login, project CRUD, text/PDF parsing, OCR, Google Forms graceful failure, and export generation all manually verified working (prior session checkpoint).

---

**Bottom line:** Safe for continued development and single-instance/internal use today. Not safe for a public multi-instance production launch until the 🔴 items above are resolved — the JWT-secret and rate-limiting gaps in particular are exploitable, not just theoretical.
