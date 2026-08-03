from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from backend.schemas.items import FoundItemRead, LostItemRead


class MatchSummary(BaseModel):
    id: int
    text_score: float
    image_score: Optional[float] = None
    final_score: float
    status: str
    created_at: datetime


class MatchRead(MatchSummary):
    model_config = ConfigDict(from_attributes=True)

    lost_item: LostItemRead
    found_item: FoundItemRead

