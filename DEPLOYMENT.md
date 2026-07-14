# Deployment Guide

This app deploys as two independent services:

- **Frontend** (Next.js) → **Vercel** — zero-config, edge CDN, automatic preview deploys per PR
- **Backend** (FastAPI) → **Render** or **Railway** — Docker-based, includes managed Postgres + Redis

They communicate over HTTPS; no shared infrastructure is required between them.

---

## 1. Backend → Render

### 1.1 Create the Postgres database

1. Render dashboard → **New → PostgreSQL**
2. Choose a region close to where you'll deploy the backend service (same region avoids cross-region latency on every query)
3. Once created, copy the **Internal Database URL** — you'll need it in step 1.3

### 1.2 Create the Redis instance

1. Render dashboard → **New → Redis**
2. Same region as the Postgres instance
3. Copy the **Internal Redis URL**

### 1.3 Deploy the backend web service

1. Render dashboard → **New → Web Service** → connect your Git repository
2. Configure:
   - **Root directory:** `backend`
   - **Runtime:** Docker
   - **Dockerfile path:** `backend/Dockerfile` (auto-detected if root directory is set correctly)
   - **Region:** same as Postgres/Redis
   - **Instance type:** Starter is sufficient for MVP traffic; scale up if OCR/export jobs queue up
3. Environment variables (Render dashboard → your service → Environment):

   | Key | Value |
   |---|---|
   | `DATABASE_URL` | the Internal Database URL from step 1.1, with `postgresql://` changed to `postgresql+asyncpg://` |
   | `REDIS_URL` | the Internal Redis URL from step 1.2 |
   | `ENVIRONMENT` | `production` |
   | `JWT_SECRET` | generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |
   | `GOOGLE_CLIENT_ID` | from Google Cloud Console |
   | `GOOGLE_CLIENT_SECRET` | from Google Cloud Console |
   | `GOOGLE_REDIRECT_URI` | `https://your-vercel-domain.vercel.app/api/auth/callback/google` |
   | `ANTHROPIC_API_KEY` | optional, for AI parse cleanup |
   | `CORS_ORIGINS` | `["https://your-vercel-domain.vercel.app"]` |

4. Render builds the Docker image from `backend/Dockerfile` automatically on every push to your configured branch. The Dockerfile's `CMD` runs `alembic upgrade head` before starting Uvicorn, so schema migrations apply on every deploy with zero manual steps.
5. Once live, note the service URL (e.g. `https://quizgen-backend.onrender.com`) — you'll set this as `NEXT_PUBLIC_API_URL` on the frontend.

### 1.4 Health checks

Render automatically polls `GET /health` (already implemented in `main.py`) to determine deploy success and ongoing liveness. No extra configuration needed.

---

## 1-alt. Backend → Railway (alternative)

Railway's flow is nearly identical and slightly more automated:

1. Railway dashboard → **New Project → Deploy from GitHub repo**
2. Add a **PostgreSQL** plugin and a **Redis** plugin from the Railway marketplace — both auto-inject `DATABASE_URL`/`REDIS_URL`-style variables you can reference
3. For the backend service: **Settings → Root Directory** → `backend`; Railway auto-detects the Dockerfile
4. Add the same environment variables as the Render table above (Railway's plugin variables can be referenced directly, e.g. `${{Postgres.DATABASE_URL}}`, adjusting the driver prefix to `postgresql+asyncpg://`)
5. Railway assigns a public domain automatically under **Settings → Networking → Generate Domain**

---

## 2. Frontend → Vercel

1. [vercel.com](https://vercel.com) → **Add New → Project** → import your Git repository
2. **Root Directory:** `frontend` (Vercel auto-detects Next.js and applies the correct build settings — no `vercel.json` needed)
3. Environment variables (Vercel dashboard → Project → Settings → Environment Variables):

   | Key | Value |
   |---|---|
   | `NEXTAUTH_URL` | `https://your-project.vercel.app` (or your custom domain) |
   | `NEXTAUTH_SECRET` | generate with `openssl rand -base64 32` |
   | `GOOGLE_CLIENT_ID` | same value as the backend's |
   | `GOOGLE_CLIENT_SECRET` | same value as the backend's |
   | `NEXT_PUBLIC_API_URL` | `https://quizgen-backend.onrender.com/api/v1` (your backend URL from step 1.3, + `/api/v1`) |

4. Deploy. Vercel builds on every push to `main` and creates a preview deployment for every pull request automatically.
5. **Important:** go back to Google Cloud Console → your OAuth client → add the production redirect URI: `https://your-project.vercel.app/api/auth/callback/google`

---

## 3. Post-deployment checklist

- [ ] Visit the frontend URL and complete a full Google sign-in — confirms OAuth redirect URIs are correctly configured on both Google Cloud Console and both services' env vars
- [ ] Create a test project, paste sample MCQ text, confirm parsing works end-to-end
- [ ] Generate a Google Form from the parsed questions — confirms the backend's Google API calls succeed with production credentials
- [ ] Check the backend's `/health` endpoint returns `{"status": "ok"}`
- [ ] Confirm `CORS_ORIGINS` on the backend exactly matches the frontend's deployed domain (a mismatch here is the most common cross-service deployment error — the browser console will show CORS errors on every API call)
- [ ] If using Tesseract OCR in production, upload a sample scanned image and confirm text extraction works (Render/Railway's Docker build includes the Tesseract language packs from `backend/Dockerfile` — no extra setup needed, but worth a smoke test)

---

## 4. Scaling notes

- The backend's export-cleanup background task (hourly sweep of expired files) runs as an `asyncio` task inside the same process — for a single-instance deployment this is sufficient. If you scale the backend to multiple instances, move this to a proper Celery beat schedule (the `celery` + `redis` dependencies are already in `requirements.txt` for this reason) so the sweep doesn't run redundantly on every instance.
- Local disk storage for exports (`/tmp/quizgen_exports`) does **not** persist across Render/Railway container restarts or multi-instance deployments. For production traffic beyond a single instance, swap the export storage in `app/routers/exports.py` for S3-compatible object storage (the signed-URL scheme in `app/utils/signed_url.py` is storage-agnostic and works the same way against an S3 presigned URL).
