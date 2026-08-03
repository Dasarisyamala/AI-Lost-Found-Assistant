from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ItemOwner(BaseModel):
    id: int
    name: str
    email: str


class LostItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    item_name: str
    category: str
    description: str
    date_lost: date
    location: str
    image_path: Optional[str] = None
    status: str
    created_at: datetime
    image_url: Optional[str] = None


class LostItemPublicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item_name: str
    category: str
    description: str
    date_lost: date
    location: str
    status: str
    created_at: datetime
    image_url: Optional[str] = None


class FoundItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    description: str
    category: str
    date_found: date
    location: str
    image_path: Optional[str] = None
    status: str
    created_at: datetime
    image_url: Optional[str] = None

