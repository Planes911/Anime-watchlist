"""
Create the database tables and seed the initial animes.

Run from the backend/ folder:  python -m app.seed
Safe to run repeatedly (idempotent): animes that already exist are skipped.
"""

import json
import os
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models import Genre, Anime
from app.database import Base, engine, SessionLocal

def find_animes_json() -> Path:
    """Locate anime.json: env override first, then backend/data/, then <repo>/data/."""
    here = Path(__file__).resolve()
    candidates = [
        os.environ.get("ANIME_JSON_PATH"),
        here.parents[1] / "data" / "anime.json",  # backend/data/anime.json
        here.parents[2] / "data" / "anime.json",  # <repo>/data/anime.json (starter pack layout)
    ]
    for c in candidates:
        if c and Path(c).is_file():
            return Path(c)
    raise FileNotFoundError("anime.json tidak ditemukan. Set ANIME_JSON_PATH atau letakkan di <repo>/data/.")

def load_animes_json(path: Path | None = None) -> list[dict]:
    """Read the seed animes from the JSON file shipped with the starter pack."""
    with open(path or find_animes_json(), encoding="utf-8") as f:
        return json.load(f)
    
def seed_animes(db: Session, animes: list[dict]):
    """Insert the animes that are not in the database yet.

    Returns the number of newly created animes (0 when everything already exists).
    """
    existing_ids = set(db.scalars(select(Anime.id)).all())
    # Cache genres by name so each genre row is created only once.
    genre_cache = {g.name: g for g in db.scalars(select(Genre)).all()}
    created = 0

    for item in animes:
        if item["id"] in existing_ids:
            continue
        genres = []
        for name in item["genres"]:
            genre = genre_cache.get(name)
            if genre is None:
                genre = Genre(name=name)
                db.add(genre)
                genre_cache[name] = genre
            genres.append(genre)
        db.add(
            Anime(
                id=item["id"], title=item["title"], year=item["year"], studio=item["studio"],
                rating=item["rating"], episodes=item["episodes"], synopsis=item["synopsis"],
                poster_url=item["poster_url"], cast_members=item["cast"], genres=genres,
            )
        )
        created += 1
    db.commit()
    return created

def sync_postgres_sequence(db: Session) -> None:
    """Align PostgreSQL's id sequence with the seeded rows.

    Seeding inserts explicit ids (1..N), which does not advance the sequence; without
    this, the next auto-generated id would collide with an existing primary key.
    """
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text(
            "SELECT setval(pg_get_serial_sequence('animes', 'id'), COALESCE((SELECT MAX(id) FROM animes), 1))"
        ))
        db.commit()
        
def main() -> None:
    """Create missing tables, then seed the animes."""
    # create_all only creates missing tables and never alters existing ones. For schema changes in
    # production, use a migration tool such as Alembic.
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        created = seed_animes(db, load_animes_json())
        sync_postgres_sequence(db)
        total = db.scalar(select(func.count()).select_from(Anime))
    print(f"Seed selesai: {created} anime baru ditambahkan, total {total} anime di database.")

if __name__ == "__main__":
    main()