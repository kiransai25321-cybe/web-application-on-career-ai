import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")


@dataclass
class Settings:
    APP_NAME: str = "AI Resume Analyzer"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-dev-secret-key-change-in-production-1234567890")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/resume_analyzer.db")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    MAX_UPLOAD_SIZE_BYTES: int = 5 * 1024 * 1024  # 5MB
    SESSION_MAX_AGE_DAYS: int = 14
    BASE_DIR: Path = BASE_DIR

    @property
    def google_oauth_enabled(self) -> bool:
        return bool(self.GOOGLE_CLIENT_ID and self.GOOGLE_CLIENT_SECRET)


settings = Settings()

