from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./lostfound.db")
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expire_minutes: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
    match_threshold: float = float(os.getenv("MATCH_THRESHOLD", "0.75"))
    text_weight: float = float(os.getenv("TEXT_WEIGHT", "0.5"))
    image_weight: float = float(os.getenv("IMAGE_WEIGHT", "0.5"))
    top_k: int = int(os.getenv("TOP_K", "5"))
    smtp_host: str = os.getenv("SMTP_HOST", "")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_sender: str = os.getenv("SMTP_SENDER", "noreply@lostfound.app")
    collection_point_info: str = os.getenv(
        "COLLECTION_POINT_INFO", "Security Office, Block A, 9am-5pm"
    )
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    backend_public_url: str = os.getenv("BACKEND_PUBLIC_URL", "http://localhost:8000")
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", Path(__file__).resolve().parent / "uploads"))


settings = Settings()
