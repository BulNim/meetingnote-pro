"""e2e 보충: 세션 만료 안내, 잘못된 초대코드 가입, member 권한 화면, 정원 초과, 로그인 실패"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(r"D:\meetingnote-pro")
sys.path.insert(0, str(ROOT / "backend"))
os.environ["MEETINGNOTE_SKIP_INIT"] = "1"
from app.security import create_token  # noqa: E402

import tempfile
SCRATCH = Path(tempfile.mkdtemp(prefix="mn-e2e-"))   # 임시 폴더(DB · 스크린샷)
SHOTS = SCRATCH / "shots"
SHOTS.mkdir(exist_ok=True)
DB = SCRATCH / "demo2.db"
PORT = 8767
BASE = f"http://127.0.0.1:{PORT}"
if DB.exists():
    DB.unlink()
env = dict(os.environ, DATABASE_URL=f"sqlite:///{DB.as_posix()}", PYTHONIOENCODING="utf-8")
env.pop("MEETINGNOTE_SKIP_INIT", None)
server = subprocess.Popen(
    [str(ROOT / ".venv/Scripts/python.exe"), "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--port", str(PORT)],
    cwd=ROOT, env=env, stdout=open(SCRATCH / "server2.log", "w"), stderr=subprocess.STDOUT)
results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(("PASS " if ok else "FAIL ") + name + (f"  {detail}" if detail else ""), flush=True)


def api(method, path, body=None, token=None):
    req = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


def signup(email, name):
    s, d = api("POST", "/api/auth/signup", {"email": email, "password": "password123", "name": name})
    assert s == 201, d
    return d["token"], d["user"]["id"]


try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/docs")
            break
        except Exception:
            time.sleep(0.3)

    owner_tok, owner_id = signup("owner@example.com", "김대리")
    s, team = api("POST", "/api/teams", {"name": "기획팀"}, owner_tok)
    member_tok, member_id = signup("member@example.com", "박과장")
    api("POST", "/api/teams/join", {"invite_code": team["invite_code"]}, member_tok)
    # 할 일이 있는 회의록 (Gemini 없이 직접 DB 에 넣지 않고 API 로 저장 - 키가 있으면 실제 정리)
    api("POST", f"/api/teams/{team['id']}/meetings", {
        "title": "배포 환경 점검", "met_at": "2026-09-18T01:30:00Z", "attendees": "박과장",
        "body": "박과장: 키 정리는 제가 이번 주 안에 하겠습니다."}, owner_tok)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))

        def shot(name):
            page.wait_for_timeout(400)
            page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)

        # B-03 세션 만료: 25시간 전에 발급된 토큰
        expired = create_token(owner_id, now=datetime.now(timezone.utc) - timedelta(hours=30))
        page.goto(BASE + "/login.html")
        page.evaluate(f"localStorage.setItem('token', '{expired}')")
        page.goto(BASE + "/meetings.html")
        page.wait_for_url("**/login.html")
        page.wait_for_selector("#boxExpired:not(.hidden)")
        check("B-03 만료 토큰이면 로그인 화면에 세션 만료 안내", "세션 만료" in page.inner_text("#boxExpired"))
        check("만료된 토큰은 지워짐", page.evaluate("localStorage.getItem('token')") is None)
        shot("30-session-expired")

        # B-02 로그인 실패: 이메일 존재 여부를 알리지 않는 한 메시지
        page.fill("#email", "owner@example.com")
        page.fill("#pw", "wrong-password")
        page.click("#submit")
        page.wait_for_selector("#boxErr:not(.hidden)")
        msg1 = page.inner_text("#boxErr")
        page.fill("#email", "nobody@example.com")
        page.click("#submit")
        page.wait_for_function("document.querySelector('#boxErr').textContent.includes('올바르지')")
        check("B-02 이메일이 없어도 비밀번호가 틀려도 같은 메시지", msg1 == page.inner_text("#boxErr"), msg1.replace("\n", " "))
        shot("31-login-fail")

        # B-11 잘못된 초대코드로 가입: 계정은 유지, 팀 화면으로
        page.click("#toggle")
        page.fill("#email", "newbie@example.com")
        page.fill("#pw", "password123")
        page.fill("#uname", "신입")
        page.fill("#invite", "MN-0000")
        page.click("#submit")
        page.wait_for_selector("#errInvite:not(.hidden)")
        check("B-11 초대코드 칸에 오류", "초대코드" in page.inner_text("#errInvite"), page.inner_text("#errInvite"))
        shot("32-signup-invite-error")
        page.wait_for_url("**/team.html", timeout=8000)
        page.wait_for_selector("#onboard:not(.hidden)")
        check("B-11 계정은 유지되고 팀 화면(소속 팀 없음)으로 이동", True)
        s, _ = api("POST", "/api/auth/login", {"email": "newbie@example.com", "password": "password123"})
        check("가입한 계정으로 로그인 가능", s == 200)
        # 팀 화면에서 합류 실패 (F-03)
        page.fill("#joinCode", "MN-9999")
        page.click("#joinBtn")
        page.wait_for_selector("#onboardErr:not(.hidden)")
        check("F-03 팀 화면에서도 없는 코드 오류", "없는 초대코드" in page.inner_text("#onboardErr"))
        shot("33-team-join-error")

        # F-06 정원 초과: 팀을 6명으로 채운 뒤 합류
        for i in range(4):
            tok, _ = signup(f"fill{i}@example.com", f"채움{i}")
            api("POST", "/api/teams/join", {"invite_code": team["invite_code"]}, tok)
        page.fill("#joinCode", team["invite_code"])
        page.click("#joinBtn")
        page.wait_for_function("document.querySelector('#onboardErr').textContent.includes('정원')")
        check("F-06 정원 초과 알림", True)
        shot("34-team-full")

        # F-08 member 권한: 읽기 전용
        page.evaluate("localStorage.clear()")
        page.goto(BASE + "/login.html")
        page.fill("#email", "member@example.com")
        page.fill("#pw", "password123")
        page.click("#submit")
        page.wait_for_url("**/meetings.html")
        page.goto(BASE + "/team.html")
        page.wait_for_selector("#teamView:not(.hidden)")
        check("F-08 member 는 이름 저장 · 재발급 버튼이 비활성", page.is_disabled("#saveName") and page.is_disabled("#newCodeBtn"))
        check("F-08 member 는 이름 입력이 읽기 전용", page.get_attribute("#tName", "readonly") is not None)
        check("F-08 잠김 안내가 보임", "owner 전용 조작 잠김" in page.inner_text("#lockNote"))
        check("멤버 6 / 6", "6 / 6" in page.inner_text("#mCap"), page.inner_text("#mCap"))
        shot("35-team-member-view")
        page.goto(BASE + "/todos.html")
        page.click("#tabAll")
        page.wait_for_selector(".card")
        check("E-11 member 는 삭제 버튼이 비활성", page.locator('[data-act="del"]').first.is_disabled())
        shot("36-todos-member")
        # owner 는 삭제 가능
        page.evaluate("localStorage.clear()")
        page.goto(BASE + "/login.html")
        page.fill("#email", "owner@example.com")
        page.fill("#pw", "password123")
        page.click("#submit")
        page.wait_for_url("**/meetings.html")
        page.goto(BASE + "/todos.html")
        page.click("#tabAll")
        page.wait_for_selector(".card")
        check("E-11 owner 는 삭제 버튼이 활성", not page.locator('[data-act="del"]').first.is_disabled())
        # 재발급 알림 (F-05)
        page.goto(BASE + "/team.html")
        page.wait_for_selector("#teamView:not(.hidden)")
        old = page.inner_text("#code")
        page.click("#newCodeBtn")
        page.wait_for_function(f"document.querySelector('#code').textContent !== '{old}'")
        check("F-05 owner 재발급", "다시 발급" in page.inner_text("#codeMsg"))
        shot("37-team-recode")
        # D-13 없는 회의록 / D-12 댓글 삭제 (남이 쓴 댓글은 owner 만 지움)
        page.goto(BASE + "/detail.html?id=9999")
        page.wait_for_selector("#missing:not(.hidden)")
        check("D-13 없는 회의록은 404 안내", "없는 회의록" in page.inner_text("#missing"))
        page.wait_for_url("**/meetings.html", timeout=6000)
        check("D-13 목록으로 돌려보냄", True)
        api("POST", "/api/meetings/1/comments", {"content": "박과장이 쓴 댓글"}, member_tok)
        page.goto(BASE + "/detail.html?id=1")
        page.wait_for_selector("#comments li")
        check("D-12 owner 에게는 남의 댓글에도 삭제 버튼", page.locator("[data-del-c]").count() == 1)
        page.locator("[data-del-c]").first.click()
        page.wait_for_function("document.querySelectorAll('#comments li').length === 0")
        check("D-12 댓글 삭제", True)
        check("D-11 댓글이 없으면 빈 안내", page.is_visible("#cEmpty"))
        shot("38-detail-no-comments")
        check("페이지 오류 없음", not errors, "; ".join(errors)[:300])
        browser.close()
finally:
    server.terminate()
    try:
        server.wait(timeout=10)
    except Exception:
        server.kill()
print(f"\n{sum(results)}/{len(results)} 통과")
print(f"스크린샷: {SHOTS}")
sys.exit(0 if all(results) else 1)
