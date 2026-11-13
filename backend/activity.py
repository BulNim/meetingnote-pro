"""활동 기록 - kind 5종만 남기고, 화면이 그대로 그릴 완성 문장을 서버가 만든다."""
from sqlalchemy.orm import Session

from .models import Activity

KINDS = ("meeting_add", "todo_assign", "todo_done", "comment_add", "member_join")


def text_for(kind: str, **kw: str) -> str:
    if kind == "meeting_add":
        return f"회의록 「{kw['title']}」 등록"
    if kind == "todo_assign":
        return f"할 일 「{kw['what']}」를 {kw['assignee']}에게 배정"
    if kind == "todo_done":
        return f"할 일 「{kw['what']}」 완료"
    if kind == "comment_add":
        return f"회의록 「{kw['title']}」에 댓글 작성"
    if kind == "member_join":
        return "초대코드로 합류"
    raise ValueError(f"활동 kind 는 5종뿐: {kind}")


def record(db: Session, team_id: int, actor_id: int, kind: str, **kw: str) -> Activity:
    if kind not in KINDS:
        raise ValueError(f"활동 kind 는 5종뿐: {kind}")
    a = Activity(team_id=team_id, actor_id=actor_id, kind=kind, target=text_for(kind, **kw))
    db.add(a)
    return a
