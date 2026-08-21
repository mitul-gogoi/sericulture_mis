"""App settings loaded from environment."""
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT / ".env")


class Settings:
    APP_NAME: str = os.environ.get("APP_NAME", "sericulture-mis")
    DATABASE_URL: str = os.environ["DATABASE_URL"]
    JWT_SECRET: str = os.environ["JWT_SECRET"]
    JWT_REFRESH_SECRET: str = os.environ["JWT_REFRESH_SECRET"]
    JWT_ALGORITHM: str = "HS256"
    # Required, fail-closed: farmer Aadhaar numbers are unreadable without it. Losing or
    # rotating this key permanently breaks decryption AND duplicate detection — see
    # app/core/aadhaar.py.
    AADHAAR_SECRET_KEY: str = os.environ["AADHAAR_SECRET_KEY"]
    ACCESS_TOKEN_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_MINUTES", "30"))
    REFRESH_TOKEN_DAYS: int = int(os.environ.get("REFRESH_TOKEN_DAYS", "7"))
    UPLOAD_ROOT: Path = Path(os.environ.get("UPLOAD_ROOT", str(ROOT / "file_uploads")))
    RATE_LIMIT_LOGIN: str = os.environ.get("RATE_LIMIT_LOGIN", "5/minute")
    CORS_ORIGINS: list[str] = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    DB_POOL_SIZE: int = int(os.environ.get("DB_POOL_SIZE", "5"))
    DB_MAX_OVERFLOW: int = int(os.environ.get("DB_MAX_OVERFLOW", "5"))
    STATE_ADMIN_MOBILE: str = os.environ.get("STATE_ADMIN_MOBILE", "9999999999")
    STATE_ADMIN_PASSWORD: str = os.environ.get("STATE_ADMIN_PASSWORD", "Admin@123")
    DISTRICT_ADMIN_MOBILE: str = os.environ.get("DISTRICT_ADMIN_MOBILE", "8888888888")
    DISTRICT_ADMIN_PASSWORD: str = os.environ.get("DISTRICT_ADMIN_PASSWORD", "District@123")
    FIG_PRESIDENT_MOBILE: str = os.environ.get("FIG_PRESIDENT_MOBILE", "7777777777")
    FIG_PRESIDENT_PASSWORD: str = os.environ.get("FIG_PRESIDENT_PASSWORD", "Fig@123")


settings = Settings()
