from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class LostItem(Base):
    __tablename__ = "lost_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    item_name = Column(String(255), nullable=False)
    category = Column(String(80), nullable=False)
    description = Column(Text, nullable=False)
    date_lost = Column(Date, nullable=False)
    location = Column(String(255), nullable=False)
    image_path = Column(String(255), nullable=True)
    embedding_text = Column(Text, nullable=True)
    embedding_image = Column(Text, nullable=True)
    status = Column(String(30), default="open", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="lost_items")
    matches = relationship("Match", back_populates="lost_item", cascade="all, delete-orphan")


class FoundItem(Base):
    __tablename__ = "found_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(80), nullable=False)
    date_found = Column(Date, nullable=False)
    location = Column(String(255), nullable=False)
    image_path = Column(String(255), nullable=True)
    embedding_text = Column(Text, nullable=True)
    embedding_image = Column(Text, nullable=True)
    status = Column(String(30), default="open", nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    user = relationship("User", back_populates="found_items")
    matches = relationship("Match", back_populates="found_item", cascade="all, delete-orphan")
