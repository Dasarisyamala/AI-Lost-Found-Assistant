from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.database import Base, SessionLocal, engine
from backend.models import FoundItem, LostItem, Match, User  # noqa: F401
from backend.routers.auth import router as auth_router
from backend.routers.found_items import router as found_items_router
from backend.routers.lost_items import router as lost_items_router
from backend.routers.matches import router as matches_router
from backend.routers.users import router as users_router
from backend.services.ai_matching import get_matching_engine
from backend.services.storage import ensure_upload_dir


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_upload_dir()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Lost & Found Assistant", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(ensure_upload_dir())), name="uploads")

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(lost_items_router)
app.include_router(found_items_router)
app.include_router(matches_router)


@app.get("/")
def root():
    return {"message": "AI Lost & Found Assistant API"}

