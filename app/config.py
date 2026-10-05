import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")


def resolve_database_url(raw_url: str) -> str:
    """
    Ensure SQLite URLs with relative paths resolve relative to BASE_DIR (project root),
    preventing CWD-dependent database file locations upon application restart.
    """
    if not raw_url:
        db_path = (BASE_DIR / "resume_analyzer.db").resolve()
        return f"sqlite:///{db_path.as_posix()}"

    if raw_url.startswith("sqlite:///"):
        sqlite_path_str = raw_url[10:]
        if sqlite_path_str == ":memory:" or sqlite_path_str.startswith("?"):
            return raw_url

        params = ""
        if "?" in sqlite_path_str:
            sqlite_path_str, params = sqlite_path_str.split("?", 1)
            params = "?" + params

        path_obj = Path(sqlite_path_str)
        if not path_obj.is_absolute():
            path_obj = (BASE_DIR / path_obj).resolve()
        return f"sqlite:///{path_obj.as_posix()}{params}"

    return raw_url


@dataclass
class Settings:
    APP_NAME: str = "AI Resume Analyzer"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "insecure-dev-secret-key-change-in-production-1234567890")
    DATABASE_URL: str = field(default_factory=lambda: resolve_database_url(os.getenv("DATABASE_URL", "")))
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


