"""활동 기록 - 5종만 남긴다. 문장은 서버가 만든 완성 문장 (화면은 그대로 그림)"""
from sqlalchemy.orm import Session

from ..models import ACTIVITY_KINDS, Activity


def record(db: Session, team_id: int, actor_id: int, kind: str, text: str) -> Activity:
    """같은 트랜잭션 안에서 부른다. 커밋은 호출한 쪽이 한다"""
    assert kind in ACTIVITY_KINDS, f"정의되지 않은 활동 종류: {kind}"
    activity = Activity(team_id=team_id, actor_id=actor_id, kind=kind, target=text)
    db.add(activity)
    return activity


def meeting_added(title: str) -> str:
    return f"회의록 「{title}」 등록"


def todo_assigned(what: str, assignee_name: str) -> str:
    return f"할 일 「{what}」를 {assignee_name}에게 배정"


def todo_done(what: str) -> str:
    return f"할 일 「{what}」 완료"


def comment_added(title: str) -> str:
    return f"회의록 「{title}」에 댓글 작성"


def member_joined() -> str:
    return "초대코드로 합류"
