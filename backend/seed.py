from __future__ import annotations

from datetime import date

from backend.database import Base, SessionLocal, engine
from backend.models import FoundItem, LostItem, User
from backend.services.ai_matching import get_matching_engine
from backend.services.auth_service import hash_password
from backend.services.storage import ensure_upload_dir


def seed() -> None:
    ensure_upload_dir()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "student@example.com").first()
        if user is None:
            user = User(name="Sample Student", email="student@example.com", hashed_password=hash_password("Password123!"))
            db.add(user)
            db.commit()
            db.refresh(user)

        lost = LostItem(
            user_id=user.id,
            item_name="Blue USB drive",
            category="Electronics",
            description="Small blue USB drive with a black lanyard.",
            date_lost=date.today(),
            location="Library study area",
            image_path=None,
            status="open",
        )
        found = FoundItem(
            user_id=user.id,
            description="A blue flash drive found near the library tables.",
            category="Electronics",
            date_found=date.today(),
            location="Library hallway",
            image_path=None,
            status="open",
        )

        engine = get_matching_engine()
        engine.build_lost_embeddings(lost)
        engine.build_found_embeddings(found)
        db.add_all([lost, found])
        db.commit()
        db.refresh(lost)
        db.refresh(found)
        engine.refresh_index(lost)
        engine.refresh_index(found)
        engine.find_matches_for_lost(db, lost)
        db.commit()
        print("Seed data created.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
