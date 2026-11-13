"""활동 기록 2개 - 팀 활동 · 내 활동. 최신 순 50건."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import config
from ..db import get_db
from ..models import Activity, User
from ..security import current_user, require_member
from ..serial import activity_out

router = APIRouter(tags=["activity"])


@router.get("/api/teams/{team_id}/activities", summary="팀 활동 - 최신 순 50건")
def team_activities(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    rows = db.scalars(select(Activity).where(Activity.team_id == team_id)
                      .order_by(Activity.created_at.desc(), Activity.id.desc()).limit(config.ACTIVITY_LIMIT)).all()
    return [activity_out(db, a) for a in rows]


@router.get("/api/me/activities", summary="내 활동 - 내가 한 것만, 최신 순 50건")
def my_activities(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(Activity).where(Activity.actor_id == user.id)
                      .order_by(Activity.created_at.desc(), Activity.id.desc()).limit(config.ACTIVITY_LIMIT)).all()
    return [activity_out(db, a) for a in rows]
