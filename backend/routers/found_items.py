from __future__ import annotations

import logging
from datetime import date

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from backend.config import settings
from backend.database import get_db
from backend.models import FoundItem, LostItem, Match, User
from backend.schemas.items import FoundItemRead
from backend.services.ai_matching import get_matching_engine
from backend.services.auth_service import get_current_user
from backend.services.email_service import send_match_notification
from backend.services.storage import save_uploaded_file


router = APIRouter(prefix="/found-items", tags=["found-items"])
logger = logging.getLogger(__name__)


def _serialize_found_item(item: FoundItem) -> dict:
    return {
        "id": item.id,
        "user_id": item.user_id,
        "description": item.description,
        "category": item.category,
        "date_found": item.date_found,
        "location": item.location,
        "image_path": item.image_path,
        "status": item.status,
        "created_at": item.created_at,
        "image_url": f"{settings.backend_public_url}/uploads/{item.image_path}" if item.image_path else None,
    }


@router.post("", response_model=FoundItemRead, status_code=status.HTTP_201_CREATED)
def create_found_item(
    description: str = Form(...),
    category: str = Form(...),
    date_found: date = Form(...),
    location: str = Form(...),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_path = save_uploaded_file(image, "found")
    found_item = FoundItem(
        user_id=current_user.id,
        description=description.strip(),
        category=category.strip(),
        date_found=date_found,
        location=location.strip(),
        image_path=image_path,
        status="open",
    )
    db.add(found_item)
    db.commit()
    db.refresh(found_item)

    try:
        engine = get_matching_engine()

        try:
            engine.build_found_embeddings(found_item)
            db.commit()
            db.refresh(found_item)
        except Exception:
            db.rollback()
            logger.exception("Failed to build embeddings for found item %s", found_item.id)

        try:
            engine.refresh_index(found_item)
            matches = engine.find_matches_for_found(db, found_item)
            db.commit()

            if matches:
                found_item.status = "matched"
                db.commit()
                db.refresh(found_item)
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
                    if loaded_match is not None:
                        try:
                            send_match_notification(loaded_match.lost_item, loaded_match.found_item, loaded_match)
                        except Exception:
                            logger.exception("Failed to send match notification for match %s", match.id)
        except Exception:
            db.rollback()
            logger.exception("AI matching failed while creating found item %s; returning saved item", found_item.id)
    except Exception:
        logger.exception("Matching engine unavailable while creating found item %s", found_item.id)

    return _serialize_found_item(found_item)


@router.get("", response_model=list[FoundItemRead])
def list_found_items(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    items = (
        db.query(FoundItem)
        .options(joinedload(FoundItem.user))
        .filter(FoundItem.user_id == current_user.id)
        .order_by(FoundItem.created_at.desc())
        .all()
    )
    return [_serialize_found_item(item) for item in items]

