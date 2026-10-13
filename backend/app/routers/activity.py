"""activity - 정의서 7절 Activity 2개. 근거: 스토리보드 F-01(team.html), J-07(profile.html)"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import activity_text, current_user, iso, require_member
from ..models import Activity, User

router = APIRouter(tags=["activity"])

LIMIT = 50


def _rows(db: Session, query) -> list[dict]:
    rows = query.order_by(Activity.created_at.desc(), Activity.id.desc()).limit(LIMIT).all()
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_({a.actor_id for a in rows} or {0})).all()}
    return [
        {
            "id": a.id,
            "kind": a.kind,
            "actor_name": names.get(a.actor_id),
            "text": activity_text(a.kind, names.get(a.actor_id, ""), a.target),
            "created_at": iso(a.created_at),
        }
        for a in rows
    ]


@router.get("/teams/{team_id}/activities", summary="팀 활동 기록 - 최신순 최근 50건")
def team_activities(team_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_member(db, user, team_id)
    return _rows(db, db.query(Activity).filter(Activity.team_id == team_id))


@router.get("/me/activities", summary="내 활동 기록 - 최신순 최근 50건")
def my_activities(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _rows(db, db.query(Activity).filter(Activity.actor_id == user.id))
