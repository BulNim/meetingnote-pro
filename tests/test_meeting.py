from backend import config
from tests.conftest import MP3, MP4, WAV, Api, Classified, TodoItem, assert_error


def test_list_fields_order_and_counts(client, team, fake):
    owner = team["owner"]
    fake.result = Classified(summary="요약", decisions=["하나", "", "둘"],
                             todos=[TodoItem(what="정리", assignee="박과장", due="금요일"), TodoItem(what="조사")])
    owner.new_meeting(title="옛 회의", met_at="2026-09-10T00:00:00Z")
    owner.new_meeting(title="새 회의", met_at="2026-09-24T05:00:00Z")
    rows = owner.get(f"/api/teams/{owner.team_id}/meetings").json()
    assert [r["title"] for r in rows] == ["새 회의", "옛 회의"]
    r = rows[0]
    assert set(r) == {"id", "title", "met_at", "attendees", "summary", "created_at",
                      "todo_done_count", "todo_total_count", "decision_count"}
    assert r["decision_count"] == 2 and r["todo_total_count"] == 2 and r["todo_done_count"] == 0
    assert r["met_at"] == "2026-09-24T05:00:00Z"


def test_empty_and_search(client, team, fake):
    owner = team["owner"]
    url = f"/api/teams/{owner.team_id}/meetings"
    assert owner.get(url).json() == []
    owner.new_meeting(title="배포 환경 점검", attendees="박과장, 최선임", body="예산 이야기", met_at="2026-09-18T01:30:00Z")
    owner.new_meeting(title="기획 킥오프", attendees="김대리", met_at="2026-09-10T00:00:00Z")
    assert [m["title"] for m in owner.get(url, params={"q": "배포"}).json()] == ["배포 환경 점검"]
    assert [m["title"] for m in owner.get(url, params={"q": "최선임"}).json()] == ["배포 환경 점검"]
    r = owner.get(url, params={"q": "예산"})  # 본문만 일치
    assert r.status_code == 200 and r.json() == []
    assert [m["title"] for m in owner.get(url, params={"from": "2026-09-15", "to": "2026-09-30"}).json()] == ["배포 환경 점검"]
    assert [m["title"] for m in owner.get(url, params={"to": "2026-09-10"}).json()] == ["기획 킥오프"]
    assert_error(owner.get(url, params={"from": "9월"}), 400, "VALIDATION_ERROR")


def test_upload_ok_and_formats(client, team, fake):
    owner = team["owner"]
    r = owner.post("/api/upload", files={"file": ("회의_녹음.wav", WAV, "audio/wav")})
    assert r.status_code == 200 and r.json() == {"body": fake.body}
    assert owner.post("/api/upload", files={"file": ("a.mp3", MP3, "audio/mpeg")}).status_code == 200
    assert_error(owner.post("/api/upload", files={"file": ("회의_녹화.mp4", MP4, "video/mp4")}), 415, "UNSUPPORTED_MEDIA_TYPE")
    # 확장자만 바꾼 파일
    assert_error(owner.post("/api/upload", files={"file": ("a.wav", MP4, "audio/wav")}), 415, "UNSUPPORTED_MEDIA_TYPE")
    # 업로드는 회의록을 저장하지 않음
    assert owner.get(f"/api/teams/{owner.team_id}/meetings").json() == []


def test_upload_size_limit(client, team, fake, monkeypatch):
    owner = team["owner"]
    monkeypatch.setenv("VERCEL", "1")
    assert config.upload_max() == int(4.5 * config.MB)
    big = WAV + b"\x00" * (int(4.5 * config.MB) + 1)
    assert_error(owner.post("/api/upload", files={"file": ("big.wav", big, "audio/wav")}), 400, "VALIDATION_ERROR")
    monkeypatch.delenv("VERCEL")
    assert config.upload_max() == 20 * config.MB
    assert owner.post("/api/upload", files={"file": ("big.wav", big, "audio/wav")}).status_code == 200


def test_transcribe_fail_502(client, team, fake):
    fake.fail_transcribe = True
    assert_error(team["owner"].post("/api/upload", files={"file": ("a.wav", WAV, "audio/wav")}), 502, "VALIDATION_ERROR")


def test_real_gemini_without_key_is_502(client, team, monkeypatch):
    """가짜를 걷어 내고 키를 비우면 공급자를 부르지 않고 502."""
    from backend import gemini
    from tests.conftest import REAL_TRANSCRIBE
    monkeypatch.setattr(gemini, "transcribe", REAL_TRANSCRIBE)
    monkeypatch.setenv("GEMINI_API_KEY", "")
    r = team["owner"].post("/api/upload", files={"file": ("a.wav", WAV, "audio/wav")})
    assert_error(r, 502, "VALIDATION_ERROR")
    assert "GEMINI_API_KEY" in r.json()["msg"]


def test_save_requires_fields_and_classify_fail(client, team, fake):
    owner = team["owner"]
    url = f"/api/teams/{owner.team_id}/meetings"
    assert_error(owner.post(url, json={"title": "t", "met_at": "2026-09-24T05:00:00Z", "body": " "}), 400, "VALIDATION_ERROR")
    assert_error(owner.post(url, json={"title": "t", "met_at": "어제", "body": "b"}), 400, "VALIDATION_ERROR")
    fake.fail_classify = True
    assert_error(owner.post(url, json={"title": "t", "met_at": "2026-09-24T05:00:00Z", "body": "b"}), 502, "VALIDATION_ERROR")
    assert owner.get(url).json() == []


def test_assignee_matching_and_activities(client, team, fake):
    owner = team["owner"]
    fake.result = Classified(summary="s", decisions=[], todos=[
        TodoItem(what="목록 정리", assignee="이주임님", due="다음 주 금요일"),
        TodoItem(what="배포 확인", assignee=" 박 과장 ", due=""),
        TodoItem(what="인터뷰", assignee="홍길동", due="미정"),
    ])
    m = owner.new_meeting()
    todos = {t["what"]: t for t in m["todos"]}
    assert todos["목록 정리"]["assignee_name"] == "이주임" and todos["목록 정리"]["due_text"] == "다음 주 금요일"
    assert todos["배포 확인"]["assignee_name"] == "박과장"
    assert todos["인터뷰"]["assignee_id"] is None
    kinds = [a["kind"] for a in owner.get("/api/me/activities").json()]
    assert kinds.count("meeting_add") == 1 and kinds.count("todo_assign") == 2
    assert fake.calls[-1][0] == "classify" and set(fake.calls[-1][1]) == {"김대리", "박과장", "이주임"}


def test_detail_and_edit_keeps_parts(client, team, fake):
    owner, park = team["owner"], team["park"]
    fake.result = Classified(summary="요약", decisions=["결정"], todos=[TodoItem(what="일", assignee="박과장")])
    m = owner.new_meeting(body="원래 본문")
    d = owner.get(f"/api/meetings/{m['id']}").json()
    assert d["body"] == "원래 본문" and d["can_edit"] is True and len(d["todos"]) == 1 and d["decisions"] == "결정"
    assert park.get(f"/api/meetings/{m['id']}").json()["can_edit"] is False
    calls = len(fake.calls)
    r = owner.put(f"/api/meetings/{m['id']}", json={"body": "고친 본문", "title": "새 제목"})
    assert r.status_code == 200 and r.json()["body"] == "고친 본문" and r.json()["summary"] == "요약"
    assert len(fake.calls) == calls  # 다시 돌리지 않음
    assert_error(park.put(f"/api/meetings/{m['id']}", json={"title": "x"}), 403, "FORBIDDEN")


def test_owner_can_edit_others_meeting(client, team, fake):
    owner, park = team["owner"], team["park"]
    m = park.new_meeting()
    assert owner.get(f"/api/meetings/{m['id']}").json()["can_edit"] is True
    assert owner.put(f"/api/meetings/{m['id']}", json={"title": "owner 수정"}).status_code == 200


def test_delete_cascades(client, team, fake):
    owner, park = team["owner"], team["park"]
    fake.result = Classified(summary="s", decisions=[], todos=[TodoItem(what="일", assignee="박과장")])
    m = owner.new_meeting()
    park.post(f"/api/meetings/{m['id']}/comments", json={"content": "의견"})
    assert_error(park.delete(f"/api/meetings/{m['id']}"), 403, "FORBIDDEN")
    assert owner.delete(f"/api/meetings/{m['id']}").status_code == 204
    assert owner.get(f"/api/teams/{owner.team_id}/todos").json() == []
    assert_error(owner.get(f"/api/meetings/{m['id']}"), 404, "MEETING_NOT_FOUND")


def test_other_team_meeting_is_404(client, team, fake):
    m = team["owner"].new_meeting()
    other = Api(client, "남의팀")
    other.make_team("다른팀")
    assert_error(other.get(f"/api/meetings/{m['id']}"), 404, "MEETING_NOT_FOUND")
    assert_error(other.get(f"/api/teams/{team['owner'].team_id}/meetings"), 403, "FORBIDDEN")
    assert_error(team["owner"].get("/api/meetings/99"), 404, "MEETING_NOT_FOUND")


# ── modify-todo-due-date ──
def test_save_resolves_due_from_meeting_day(client, team, fake):
    owner = team["owner"]
    fake.result = Classified(summary="s", decisions=[], todos=[
        TodoItem(what="목록 정리", assignee="이주임", due="다음 주 금요일"),
        TodoItem(what="조사", assignee="", due="내일"),
        TodoItem(what="인터뷰", assignee="", due="이번 주 안"),
    ])
    m = owner.new_meeting(met_at="2026-11-11T23:30:00Z")  # 한국 11-12(목) 08:30
    got = {t["what"]: (t["due_text"], t["due_date"]) for t in m["todos"]}
    assert got == {"목록 정리": ("다음 주 금요일", "2026-11-20"), "조사": ("내일", "2026-11-13"), "인터뷰": ("이번 주 안", None)}


def test_met_at_change_recomputes_due(client, team, fake):
    owner = team["owner"]
    fake.result = Classified(summary="s", decisions=[], todos=[TodoItem(what="일", due="내일")])
    m = owner.new_meeting(met_at="2026-11-12T05:00:00Z")
    assert m["todos"][0]["due_date"] == "2026-11-13"
    r = owner.put(f"/api/meetings/{m['id']}", json={"title": "제목만"}).json()
    assert r["todos"][0]["due_date"] == "2026-11-13"
    r = owner.put(f"/api/meetings/{m['id']}", json={"met_at": "2026-11-19T05:00:00Z"}).json()
    assert r["todos"][0]["due_date"] == "2026-11-20" and r["todos"][0]["due_text"] == "내일"
