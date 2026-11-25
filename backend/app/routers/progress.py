"""Watch-progress endpoints: which anime the user is following and on which episode.

All of them require a valid token, and a user can only ever touch their own rows.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.errors import Api_Error
from app.models import Anime, User, Watch_Progress
from app.schemas import Message_Out, Progress_Out, Progress_Status, Progress_Update_In

router = APIRouter(prefix="/api/progress", tags=["Watch Progress"], dependencies=[Depends(get_current_user)])

@router.get("", response_model=list[Progress_Out])
def list_progress(
    status: Progress_Status | None = Query(None, description="Filter: watching, completed, on_hold, dropped"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Watch_Progress).where(Watch_Progress.user_id == user.id)
    if status:
        stmt = stmt.where(Watch_Progress.status == status)
    stmt = stmt.order_by(Watch_Progress.updated_at.desc(), Watch_Progress.id.desc())
    return [Progress_Out.from_model(p) for p in db.scalars(stmt).all()]

@router.put("/{anime_id}", response_model=Progress_Out)
def set_progress(
    anime_id: int, payload: Progress_Update_In,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    anime = db.get(Anime, anime_id)
    if anime is None:
        raise Api_Error(404, "Anime tidak ditemukan.")
    if payload.current_episode > anime.total_episodes:
        raise Api_Error(400, f"Episode melebihi total episode anime ini ({anime.total_episodes}).")

    episode = anime.total_episodes if payload.status == "completed" else payload.current_episode
    item = db.scalar(
        select(Watch_Progress).where(Watch_Progress.user_id == user.id, Watch_Progress.anime_id == anime.id)
    )
    if item is None:
        item = Watch_Progress(user_id=user.id, anime_id=anime.id, status=payload.status, current_episode=episode)
        db.add(item)
    else:
        item.status = payload.status
        item.current_episode = episode
    try:
        db.commit()
    except IntegrityError:
        # Only reachable when two requests create the same (user, anime) row at the same time.
        db.rollback()
        raise Api_Error(409, "Progress untuk anime ini baru saja dibuat. Coba lagi.")
    db.refresh(item)
    return Progress_Out.from_model(item)

@router.delete("/{anime_id}", response_model=Message_Out)
def delete_progress(anime_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.scalar(
        select(Watch_Progress).where(Watch_Progress.user_id == user.id, Watch_Progress.anime_id == anime_id)
    )
    if item is None:
        # Someone else's entry also yields 404, so its existence is never revealed.
        raise Api_Error(404, "Progress anime ini tidak ditemukan.")
    db.delete(item)
    db.commit()
    return Message_Out(message="Progress dihapus.")