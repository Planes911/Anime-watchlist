"""Personalised recommendations from the user's own history (requires a valid token)."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Anime, Review, User, Watch_Progress, Watchlist_Item
from app.schemas import Anime_Out, Recommendation_Out
from app.services.recommender import LIKED_MIN_RATING, recommend

router = APIRouter(prefix="/api/recommendations", tags=["Recommendations"], dependencies=[Depends(get_current_user)])

@router.get("", response_model=list[Recommendation_Out])
def get_recommendations(
    limit: int = Query(5, ge=1, le=20, description="Maksimal jumlah rekomendasi"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # The user id always comes from the verified token.
    reviews = db.scalars(select(Review).where(Review.user_id == user.id)).all()
    seen_ids = {r.anime_id for r in reviews}
    seen_ids |= set(db.scalars(select(Watchlist_Item.anime_id).where(Watchlist_Item.user_id == user.id)))
    seen_ids |= set(db.scalars(select(Watch_Progress.anime_id).where(Watch_Progress.user_id == user.id)))

    liked = [
        {"title": r.anime.title, "genres": [g.name for g in r.anime.genres],
         "studio": r.anime.studio, "user_rating": r.rating}
        for r in reviews if r.rating >= LIKED_MIN_RATING
    ]
    unseen = db.scalars(select(Anime).where(Anime.id.not_in(seen_ids)).order_by(Anime.id)).all()
    candidates = [
        {"id": a.id, "title": a.title, "genres": [g.name for g in a.genres], "studio": a.studio, "rating": a.rating}
        for a in unseen
    ]

    by_id = {a.id: a for a in unseen}
    return [
        Recommendation_Out(anime=Anime_Out.from_model(by_id[item["anime_id"]]), score=item["score"], reason=item["reason"])
        for item in recommend(liked, candidates, limit)
    ]