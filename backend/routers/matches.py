from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from backend.config import settings
from backend.database import get_db
from backend.models import FoundItem, LostItem, Match, User
from backend.schemas.matches import MatchRead
from backend.services.auth_service import get_current_user
from backend.services.email_service import send_match_notification


router = APIRouter(prefix="/matches", tags=["matches"])


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


def _serialize_match(match: Match) -> dict:
    return {
        "id": match.id,
        "text_score": match.text_score,
        "image_score": match.image_score,
        "final_score": match.final_score,
        "status": match.status,
        "created_at": match.created_at,
        "lost_item": _serialize_lost_item(match.lost_item),
        "found_item": _serialize_found_item(match.found_item),
    }


def _get_match_or_404(db: Session, match_id: int) -> Match:
    match = (
        db.query(Match)
        .options(joinedload(Match.lost_item).joinedload(LostItem.user), joinedload(Match.found_item).joinedload(FoundItem.user))
        .filter(Match.id == match_id)
        .first()
    )
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")
    return match


@router.get("", response_model=list[MatchRead])
def list_matches(
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Match)
        .options(joinedload(Match.lost_item).joinedload(LostItem.user), joinedload(Match.found_item).joinedload(FoundItem.user))
        .join(Match.lost_item)
        .join(Match.found_item)
        .filter((LostItem.user_id == current_user.id) | (FoundItem.user_id == current_user.id))
        .order_by(Match.created_at.desc())
    )
    if status_filter in {"pending", "confirmed", "rejected"}:
        query = query.filter(Match.status == status_filter)
    matches = query.all()
    return [_serialize_match(match) for match in matches]


@router.get("/{match_id}", response_model=MatchRead)
def get_match(match_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    match = _get_match_or_404(db, match_id)
    if match.lost_item.user_id != current_user.id and match.found_item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this match")
    return _serialize_match(match)


@router.post("/{match_id}/confirm", response_model=MatchRead)
def confirm_match(match_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    match = _get_match_or_404(db, match_id)
    if match.lost_item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the lost item owner can confirm the match")
    match.status = "confirmed"
    match.lost_item.status = "closed"
    match.found_item.status = "closed"
    db.commit()
    db.refresh(match)
    return _serialize_match(match)


@router.post("/{match_id}/reject", response_model=MatchRead)
def reject_match(match_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    match = _get_match_or_404(db, match_id)
    if match.lost_item.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the lost item owner can reject the match")
    match.status = "rejected"
    db.commit()
    db.refresh(match)
    return _serialize_match(match)

