"""활동 기록 조회 - 팀 활동과 내 활동 (스토리보드 F-01, J)"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import ACTIVITY_LIMIT
from ..db import get_db
from ..deps import get_current_user, require_team
from ..models import Activity, User
from ..util import iso

router = APIRouter(prefix="/api", tags=["activity"])


def _rows(db: Session, query) -> list[dict]:
    rows = (
        query.join(User, User.id == Activity.actor_id)
        .with_entities(Activity, User.name)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
        .limit(ACTIVITY_LIMIT)
        .all()
    )
    return [
        {"id": a.id, "kind": a.kind, "actor_name": name, "text": a.target, "created_at": iso(a.created_at)}
        for a, name in rows
    ]


@router.get("/teams/{team_id}/activities", summary="팀 활동 기록 (최근 50건)")
def team_activities(team_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    team, _ = require_team(db, user, team_id)
    return _rows(db, db.query(Activity).filter(Activity.team_id == team.id))


@router.get("/me/activities", summary="내 활동 기록 (최근 50건)")
def my_activities(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _rows(db, db.query(Activity).filter(Activity.actor_id == user.id))
