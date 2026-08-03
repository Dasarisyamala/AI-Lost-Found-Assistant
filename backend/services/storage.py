from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.config import settings


def ensure_upload_dir() -> Path:
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    return settings.upload_dir


def save_uploaded_file(upload_file: UploadFile | None, prefix: str) -> str | None:
    if upload_file is None:
        return None
    upload_dir = ensure_upload_dir()
    suffix = Path(upload_file.filename or "image").suffix.lower() or ".jpg"
    filename = f"{prefix}_{uuid4().hex}{suffix}"
    file_path = upload_dir / filename
    with file_path.open("wb") as buffer:
        buffer.write(upload_file.file.read())
    return filename


def resolve_upload_path(filename: str | None) -> str | None:
    if not filename:
        return None
    return str(ensure_upload_dir() / filename)

