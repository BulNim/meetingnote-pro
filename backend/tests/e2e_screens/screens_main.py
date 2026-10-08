"""화면 6종을 실제 서버 + 실제 Chrome 으로 돌려 보는 스크립트 (프로젝트 밖 임시 파일)"""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(r"D:\meetingnote-pro")
import tempfile
SCRATCH = Path(tempfile.mkdtemp(prefix="mn-e2e-"))   # 임시 폴더(DB · 스크린샷)
SHOTS = SCRATCH / "shots"
SHOTS.mkdir(exist_ok=True)
DB = SCRATCH / "demo.db"
PORT = 8766
BASE = f"http://127.0.0.1:{PORT}"
WAV = ROOT / "회의_녹음.wav"

for f in (DB,):
    if f.exists():
        f.unlink()

env = dict(os.environ, DATABASE_URL=f"sqlite:///{DB.as_posix()}", PYTHONIOENCODING="utf-8")
server = subprocess.Popen(
    [str(ROOT / ".venv/Scripts/python.exe"), "-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--port", str(PORT)],
    cwd=ROOT, env=env, stdout=open(SCRATCH / "server.log", "w"), stderr=subprocess.STDOUT)

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
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


try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/docs")
            break
        except Exception:
            time.sleep(0.3)

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "cdn.tailwindcss" not in m.text and "Failed to load resource" not in m.text else None)

        def shot(name):
            page.wait_for_timeout(400)
            page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)

        # ── 로그인 화면: 가입 전 검증 ──
        page.goto(BASE + "/login.html")
        page.wait_for_selector("#submit")
        shot("01-login")
        page.click("#toggle")
        page.fill("#email", "user@@example")
        page.fill("#pw", "1234")
        page.fill("#uname", "김대리")
        page.click("#submit")
        check("B-08 이메일 형식은 화면에서 먼저 거름", page.is_visible("#errEmail"), page.inner_text("#errEmail"))
        page.fill("#email", "owner@example.com")
        page.click("#submit")
        check("B-10 약한 비밀번호는 화면에서 먼저 거름", page.is_visible("#errPw"), page.inner_text("#errPw"))
        shot("02-signup-error")
        page.fill("#pw", "password123")
        page.click("#submit")
        page.wait_for_url("**/team.html")
        check("가입 후 소속 팀이 없으면 팀 화면으로 이동", "team.html" in page.url)
        shot("03-team-onboard")

        # ── 팀 만들기 ──
        page.fill("#newName", "기획팀")
        page.click("#createBtn")
        page.wait_for_selector("#teamView:not(.hidden)")
        code = page.inner_text("#code")
        check("F-01 팀 만들기 후 초대코드가 보임", code.startswith("MN-"), code)
        check("owner 는 이름 저장 · 재발급이 가능", not page.is_disabled("#saveName") and not page.is_disabled("#newCodeBtn"))
        shot("04-team")

        # 두 번째 사용자(박과장)는 API 로 합류
        s, d = api("POST", "/api/auth/signup", {"email": "member@example.com", "password": "password123", "name": "박과장"})
        member_token = d["token"]
        s, _ = api("POST", "/api/teams/join", {"invite_code": code}, member_token)
        check("API 합류", s == 200)

        # ── 회의록 목록: 빈 상태 → 새 회의록(받아쓰기) ──
        page.goto(BASE + "/meetings.html")
        page.wait_for_selector("#empty:not(.hidden)")
        check("C-02 빈 상태 안내", "아직 회의록이 없음" in page.inner_text("#emptyTitle"))
        shot("05-meetings-empty")
        page.click("#newBtn")
        page.fill("#nTitle", "2차 스프린트 계획 회의")
        page.fill("#nWho", "김대리, 박과장")
        # 5MB 초과 파일은 올리기 전에 막힌다
        big = SCRATCH / "big.wav"
        big.write_bytes(b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * 4_600_000)
        page.set_input_files("#file", str(big))
        page.wait_for_selector("#dropErr:not(.hidden)")
        check("C-09 4.4MB 초과는 413 알림", "4.4MB" in page.inner_text("#dropErr"), page.inner_text("#dropErr").replace("\n", " "))
        shot("06-upload-too-big")
        txt = SCRATCH / "fake.mp3"
        txt.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 200)
        page.set_input_files("#file", str(txt))
        page.wait_for_function("document.querySelector('#dropErr').textContent.includes('mp3 또는 wav')", timeout=15000)
        check("C-08 mp3/wav 가 아니면 415 알림", "mp3 또는 wav" in page.inner_text("#dropErr"))
        # 시험 wav 를 올린다 (실제 Gemini)
        page.set_input_files("#file", str(WAV))
        page.wait_for_function("document.querySelector('#nBody').value.length > 50", timeout=120000)
        check("C-06/07 시험 wav 가 올라가 받아쓰기됨", len(page.input_value("#nBody")) > 50, f"{len(page.input_value('#nBody'))}자")
        shot("07-upload-done")
        page.click("#saveBtn")
        page.wait_for_selector("#list a", timeout=120000)
        check("C-11 저장 후 목록 맨 위에 추가", page.locator("#list a").count() == 1)
        check("저장 후 입력칸이 비워짐", page.input_value("#nTitle") == "" and page.is_hidden("#newPanel"))
        shot("08-meetings-list")

        # 두 번째 회의록: 메모 붙여넣기로
        page.click("#newBtn")
        page.fill("#nTitle", "배포 환경 점검")
        page.fill("#nWho", "박과장")
        page.fill("#nBody", "박과장: 배포는 Vercel 로 확정했습니다. 키 정리는 제가 이번 주 안에 하겠습니다.")
        page.click("#saveBtn")
        page.wait_for_function("document.querySelectorAll('#list a').length === 2", timeout=120000)
        check("메모 붙여넣기로도 저장", True)

        # 검색
        page.fill("#q", "배포")
        page.wait_for_function("document.querySelectorAll('#list a').length === 1")
        check("C-03 제목 검색", "배포" in page.inner_text("#list"))
        page.fill("#q", "없는말")
        page.wait_for_selector("#empty:not(.hidden)")
        check("C-04 검색 0건", "검색 결과 없음" in page.inner_text("#emptyTitle"))
        shot("09-search-none")
        page.fill("#q", "")
        page.wait_for_function("document.querySelectorAll('#list a').length === 2")

        # ── 회의록 상세 ──
        page.locator("#list a").first.click()
        page.wait_for_selector("#todos li")
        shot("10-detail")
        check("D-01 세 칸과 본문 접힘", page.is_hidden("#body") and page.is_visible("#summary"))
        check("할 일 칸에 담당자 선택이 있음", page.locator("select.assign").count() >= 1)
        page.click("#bodyToggle")
        check("D-07 본문 펼침", page.is_visible("#body"))
        page.fill("#cInput", "받아쓰기 실패는 세 칸을 비우기로 했습니다.")
        page.click("#cBtn")
        page.wait_for_selector("#comments li")
        check("D-10 댓글 등록", page.locator("#comments li").count() == 1 and page.input_value("#cInput") == "")
        shot("11-detail-comment")
        page.click("#editBtn")
        page.fill("#eTitle", "2차 스프린트 계획 회의 (수정)")
        page.click("#editSave")
        page.wait_for_function("document.querySelector('#title').textContent.includes('수정')")
        check("D-02 제목 수정", True)
        page.click("#delBtn")
        check("D-08 삭제 확인", page.is_visible("#delConfirm"))
        shot("12-detail-delete-confirm")
        page.click("#delNo")

        # ── 할 일 칸반 ──
        page.goto(BASE + "/todos.html")
        page.wait_for_selector("#board")
        page.click("#tabAll")
        page.wait_for_function("document.querySelectorAll('.card').length >= 2")
        n_cards = page.locator(".card").count()
        shot("13-todos-all")
        check("E-02 전체 탭에 카드가 보임", n_cards >= 2, f"{n_cards}장")
        # 끌어서 옮기기: 대기 칸의 첫 카드를 진행 칸으로
        src = page.locator('section[data-col="OPEN"] .card').first
        what = src.locator("p").first.inner_text()
        box = src.bounding_box()
        dst = page.locator('section[data-col="DOING"]').bounding_box()
        page.mouse.move(box["x"] + 30, box["y"] + 20)
        page.mouse.down()
        page.mouse.move(box["x"] + 60, box["y"] + 40, steps=4)
        page.mouse.move(dst["x"] + dst["width"] / 2, dst["y"] + 80, steps=8)
        shot("14-todos-dragging")
        hint_visible = page.locator('section[data-col="DOING"] [data-hint]').is_visible()
        page.mouse.up()
        page.wait_for_function(
            "(w) => [...document.querySelectorAll('section[data-col=DOING] .card p')].some(p => p.textContent === w)", arg=what)
        check("E-03/04 끌어서 진행 칸으로 이동 (놓을 칸 표시 포함)", hint_visible, what)
        # 눌러서 칸 고르기
        card = page.locator('section[data-col="DOING"] .card').first
        card.locator("p").first.click()
        page.wait_for_selector("#picker button")
        check("E-05 눌러서 칸 고르기 버튼 3개", page.locator("#picker button").count() == 3)
        shot("15-todos-picker")
        page.locator("#picker button", has_text="완료").click()
        page.wait_for_function("document.querySelectorAll('section[data-col=DONE] .card').length >= 1")
        check("E-04 완료 칸으로 이동", True)
        # 담당자 배정
        chip = page.locator('[data-act="assign"]').first
        chip.click()
        page.wait_for_selector("select")
        page.locator("select").last.select_option(label="박과장")
        page.wait_for_timeout(600)
        check("E-06 담당자 배정", True)
        # 기한 돌리기
        due = page.locator('[data-act="due"]').first
        before = due.inner_text()
        due.click()
        page.wait_for_timeout(600)
        check("기한 배지를 눌러 바꿈", page.locator('[data-act="due"]').first.inner_text() != before)
        # 담당자 필터는 서버를 다시 부르지 않는다
        calls = []
        page.on("request", lambda r: calls.append(r.url) if "/api/" in r.url else None)
        page.select_option("#fWho", label="박과장")
        page.wait_for_timeout(400)
        check("E-07 담당자 필터는 서버를 다시 부르지 않음", not calls, str(calls))
        shot("16-todos-filter")

        # ── 팀 화면(활동 기록) ──
        page.goto(BASE + "/team.html")
        page.wait_for_selector("#acts li")
        acts = page.locator("#acts li").all_inner_texts()
        check("F-01 활동 기록이 최근 순으로 보임", len(acts) >= 3, f"{len(acts)}건")
        shot("17-team-activities")

        # ── 내 정보 ──
        page.goto(BASE + "/profile.html")
        page.wait_for_function("document.querySelector('#tCount').textContent !== ''", timeout=10000)
        shot("18-profile")
        page.fill("#pw1", "newpass1234")
        page.fill("#pw2", "different12")
        page.click("#saveBtn")
        check("J-03 비밀번호 불일치는 서버로 보내지 않음", "두 비밀번호가 다름" in page.inner_text("#errPw"))
        page.fill("#pw2", "newpass1234")
        page.fill("#pwCur", "wrongpass99")
        page.click("#saveBtn")
        page.wait_for_function("document.querySelector('#errCur').textContent.length > 0")
        check("현재 비밀번호가 틀리면 오류 표시", "현재 비밀번호" in page.inner_text("#errCur"))
        shot("19-profile-wrong-current")
        page.fill("#pwCur", "password123")
        page.fill("#name", "김수석")
        page.click("#saveBtn")
        page.wait_for_function("document.querySelector('#who').textContent === '김수석'")
        check("J-06 저장 완료", True)
        page.click("#logoutBtn")
        page.wait_for_url("**/login.html")
        check("로그아웃하면 로그인 화면", True)

        # ── 만료 토큰 → 세션 만료 안내 ──
        page.evaluate("localStorage.setItem('token','garbage.token.value')")
        page.goto(BASE + "/meetings.html")
        page.wait_for_url("**/login.html")
        check("토큰이 깨지면 로그인 화면으로", "login.html" in page.url)

        # ── 다크 모드 + 360px ──
        page.goto(BASE + "/login.html")
        page.fill("#email", "owner@example.com")
        page.fill("#pw", "newpass1234")
        page.click("#submit")
        page.wait_for_url("**/meetings.html")
        page.click("#themeBtn")
        shot("20-meetings-dark")
        page.set_viewport_size({"width": 360, "height": 800})
        for name in ("meetings", "todos"):
            page.goto(BASE + f"/{name}.html")
            page.wait_for_timeout(1200)
            overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
            check(f"N-01 360px {name} 가로 스크롤 없음", not overflow)
            shot(f"21-{name}-360")
        page.goto(BASE + "/meetings.html")
        page.locator("#list a").first.click()
        page.wait_for_selector("#todos")
        page.wait_for_timeout(800)
        overflow = page.evaluate("document.documentElement.scrollWidth > document.documentElement.clientWidth")
        check("N-01 360px detail 가로 스크롤 없음", not overflow)
        shot("21-detail-360")

        check("브라우저 콘솔/페이지 오류 없음", not errors, "; ".join(errors)[:300])
        browser.close()
finally:
    server.terminate()
    try:
        server.wait(timeout=10)
    except Exception:
        server.kill()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} 통과")
print(f"스크린샷: {SHOTS}")
sys.exit(1 if failed else 0)
