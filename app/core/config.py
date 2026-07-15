from dataclasses import dataclass
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]

try:
    from dotenv import load_dotenv
except ImportError:  # Allows bare source imports before dependencies are installed.
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True, slots=True)
class Settings:
    project_name: str = "Real Estate Listings Platform API"
    api_v1_prefix: str = os.getenv("API_V1_PREFIX", "/api/v1")
    database_url: str = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT / 'real_estate.db'}")
    media_root: Path = Path(os.getenv("MEDIA_ROOT", str(PROJECT_ROOT / "media"))).resolve()

    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "development-only-change-this-secret")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
    refresh_token_days: int = int(os.getenv("REFRESH_TOKEN_DAYS", "30"))

    admin_email: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    admin_password: str | None = os.getenv("ADMIN_PASSWORD")
    admin_full_name: str = os.getenv("ADMIN_FULL_NAME", "Platform Admin")
    admin_phone_number: str = os.getenv("ADMIN_PHONE_NUMBER", "+10000000000")

    max_images_per_listing: int = int(os.getenv("MAX_IMAGES_PER_LISTING", "10"))
    max_image_bytes: int = int(os.getenv("MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))
    max_fuzzy_candidates: int = int(os.getenv("MAX_FUZZY_CANDIDATES", "2000"))
    auto_create_schema: bool = os.getenv("AUTO_CREATE_SCHEMA", "true").lower() == "true"


settings = Settings()
