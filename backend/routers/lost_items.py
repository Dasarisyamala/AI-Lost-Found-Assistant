from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from backend.config import settings
from backend.database import get_db
from backend.models import FoundItem, LostItem, Match, User
from backend.schemas.items import LostItemPublicRead, LostItemRead
from backend.services.ai_matching import get_matching_engine
from backend.services.auth_service import get_current_user
from backend.services.email_service import send_match_notification
from backend.services.storage import save_uploaded_file


router = APIRouter(prefix="/lost-items", tags=["lost-items"])
logger = logging.getLogger(__name__)


def _serialize_lost_item(item: LostItem) -> dict:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "item_name": item.item_name,
        "category": item.category,
        "description": item.description,
        "date_lost": item.date_lost,
        "location": item.location,
        "image_path": item.image_path,
        "status": item.status,
        "created_at": item.created_at,
        "image_url": f"{settings.backend_public_url}/uploads/{item.image_path}" if item.image_path else None,
    }


def _serialize_public_lost_item(item: LostItem) -> dict:
    return {
        "id": item.id,
        "item_name": item.item_name,
        "category": item.category,
        "description": item.description,
        "date_lost": item.date_lost,
        "location": item.location,
        "status": item.status,
        "created_at": item.created_at,
        "image_url": f"{settings.backend_public_url}/uploads/{item.image_path}" if item.image_path else None,
    }


@router.post("", response_model=LostItemRead, status_code=status.HTTP_201_CREATED)
def create_lost_item(
    item_name: str = Form(...),
    category: str = Form(...),
    description: str = Form(...),
    date_lost: date = Form(...),
    location: str = Form(...),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_path = save_uploaded_file(image, "lost")
    lost_item = LostItem(
        user_id=current_user.id,
        item_name=item_name.strip(),
        category=category.strip(),
        description=description.strip(),
        date_lost=date_lost,
        location=location.strip(),
        image_path=image_path,
        status="open",
    )
    db.add(lost_item)
    db.commit()
    db.refresh(lost_item)

    try:
        engine = get_matching_engine()
        engine.build_lost_embeddings(lost_item)
        db.commit()
        db.refresh(lost_item)
        engine.refresh_index(lost_item)

        matches = engine.find_matches_for_lost(db, lost_item)
        db.commit()

        if matches:
            lost_item.status = "matched"
            db.commit()
            db.refresh(lost_item)
            for match in matches:
                db.refresh(match)
                loaded_match = (
                    db.query(Match)
                    .options(
                        joinedload(Match.lost_item).joinedload(LostItem.user),
                        joinedload(Match.found_item).joinedload(FoundItem.user),
                    )
                    .filter(Match.id == match.id)
                    .first()
                )
                if loaded_match is None:
                    continue
                try:
                    send_match_notification(loaded_match.lost_item, loaded_match.found_item, loaded_match)
                except Exception:
                    logger.exception("Failed to send match notification for match %s", match.id)
    except Exception:
        db.rollback()
        logger.exception("AI matching failed while creating lost item %s; returning saved item", lost_item.id)

    return _serialize_lost_item(lost_item)


@router.get("", response_model=list[LostItemRead])
def list_lost_items(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = (
        db.query(LostItem)
        .options(joinedload(LostItem.user))
        .filter(LostItem.user_id == current_user.id)
        .order_by(LostItem.created_at.desc())
        .all()
    )
    return [_serialize_lost_item(item) for item in items]


@router.get("/public", response_model=list[LostItemPublicRead])
def list_public_lost_items(db: Session = Depends(get_db)):
    items = (
        db.query(LostItem)
        .filter(LostItem.status == "open")
        .order_by(LostItem.created_at.desc())
        .all()
    )
    return [_serialize_public_lost_item(item) for item in items]

