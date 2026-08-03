from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.models import User
from backend.schemas.auth import UserRead
from backend.services.auth_service import get_current_user


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
def me(current_user: User = Depends(get_current_user)):
    return current_user
