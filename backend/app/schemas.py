"""Request and response schemas. Input validation lives here (via Pydantic)."""

from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import Anime, Review, Watchlist_Item

def _strip(v):
    """Trim surrounding whitespace so a blank string cannot pass as a value."""
    return v.strip() if isinstance(v, str) else v

class Register_In(BaseModel):
    """Payload for POST /api/auth/register."""
    # Deliberately loose: the frontend derives a default username from the email address.
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    
    @field_validator("username", mode="before")
    @classmethod
    def strip_username(cls, v):
        return _strip(v)

    @field_validator("password")
    @classmethod
    def check_password_bytes(cls, v: str) -> str:
        # bcrypt only uses the first 72 BYTES, and non-ASCII characters take more than one byte.
        if len(v.encode("utf-8")) > 72:
            raise ValueError("password maksimal 72 byte")
        return v
    
class Login_In(BaseModel):
    """Payload for POST /api/auth/login."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    
class User_Out(BaseModel):
    """Public user data. Never includes the password hash."""
    # Lets Pydantic read values straight from ORM objects.
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: str
    created_at: datetime
    
class Token_Out(BaseModel):
    """Response of a successful login."""
    token: str
    token_type: str = "bearer"
    user: User_Out
    
class Anime_Out(BaseModel):
    """Anime as returned by the API. Genres and cast are plain lists, matching data/anime.json."""
    id: int
    title: str
    year: int
    studio: str
    genres: list[str]
    rating: float
    episodes: str
    synopsis: str
    poster_url: str
    cast: list[str]
    
    @classmethod
    def from_model(cls, m: Anime) -> "Anime_Out":
        """Build the API representation from an ORM anime (genre objects become plain names)."""
        return cls(
            id=m.id, title=m.title, year=m.year, studio=m.studio,
            genres=[g.name for g in m.genres], rating=m.rating, episodes=m.episodes,
            synopsis=m.synopsis, poster_url=m.poster_url, cast=list(m.cast_members or []),
        )
    
class Watchlist_Add_In(BaseModel):
    """Payload for POST /api/watchlist. The spec uses `animeId`; `anime_id` is accepted too."""
    anime_id: int = Field(gt=0, validation_alias=AliasChoices("animeId", "anime_id"))
    
class Watchlist_Out(BaseModel):
    """A watchlist entry together with its anime."""
    id: int
    anime_id: int
    created_at: datetime
    anime: Anime_Out

    @classmethod
    def from_model(cls, item: Watchlist_Item) -> "Watchlist_Out":
        return cls(id=item.id, anime_id=item.anime_id, created_at=item.created_at,
                   anime=Anime_Out.from_model(item.anime))
        
class Watched_In(BaseModel):
    """Payload for POST /api/watched: a 1-5 rating and a written review.

    The frontend sends the review as both `review` and `opinion`, so either key is accepted.
    """
    anime_id: int = Field(gt=0, validation_alias=AliasChoices("animeId", "anime_id"))
    rating: int = Field(ge=1, le=5)
    review: str = Field(min_length=1, max_length=2000, validation_alias=AliasChoices("review", "opinion"))

    @field_validator("review", mode="before")
    @classmethod
    def strip_review(cls, v):
        return _strip(v)
    
class Watched_Out(BaseModel):
    """A watched anime with the user's rating and review."""
    id: int
    anime_id: int
    rating: int
    review: str
    created_at: datetime
    anime: Anime_Out

    @classmethod
    def from_model(cls, r: Review) -> "Watched_Out":
        return cls(id=r.id, anime_id=r.anime_id, rating=r.rating, review=r.review,
                   created_at=r.created_at, anime=Anime_Out.from_model(r.anime))

class Message_Out(BaseModel):
    """Simple confirmation message."""
    message: str
    