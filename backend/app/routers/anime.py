"""Anime catalogue endpoints plus the AI recommendation endpoint."""

import random
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.errors import Api_Error
from app.models import Genre, Anime
from app.schemas import Anime_Out

router = APIRouter(prefix="/api/anime", tags=["Anime"])
logger = logging.getLogger("animelog")

def _escape_like(text: str) -> str:
    """Escape LIKE wildcards so user input is matched literally (searching for '%' finds nothing)."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

@router.get("", response_model=list[Anime_Out])
def list_animes(
    genre: str | None = Query(None, max_length=50, description="Filter genre, mis. Sci-Fi"),
    search: str | None = Query(None, max_length=100, description="Cari di judul / studio"),
    shuffle: bool = Query(False, description="Acak urutan hasil"),
    db: Session = Depends(get_db),
):
    """List animes. Optional filters: genre (case-insensitive), search (title or studio), shuffle."""
    stmt = select(Anime).order_by(Anime.id)
    if genre:
        # EXISTS subquery on the many-to-many relation; the genre match is case-insensitive.
        stmt = stmt.where(Anime.genres.any(func.lower(Genre.name) == genre.strip().lower()))
    if search and search.strip():
        # Case-insensitive substring match on title or studio.
        pattern = f"%{_escape_like(search.strip())}%"
        stmt = stmt.where(
            or_(Anime.title.ilike(pattern, escape="\\"), Anime.studio.ilike(pattern, escape="\\"))
        )
    animes = list(db.scalars(stmt).all())
    if shuffle:
        random.shuffle(animes)
    return [Anime_Out.from_model(m) for m in animes]

@router.get("/{anime_id}", response_model=Anime_Out)
def get_anime(anime_id: int, db: Session = Depends(get_db)):
    """Return a single anime, or 404 if it does not exist."""
    anime = db.get(Anime, anime_id)
    if anime is None:
        raise Api_Error(404, "Anime tidak ditemukan.")
    return Anime_Out.from_model(anime)
