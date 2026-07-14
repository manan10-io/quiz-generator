from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── App ─────────────────────────────────────────────────────────────────
    APP_NAME: str = "QuizGen AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # ─── Database ────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./quizgen.db"
    # For PostgreSQL: postgresql+asyncpg://user:password@host/dbname

    # ─── Redis / Celery ──────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ─── Auth / JWT ──────────────────────────────────────────────────────────
    JWT_SECRET: str = "change-this-secret-in-production-minimum-32-chars"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ─── Google OAuth ────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/api/auth/callback/google"

    # ─── AI / Anthropic ──────────────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    AI_CLEANUP_ENABLED: bool = True
    AI_MODEL: str = "claude-haiku-4-5-20251001"   # Fast + cheap for cleanup

    # ─── Google Vision OCR (optional) ────────────────────────────────────────
    GOOGLE_VISION_API_KEY: str = ""
    USE_GOOGLE_VISION: bool = False

    # ─── Tesseract ───────────────────────────────────────────────────────────
    TESSERACT_CMD: str = "tesseract"  # or "/usr/bin/tesseract"
    OCR_LANGUAGES: str = "eng+hin+guj"  # English + Hindi + Gujarati

    # ─── File upload ─────────────────────────────────────────────────────────
    MAX_UPLOAD_MB: int = 25
    UPLOAD_DIR: str = "/tmp/quizgen_uploads"

    # ─── CORS ────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "https://quizgen.ai",
    ]

    # ─── Rate limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 60

    @property
    def is_dev(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
