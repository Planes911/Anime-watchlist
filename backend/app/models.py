"""Database models (ERD overview)."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

# Association table for the many-to-many relation between animes and genres.
anime_genres = Table(
    "anime_genres",
    Base.metadata,
    Column("anime_id", ForeignKey("animes.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, index=True)
)

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    # Display name only (the frontend derives it from the email), so it is intentionally not unique.
    # Identity for login is the unique email.
    username: Mapped[str] = mapped_column(String(50))
    # Unique and indexed: login looks users up by email.
    email: Mapped[str] = mapped_column(String(300), unique=True, index=True)
    # bcrypt hash; the plain-text password is never stored.
    password_hash: Mapped[str] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

class Genre(Base):
    __tablename__ = "genres"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)

class Anime(Base):
    __tablename__ = "animes"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    year: Mapped[int] = mapped_column(Integer)
    studio: Mapped[str] = mapped_column(String(255))
    rating: Mapped[float] = mapped_column(Float)
    episodes: Mapped[str] = mapped_column(String(50))
    total_episodes: Mapped[int] = mapped_column(Integer)
    synopsis: Mapped[str] = mapped_column(Text)
    poster_url: Mapped[str] = mapped_column(Text)
    # The cast list is only displayed, never queried, so a JSON column is enough.
    cast_members: Mapped[list] = mapped_column(JSON, default=list)
    # Normalised many-to-many so genre filtering is a real query; selectin loading avoids N+1 queries.
    genres: Mapped[list["Genre"]] = relationship(
        secondary=anime_genres, order_by="Genre.name", lazy="selectin"
    )
    
class Watchlist_Item(Base):
    __tablename__ = "watchlists"
    
    # A anime can be on a user's watchlist only once. The database enforces it, so the rule also
    # holds for concurrent requests (the API turns the violation into a 409).
    __table_args__ = (UniqueConstraint("user_id", "anime_id", name="uq_watchlist_user_anime"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    anime_id: Mapped[int] = mapped_column(ForeignKey("animes.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    anime: Mapped["Anime"] = relationship(lazy="joined")

class Review(Base):
    __tablename__ = "reviews"
    # One review per user and anime. The CHECK constraint backs up the API validation, so an
    # invalid rating can never reach the table.
    __table_args__ = (
        UniqueConstraint("user_id", "anime_id", name="uq_review_user_anime"),
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_review_rating_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    anime_id: Mapped[int] = mapped_column(ForeignKey("animes.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    review: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    anime: Mapped["Anime"] = relationship(lazy="joined")
    
class Watch_Progress(Base):
    __tablename__ = "watch_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "anime_id", name="uq_progress_user_anime"),
        CheckConstraint("current_episode >= 0", name="ck_progress_episode_not_negative"),
        CheckConstraint("status IN ('watching', 'completed', 'on_hold', 'dropped')", name="ck_progress_status"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    anime_id: Mapped[int] = mapped_column(ForeignKey("animes.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(20))
    current_episode: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    anime: Mapped["Anime"] = relationship(lazy="joined")