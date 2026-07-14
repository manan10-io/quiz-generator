# QuizGen AI

**Convert any question bank into a professional Google Forms quiz in seconds.**

Paste MCQ text, upload a PDF/DOCX/image, or drop a scanned exam paper — QuizGen AI extracts every question, detects answers, and generates a fully-configured Google Form quiz with answer keys, marks, and quiz mode enabled, automatically.

---

## Features

- **7 input formats** — paste text, PDF, DOCX, TXT, CSV, images, screenshots
- **AI-powered parsing** — regex + NLP engine handles 7+ question/answer styles, with Claude-powered cleanup for ambiguous or broken OCR text
- **Multi-language OCR** — English, Hindi, and Gujarati, with automatic deskew/denoise/threshold preprocessing and an optional Google Vision API fallback for low-confidence scans
- **Rich question editor** — drag-and-drop reorder, inline editing, search/filter by topic/difficulty/status, duplicate detection
- **Google Forms generation** — quiz mode, answer keys, per-question marks, shuffle questions/options, confirmation message — all set via the Forms API in one call
- **Drive organization** — generated forms are automatically filed into a dedicated "QuizGen AI Quizzes" folder
- **9 export formats** — PDF, DOCX, Excel, CSV, JSON, TXT, Moodle XML, Quizizz CSV, Kahoot CSV
- **Google OAuth** — with automatic access-token refresh so long editing sessions never hit an expired-token wall

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, Framer Motion, Zustand, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic |
| Parser | Custom regex + NLP engine, Claude (Anthropic) for AI cleanup |
| OCR | Tesseract 5 (local), Google Cloud Vision (cloud fallback), OpenCV preprocessing |
| Auth | Google OAuth 2.0, JWT (HS256) |
| Database | PostgreSQL (production), SQLite (local dev) |
| Storage | Local disk with HMAC-signed expiring download links |

See [`PROJECT_STRUCTURE.md`](./quiz-gen-phase1/PROJECT_STRUCTURE.md) for the full folder layout and [`DATABASE_SCHEMA.md`](./quiz-gen-phase1/DATABASE_SCHEMA.md) for the data model.

---

## Project structure

```
quiz-generator/
├── frontend/                      Next.js 14 App Router application
│   ├── src/
│   │   ├── app/                     Routes: landing, (auth), (dashboard)
│   │   ├── components/              UI components (30+, organized by domain)
│   │   ├── hooks/                   Custom React hooks (auth, parser, exports...)
│   │   ├── lib/                     Utils, constants, validators, animations
│   │   ├── services/                API client layer
│   │   ├── store/                   Zustand stores
│   │   └── types/                   Shared TypeScript types
│   ├── public/
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── Dockerfile
│   └── .env.local.example
│
├── backend/                       FastAPI application
│   ├── app/
│   │   ├── auth/                    JWT signing/verification + get_current_user dependency
│   │   ├── parser/                   MCQ text parsing engine (7 formats + AI cleanup)
│   │   ├── ocr/                      Tesseract + Vision OCR pipeline
│   │   ├── google/                   Forms API, Drive API, OAuth token refresh
│   │   ├── routers/                  REST API endpoints (7 routers)
│   │   ├── services/                 Business logic layer
│   │   ├── models/                   SQLAlchemy ORM models (6 tables)
│   │   ├── schemas/                  Pydantic request/response schemas
│   │   ├── utils/                    Signed download URLs
│   │   ├── config.py                 Settings (pydantic-settings)
│   │   ├── database.py               Async engine + session
│   │   └── main.py                   App factory, router wiring, lifespan
│   ├── tests/                        8 pytest files covering every module above
│   ├── alembic/                      Migrations (initial schema included, ready to run)
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── Dockerfile
│   └── .env.example
│
├── .github/workflows/ci.yml       Lint → test → Docker build validation
├── Dockerfile                      Root-level (builds backend; see comments inside)
├── docker-compose.yml              Full stack: Postgres + Redis + backend + frontend
├── docker-compose.dev.yml          Hot-reload overrides for local development
├── README.md
├── DEPLOYMENT.md
├── Makefile
├── .env.example                    Root-level, used by docker-compose.yml
├── .gitignore
└── LICENSE
```

---

## Quick start

### Option A — Docker Compose (recommended, zero local setup)

```bash
git clone <this-repo>
cd quiz-generator

cp .env.example .env
# Edit .env and fill in JWT_SECRET, NEXTAUTH_SECRET, GOOGLE_CLIENT_ID,
# GOOGLE_CLIENT_SECRET (see "Google OAuth setup" below)

make up
# or: docker compose up --build
```

Visit **http://localhost:3000**. The backend runs at **http://localhost:8000** (interactive API docs at `/docs` when `ENVIRONMENT=development`).

For hot-reload during active development:

```bash
make dev
# or: docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

### Option B — Run natively (no Docker)

**Backend:**

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# System dependency: Tesseract OCR
# macOS:   brew install tesseract tesseract-lang
# Ubuntu:  sudo apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-guj

cp .env.example .env   # fill in the values — see backend/.env.example
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

**Frontend** (in a second terminal):

```bash
cd frontend
npm install
cp .env.local.example .env.local   # fill in the values
npm run dev
```

---

## Google OAuth setup

QuizGen AI needs a Google Cloud OAuth client to sign users in and create Forms/Drive files on their behalf.

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → create or select a project
2. **APIs & Services → Library** — enable:
   - Google Forms API
   - Google Drive API
3. **APIs & Services → Credentials → Create Credentials → OAuth client ID**
   - Application type: Web application
   - Authorized redirect URI: `http://localhost:3000/api/auth/callback/google` (add your production URL too, once deployed)
4. Copy the generated **Client ID** and **Client Secret** into both `backend/.env` and `frontend/.env.local` (they must match)
5. **OAuth consent screen** — add the `forms.body` and `drive.file` scopes (already requested by the frontend's NextAuth config in `lib/auth.ts`)

---

## Running tests

```bash
make test-backend
# or: cd backend && pytest -v

make test-backend-cov   # with coverage report
```

The backend test suite covers: parser format detection (7 formats + edge cases), answer/option extraction, duplicate detection, OCR preprocessing and language detection (against the real Tesseract binary), JWT auth, all 9 export generators, Google OAuth token refresh, Drive API folder management, and signed download URL security (tamper detection, expiry enforcement, secret rotation).

---

## Deployment

See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for step-by-step guides:
- **Frontend → Vercel** (recommended — zero-config Next.js hosting)
- **Backend → Render or Railway** (Docker-based, includes managed Postgres + Redis)

---

## License

Proprietary — see [`LICENSE`](./LICENSE) for full terms.
