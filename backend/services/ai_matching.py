from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from difflib import SequenceMatcher
from threading import Lock
from typing import TYPE_CHECKING, Any, Iterable

import numpy as np
from sqlalchemy.orm import Session, joinedload

from backend.config import settings
from backend.models import FoundItem, LostItem, Match
from backend.services.storage import resolve_upload_path

if TYPE_CHECKING:
    import faiss


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lazy dependency imports
# ---------------------------------------------------------------------------

def _faiss():
    import faiss

    return faiss


def _torch():
    import torch

    return torch


def _cv2():
    import cv2

    return cv2


def _open_clip():
    import open_clip

    return open_clip


def _sentence_transformers():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------

def _normalize(vector: np.ndarray | None) -> np.ndarray | None:
    """
    Normalize an embedding as a one-dimensional float32 NumPy array.

    Returns None safely when embedding generation failed.
    """
    if vector is None:
        return None

    try:
        array = np.asarray(vector, dtype=np.float32).reshape(-1)

        if array.size == 0:
            return None

        norm = np.linalg.norm(array)

        if norm == 0:
            return array

        return array / norm

    except Exception:
        logger.exception("Failed to normalize embedding")
        return None


def _serialize_embedding(vector: np.ndarray | None) -> str | None:
    """Serialize an embedding for storage in SQLite."""
    if vector is None:
        return None

    try:
        array = np.asarray(vector, dtype=np.float32).reshape(-1)

        if array.size == 0:
            return None

        return json.dumps(array.tolist())

    except Exception:
        logger.exception("Failed to serialize embedding")
        return None


def _deserialize_embedding(value: str | None) -> np.ndarray | None:
    """Deserialize a stored embedding safely."""
    if not value:
        return None

    try:
        data = np.asarray(json.loads(value), dtype=np.float32).reshape(-1)

        if data.size == 0:
            return None

        return _normalize(data)

    except (TypeError, ValueError, json.JSONDecodeError):
        logger.exception("Failed to deserialize embedding")
        return None


def _cosine_similarity(
    left: np.ndarray | None,
    right: np.ndarray | None,
) -> float | None:
    if left is None or right is None:
        return None

    try:
        left_vector = _normalize(left)
        right_vector = _normalize(right)

        if left_vector is None or right_vector is None:
            return None

        if left_vector.shape != right_vector.shape:
            return None

        score = float(np.dot(left_vector, right_vector))

        return max(-1.0, min(1.0, score))

    except Exception:
        logger.exception("Failed to calculate cosine similarity")
        return None


def _compose_text(
    item_name: str | None,
    category: str | None,
    description: str | None,
) -> str:
    pieces = [
        piece.strip()
        for piece in [item_name, category, description]
        if piece and piece.strip()
    ]

    return " | ".join(pieces)


def _normalize_text(value: str | None) -> str:
    return " ".join((value or "").lower().split())


# ---------------------------------------------------------------------------
# Match candidate
# ---------------------------------------------------------------------------

@dataclass
class MatchCandidate:
    item_id: int
    text_score: float | None
    image_score: float | None
    final_score: float


# ---------------------------------------------------------------------------
# Matching engine
# ---------------------------------------------------------------------------

class MatchingEngine:
    def __init__(self) -> None:
        self._lock = Lock()

        self._text_model = None
        self._clip_model = None
        self._clip_preprocess = None
        self._clip_tokenizer = None

        self._device = "cpu"

        self._text_dimension = 384
        self._image_dimension = 512

        self._lost_text_index: Any | None = None
        self._found_text_index: Any | None = None
        self._lost_image_index: Any | None = None
        self._found_image_index: Any | None = None

        self._ready = False
        self._fallback_mode = False

    # -----------------------------------------------------------------------
    # Model loading
    # -----------------------------------------------------------------------

    def _ensure_models(self) -> bool:
        """
        Load models lazily.

        Returns True when full AI models are available.
        Returns False when fallback matching must be used.
        """
        if self._fallback_mode:
            return False

        if self._text_model is None:
            try:
                sentence_transformer = _sentence_transformers()

                self._text_model = sentence_transformer(
                    "all-MiniLM-L6-v2"
                )

                dimension = (
                    self._text_model.get_sentence_embedding_dimension()
                )

                if dimension:
                    self._text_dimension = int(dimension)

                logger.info("Sentence Transformer model loaded successfully")

            except Exception:
                self._fallback_mode = True
                logger.exception(
                    "Failed to load Sentence Transformer; "
                    "using fallback text matching"
                )
                return False

        if self._clip_model is None or self._clip_preprocess is None:
            try:
                torch = _torch()
                open_clip = _open_clip()

                self._device = (
                    "cuda"
                    if torch.cuda.is_available()
                    else "cpu"
                )

                model, _, preprocess = (
                    open_clip.create_model_and_transforms(
                        "ViT-B-32",
                        pretrained="openai",
                    )
                )

                model = model.to(self._device)
                model.eval()

                self._clip_model = model
                self._clip_preprocess = preprocess
                self._clip_tokenizer = open_clip.get_tokenizer(
                    "ViT-B-32"
                )

                output_dimension = getattr(
                    model.visual,
                    "output_dim",
                    None,
                )

                if output_dimension:
                    self._image_dimension = int(output_dimension)

                logger.info(
                    "OpenCLIP model loaded successfully on %s",
                    self._device,
                )

            except Exception:
                # Text matching can still work even if image matching fails.
                logger.exception(
                    "Failed to load OpenCLIP image model; "
                    "continuing without image matching"
                )

                self._clip_model = None
                self._clip_preprocess = None
                self._clip_tokenizer = None

        return self._text_model is not None

    # -----------------------------------------------------------------------
    # FAISS index management
    # -----------------------------------------------------------------------

    def _create_index(self, dimension: int) -> Any | None:
        try:
            faiss = _faiss()

            return faiss.IndexIDMap2(
                faiss.IndexFlatIP(dimension)
            )

        except Exception:
            logger.exception(
                "Failed to create FAISS index with dimension %s",
                dimension,
            )
            return None

    def _reset_indexes(self) -> None:
        self._lost_text_index = self._create_index(
            self._text_dimension
        )

        self._found_text_index = self._create_index(
            self._text_dimension
        )

        self._lost_image_index = self._create_index(
            self._image_dimension
        )

        self._found_image_index = self._create_index(
            self._image_dimension
        )

    def bootstrap(self, db: Session) -> None:
        """Rebuild FAISS indexes from database embeddings."""
        with self._lock:
            if self._ready:
                return

            models_available = self._ensure_models()

            if not models_available:
                self._fallback_mode = True
                self._ready = True

                logger.warning(
                    "Matching engine started in fallback mode"
                )
                return

            self._reset_indexes()

            try:
                lost_items = db.query(LostItem).all()
                found_items = db.query(FoundItem).all()

                for item in lost_items:
                    self._index_lost_item(item)

                for item in found_items:
                    self._index_found_item(item)

                self._ready = True

                logger.info(
                    "Matching engine indexes created: "
                    "%s lost items and %s found items",
                    len(lost_items),
                    len(found_items),
                )

            except Exception:
                logger.exception(
                    "Failed to rebuild FAISS indexes; "
                    "using fallback matching"
                )

                self._fallback_mode = True
                self._ready = True

    # -----------------------------------------------------------------------
    # Embedding generation
    # -----------------------------------------------------------------------

    def _text_embedding(
        self,
        text: str,
    ) -> np.ndarray | None:
        if not text.strip():
            return None

        if not self._ensure_models():
            return None

        if self._text_model is None:
            return None

        try:
            embedding = self._text_model.encode(
                [text],
                normalize_embeddings=True,
            )

            return _normalize(
                np.asarray(
                    embedding[0],
                    dtype=np.float32,
                )
            )

        except Exception:
            logger.exception(
                "Failed to generate text embedding"
            )
            return None

    def _prepare_image(
        self,
        image_path: str,
    ) -> Any | None:
        try:
            cv2 = _cv2()
            from PIL import Image

            image = cv2.imread(image_path)

            if image is None:
                logger.warning(
                    "OpenCV could not read image: %s",
                    image_path,
                )
                return None

            image = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2RGB,
            )

            return Image.fromarray(image)

        except Exception:
            logger.exception(
                "Failed to process image: %s",
                image_path,
            )
            return None

    def _image_embedding(
        self,
        image_path: str | None,
    ) -> np.ndarray | None:
        if not image_path:
            return None

        # Try loading image model, but do not crash if unavailable.
        self._ensure_models()

        if (
            self._clip_model is None
            or self._clip_preprocess is None
        ):
            return None

        try:
            resolved_path = resolve_upload_path(image_path)

            if resolved_path is None:
                logger.warning(
                    "Unable to resolve image path: %s",
                    image_path,
                )
                return None

            image = self._prepare_image(
                str(resolved_path)
            )

            if image is None:
                return None

            torch = _torch()

            tensor = (
                self._clip_preprocess(image)
                .unsqueeze(0)
                .to(self._device)
            )

            with torch.no_grad():
                features = self._clip_model.encode_image(
                    tensor
                )

                features = features / features.norm(
                    dim=-1,
                    keepdim=True,
                )

            result = (
                features[0]
                .detach()
                .cpu()
                .numpy()
                .astype(np.float32)
            )

            return _normalize(result)

        except Exception:
            logger.exception(
                "Failed to generate image embedding for %s",
                image_path,
            )
            return None

    def build_lost_embeddings(
        self,
        item: LostItem,
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        """
        Generate and store embeddings for a lost item.

        A missing or invalid image will not stop the item from being saved.
        """
        text = _compose_text(
            item.item_name,
            item.category,
            item.description,
        )

        text_embedding = self._text_embedding(text)

        image_embedding = None

        if item.image_path:
            try:
                image_embedding = self._image_embedding(
                    item.image_path
                )
            except Exception:
                logger.exception(
                    "Image embedding failed for lost item %s",
                    getattr(item, "id", None),
                )
                image_embedding = None

        item.embedding_text = _serialize_embedding(
            text_embedding
        )

        item.embedding_image = _serialize_embedding(
            image_embedding
        )

        return text_embedding, image_embedding

    def build_found_embeddings(
        self,
        item: FoundItem,
    ) -> tuple[np.ndarray | None, np.ndarray | None]:
        """
        Generate and store embeddings for a found item.

        A missing or invalid image will not stop the item from being saved.
        """
        text = _compose_text(
            "Found item",
            item.category,
            item.description,
        )

        text_embedding = self._text_embedding(text)

        image_embedding = None

        if item.image_path:
            try:
                image_embedding = self._image_embedding(
                    item.image_path
                )
            except Exception:
                logger.exception(
                    "Image embedding failed for found item %s",
                    getattr(item, "id", None),
                )
                image_embedding = None

        item.embedding_text = _serialize_embedding(
            text_embedding
        )

        item.embedding_image = _serialize_embedding(
            image_embedding
        )

        return text_embedding, image_embedding

    # -----------------------------------------------------------------------
    # Index item helpers
    # -----------------------------------------------------------------------

    def _index_lost_item(
        self,
        item: LostItem,
    ) -> None:
        text_embedding = _deserialize_embedding(
            item.embedding_text
        )

        image_embedding = _deserialize_embedding(
            item.embedding_image
        )

        if (
            text_embedding is not None
            and self._lost_text_index is not None
            and text_embedding.size
            == self._text_dimension
        ):
            self._lost_text_index.add_with_ids(
                text_embedding
                .reshape(1, -1)
                .astype(np.float32),
                np.array(
                    [item.id],
                    dtype=np.int64,
                ),
            )

        if (
            image_embedding is not None
            and self._lost_image_index is not None
            and image_embedding.size
            == self._image_dimension
        ):
            self._lost_image_index.add_with_ids(
                image_embedding
                .reshape(1, -1)
                .astype(np.float32),
                np.array(
                    [item.id],
                    dtype=np.int64,
                ),
            )

    def _index_found_item(
        self,
        item: FoundItem,
    ) -> None:
        text_embedding = _deserialize_embedding(
            item.embedding_text
        )

        image_embedding = _deserialize_embedding(
            item.embedding_image
        )

        if (
            text_embedding is not None
            and self._found_text_index is not None
            and text_embedding.size
            == self._text_dimension
        ):
            self._found_text_index.add_with_ids(
                text_embedding
                .reshape(1, -1)
                .astype(np.float32),
                np.array(
                    [item.id],
                    dtype=np.int64,
                ),
            )

        if (
            image_embedding is not None
            and self._found_image_index is not None
            and image_embedding.size
            == self._image_dimension
        ):
            self._found_image_index.add_with_ids(
                image_embedding
                .reshape(1, -1)
                .astype(np.float32),
                np.array(
                    [item.id],
                    dtype=np.int64,
                ),
            )

    def refresh_index(self, item: LostItem | FoundItem) -> None:
        if self._fallback_mode:
            return

        if not self._ready:
            return

        try:
            with self._lock:
                if isinstance(item, LostItem):
                    self._index_lost_item(item)

                elif isinstance(item, FoundItem):
                    self._index_found_item(item)

        except Exception:
            logger.exception(
                "Failed to add item %s to FAISS index",
                getattr(item, "id", None),
            )

    def _candidate_ids(
        self,
        index: Any | None,
        vector: np.ndarray | None,
    ) -> list[int]:
        if (
            self._fallback_mode
            or index is None
            or vector is None
            or index.ntotal == 0
        ):
            return []

        try:
            query = (
                vector
                .reshape(1, -1)
                .astype(np.float32)
            )

            limit = min(
                int(settings.top_k),
                int(index.ntotal),
            )

            _, ids = index.search(
                query,
                limit,
            )

            return [
                int(candidate_id)
                for candidate_id in ids[0]
                if candidate_id != -1
            ]

        except Exception:
            logger.exception(
                "FAISS candidate search failed"
            )
            return []

    # -----------------------------------------------------------------------
    # Scoring
    # -----------------------------------------------------------------------

    def _final_score(
        self,
        text_score: float | None,
        image_score: float | None,
    ) -> float:
        if (
            text_score is not None
            and image_score is not None
        ):
            total_weight = (
                settings.text_weight
                + settings.image_weight
            )

            if total_weight <= 0:
                return 0.0

            return (
                (
                    settings.text_weight
                    * text_score
                )
                + (
                    settings.image_weight
                    * image_score
                )
            ) / total_weight

        if text_score is not None:
            return text_score

        if image_score is not None:
            return image_score

        return 0.0

    def _candidate_from_found(
        self,
        query_text: np.ndarray,
        query_image: np.ndarray | None,
        found_item: FoundItem,
    ) -> MatchCandidate:
        candidate_text = _deserialize_embedding(
            found_item.embedding_text
        )

        candidate_image = _deserialize_embedding(
            found_item.embedding_image
        )

        text_score = _cosine_similarity(
            query_text,
            candidate_text,
        )

        image_score = (
            _cosine_similarity(
                query_image,
                candidate_image,
            )
            if query_image is not None
            and candidate_image is not None
            else None
        )

        final_score = self._final_score(
            text_score,
            image_score,
        )

        return MatchCandidate(
            item_id=found_item.id,
            text_score=text_score,
            image_score=image_score,
            final_score=final_score,
        )

    def _candidate_from_lost(
        self,
        query_text: np.ndarray,
        query_image: np.ndarray | None,
        lost_item: LostItem,
    ) -> MatchCandidate:
        candidate_text = _deserialize_embedding(
            lost_item.embedding_text
        )

        candidate_image = _deserialize_embedding(
            lost_item.embedding_image
        )

        text_score = _cosine_similarity(
            query_text,
            candidate_text,
        )

        image_score = (
            _cosine_similarity(
                query_image,
                candidate_image,
            )
            if query_image is not None
            and candidate_image is not None
            else None
        )

        final_score = self._final_score(
            text_score,
            image_score,
        )

        return MatchCandidate(
            item_id=lost_item.id,
            text_score=text_score,
            image_score=image_score,
            final_score=final_score,
        )

    def _candidate_score(
        self,
        query_text: np.ndarray,
        query_image: np.ndarray | None,
        item: LostItem | FoundItem,
    ) -> MatchCandidate:
        if isinstance(item, FoundItem):
            return self._candidate_from_found(
                query_text,
                query_image,
                item,
            )

        return self._candidate_from_lost(
            query_text,
            query_image,
            item,
        )

    def _category_similarity(
        self,
        left: str | None,
        right: str | None,
    ) -> float:
        return SequenceMatcher(
            None,
            _normalize_text(left),
            _normalize_text(right),
        ).ratio()

    def _description_similarity(
        self,
        left: str | None,
        right: str | None,
    ) -> float:
        return SequenceMatcher(
            None,
            _normalize_text(left),
            _normalize_text(right),
        ).ratio()

    def _should_create_match(
        self,
        lost_item: LostItem,
        found_item: FoundItem,
        score: MatchCandidate,
    ) -> bool:
        category_similarity = (
            self._category_similarity(
                lost_item.category,
                found_item.category,
            )
        )

        description_similarity = (
            self._description_similarity(
                lost_item.description,
                found_item.description,
            )
        )

        # Strong category and description match.
        if (
            category_similarity >= 0.8
            and description_similarity >= 0.50
            and score.final_score
            >= min(settings.match_threshold, 0.60)
        ):
            return True

        # Very strong AI score.
        if (
            score.final_score
            >= min(
                0.90,
                settings.match_threshold + 0.10,
            )
            and description_similarity >= 0.40
        ):
            return True

        return False

    # -----------------------------------------------------------------------
    # Database helpers
    # -----------------------------------------------------------------------

    def _load_opposite_found_items(
        self,
        db: Session,
        ids: Iterable[int],
    ) -> list[FoundItem]:
        unique_ids = list(set(ids))

        if not unique_ids:
            return []

        return (
            db.query(FoundItem)
            .options(joinedload(FoundItem.user))
            .filter(
                FoundItem.id.in_(unique_ids),
                FoundItem.status == "open",
            )
            .all()
        )

    def _load_opposite_lost_items(
        self,
        db: Session,
        ids: Iterable[int],
    ) -> list[LostItem]:
        unique_ids = list(set(ids))

        if not unique_ids:
            return []

        return (
            db.query(LostItem)
            .options(joinedload(LostItem.user))
            .filter(
                LostItem.id.in_(unique_ids),
                LostItem.status == "open",
            )
            .all()
        )

    def _existing_match(
        self,
        db: Session,
        lost_item_id: int,
        found_item_id: int,
    ) -> Match | None:
        return (
            db.query(Match)
            .filter(
                Match.lost_item_id
                == lost_item_id,
                Match.found_item_id
                == found_item_id,
            )
            .first()
        )

    # -----------------------------------------------------------------------
    # Fallback matching
    # -----------------------------------------------------------------------

    def _fallback_text_score(
        self,
        left: str,
        right: str,
    ) -> float:
        normalized_left = _normalize_text(left)
        normalized_right = _normalize_text(right)

        if not normalized_left or not normalized_right:
            return 0.0

        return SequenceMatcher(
            None,
            normalized_left,
            normalized_right,
        ).ratio()

    def _fallback_match_score(
        self,
        lost_item: LostItem,
        found_item: FoundItem,
    ) -> float:
        lost_text = _compose_text(
            lost_item.item_name,
            lost_item.category,
            lost_item.description,
        )

        found_text = _compose_text(
            found_item.category,
            found_item.location,
            found_item.description,
        )

        description_score = self._fallback_text_score(
            lost_text,
            found_text,
        )

        category_score = self._category_similarity(
            lost_item.category,
            found_item.category,
        )

        location_score = self._fallback_text_score(
            lost_item.location or "",
            found_item.location or "",
        )

        return (
            0.65 * description_score
            + 0.25 * category_score
            + 0.10 * location_score
        )

    def _fallback_find_matches_for_lost(
        self,
        db: Session,
        lost_item: LostItem,
    ) -> list[Match]:
        candidates = (
            db.query(FoundItem)
            .options(joinedload(FoundItem.user))
            .filter(FoundItem.status == "open")
            .all()
        )

        created_matches: list[Match] = []

        for candidate in candidates:
            if self._existing_match(
                db,
                lost_item.id,
                candidate.id,
            ):
                continue

            score = self._fallback_match_score(
                lost_item,
                candidate,
            )

            category_similarity = (
                self._category_similarity(
                    lost_item.category,
                    candidate.category,
                )
            )

            if (
                category_similarity < 0.8
                or score < 0.45
            ):
                continue

            match = Match(
                lost_item_id=lost_item.id,
                found_item_id=candidate.id,
                text_score=score,
                image_score=None,
                final_score=score,
                status="pending",
            )

            db.add(match)
            created_matches.append(match)

            logger.info(
                "Fallback match created: "
                "lost=%s found=%s score=%.3f",
                lost_item.id,
                candidate.id,
                score,
            )

        db.flush()

        return created_matches

    def _fallback_find_matches_for_found(
        self,
        db: Session,
        found_item: FoundItem,
    ) -> list[Match]:
        candidates = (
            db.query(LostItem)
            .options(joinedload(LostItem.user))
            .filter(LostItem.status == "open")
            .all()
        )

        created_matches: list[Match] = []

        for candidate in candidates:
            if self._existing_match(
                db,
                candidate.id,
                found_item.id,
            ):
                continue

            score = self._fallback_match_score(
                candidate,
                found_item,
            )

            category_similarity = (
                self._category_similarity(
                    candidate.category,
                    found_item.category,
                )
            )

            if (
                category_similarity < 0.8
                or score < 0.45
            ):
                continue

            match = Match(
                lost_item_id=candidate.id,
                found_item_id=found_item.id,
                text_score=score,
                image_score=None,
                final_score=score,
                status="pending",
            )

            db.add(match)
            created_matches.append(match)

            logger.info(
                "Fallback match created: "
                "lost=%s found=%s score=%.3f",
                candidate.id,
                found_item.id,
                score,
            )

        db.flush()

        return created_matches

    # -----------------------------------------------------------------------
    # Match search
    # -----------------------------------------------------------------------

    def find_matches_for_lost(
        self,
        db: Session,
        lost_item: LostItem,
    ) -> list[Match]:
        if not self._ensure_ready(db):
            return self._fallback_find_matches_for_lost(
                db,
                lost_item,
            )

        query_text = _deserialize_embedding(
            lost_item.embedding_text
        )

        query_image = _deserialize_embedding(
            lost_item.embedding_image
        )

        if query_text is None:
            return self._fallback_find_matches_for_lost(
                db,
                lost_item,
            )

        try:
            candidates = (
                db.query(FoundItem)
                .options(joinedload(FoundItem.user))
                .filter(FoundItem.status == "open")
                .all()
            )

            created_matches: list[Match] = []

            for candidate in candidates:
                if self._existing_match(
                    db,
                    lost_item.id,
                    candidate.id,
                ):
                    continue

                score = self._candidate_score(
                    query_text,
                    query_image,
                    candidate,
                )

                if not self._should_create_match(
                    lost_item,
                    candidate,
                    score,
                ):
                    continue

                match = Match(
                    lost_item_id=lost_item.id,
                    found_item_id=candidate.id,
                    text_score=(
                        score.text_score
                        if score.text_score is not None
                        else 0.0
                    ),
                    image_score=score.image_score,
                    final_score=score.final_score,
                    status="pending",
                )

                db.add(match)
                created_matches.append(match)

                logger.info(
                    "AI match created: "
                    "lost=%s found=%s score=%.3f",
                    lost_item.id,
                    candidate.id,
                    score.final_score,
                )

            db.flush()

            return created_matches

        except Exception:
            logger.exception(
                "AI matching failed for lost item %s; "
                "using fallback matching",
                lost_item.id,
            )

            return self._fallback_find_matches_for_lost(
                db,
                lost_item,
            )

    def find_matches_for_found(
        self,
        db: Session,
        found_item: FoundItem,
    ) -> list[Match]:
        if not self._ensure_ready(db):
            return self._fallback_find_matches_for_found(
                db,
                found_item,
            )

        query_text = _deserialize_embedding(
            found_item.embedding_text
        )

        query_image = _deserialize_embedding(
            found_item.embedding_image
        )

        if query_text is None:
            return self._fallback_find_matches_for_found(
                db,
                found_item,
            )

        try:
            candidates = (
                db.query(LostItem)
                .options(joinedload(LostItem.user))
                .filter(LostItem.status == "open")
                .all()
            )

            created_matches: list[Match] = []

            for candidate in candidates:
                if self._existing_match(
                    db,
                    candidate.id,
                    found_item.id,
                ):
                    continue

                score = self._candidate_score(
                    query_text,
                    query_image,
                    candidate,
                )

                if not self._should_create_match(
                    candidate,
                    found_item,
                    score,
                ):
                    continue

                match = Match(
                    lost_item_id=candidate.id,
                    found_item_id=found_item.id,
                    text_score=(
                        score.text_score
                        if score.text_score is not None
                        else 0.0
                    ),
                    image_score=score.image_score,
                    final_score=score.final_score,
                    status="pending",
                )

                db.add(match)
                created_matches.append(match)

                logger.info(
                    "AI match created: "
                    "lost=%s found=%s score=%.3f",
                    candidate.id,
                    found_item.id,
                    score.final_score,
                )

            db.flush()

            return created_matches

        except Exception:
            logger.exception(
                "AI matching failed for found item %s; "
                "using fallback matching",
                found_item.id,
            )

            return self._fallback_find_matches_for_found(
                db,
                found_item,
            )

    def _ensure_ready(
        self,
        db: Session,
    ) -> bool:
        if self._ready:
            return not self._fallback_mode

        self.bootstrap(db)

        return (
            self._ready
            and not self._fallback_mode
        )


matching_engine = MatchingEngine()


def get_matching_engine() -> MatchingEngine:
    return matching_engine