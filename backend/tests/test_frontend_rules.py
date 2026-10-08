"""디자인 규칙 정적 검사 (tasks 8.3) - frontend/ 가 publish 의 규칙을 어기면 실패한다

금지: 인라인 style 속성 · !important · 버튼/입력 높이 44px 가 아닌 값(h-7 ~ h-10) ·
      theme.js 밖의 16진 색 · 퍼블리싱 확인용 stateBar · HTML5 네이티브 드래그
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
PUBLISH = ROOT / "publish"

PAGES = ["login", "meetings", "detail", "todos", "team", "profile"]


def _sources():
    files = [p for p in FRONTEND.rglob("*") if p.suffix in {".html", ".js"}]
    return files


def _violations(text: str, name: str, is_theme: bool) -> list[str]:
    found = []
    if re.search(r"""\bstyle\s*=\s*["']""", text):
        found.append(f"{name}: 인라인 style 속성")
    if "!important" in text:
        found.append(f"{name}: !important")
    # 로고 · 아바타 같은 정사각형(w-9 h-9)은 버튼이 아니므로 제외하고, 나머지 h-7 ~ h-10 만 잡는다
    without_squares = re.sub(r"\bw-(\d+) h-\1\b", "", text)
    if re.search(r"\bh-(7|8|9|10)\b", without_squares):
        found.append(f"{name}: 44px(h-11) 가 아닌 높이 h-7 ~ h-10")
    if not is_theme and re.search(r"#[0-9a-fA-F]{6}\b", text):
        found.append(f"{name}: 팔레트 밖의 16진 색 직접 입력")
    if "stateBar" in text and not is_theme:
        found.append(f"{name}: 퍼블리싱 확인용 stateBar")
    if re.search(r"draggable\s*=|dragstart", text):
        found.append(f"{name}: HTML5 네이티브 드래그")
    return found


def test_frontend_follows_design_rules():
    bad = []
    for path in _sources():
        text = path.read_text(encoding="utf-8")
        bad += _violations(text, path.relative_to(ROOT).as_posix(), path.name == "theme.js")
    assert not bad, "\n".join(bad)


@pytest.mark.parametrize("snippet,expect", [
    ('<div style="width:3px">', "인라인 style"),
    ('class="h-10 px-3"', "h-7 ~ h-10"),
    ("color: red !important", "!important"),
    ("const c = '#12AB34';", "16진 색"),
    ("window.stateBar([])", "stateBar"),
    ('<div draggable="true">', "네이티브 드래그"),
])
def test_the_checker_catches_violations(snippet, expect):
    assert any(expect in v for v in _violations(snippet, "x.html", False))


def test_checker_ignores_clean_markup():
    assert _violations('<button class="h-11 px-4 rounded-xl">확인</button>', "x.html", False) == []


def test_checker_allows_square_logo_boxes_but_not_short_buttons():
    assert _violations('<div class="w-9 h-9 rounded-xl">김</div>', "x.html", False) == []
    assert _violations('<button class="w-20 h-9 rounded-xl">x</button>', "x.html", False) != []


@pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없어 theme.js 를 읽지 못함")
def test_theme_js_only_adds_names_to_publish_theme():
    """frontend/theme.js 는 publish/theme.js 의 기존 값을 바꾸지 않는다 (예외: THEME_BTN)"""
    script = """
      global.window = {}; global.tailwind = {};
      const fs = require('fs');
      global.document = {documentElement:{classList:{toggle(){}}}, getElementById(){return null}};
      global.matchMedia = () => ({matches:false}); global.localStorage = {getItem(){return null}};
      const load = (p) => { global.window = {}; global.tailwind = {}; eval(fs.readFileSync(p,'utf8'));
        return {UI: window.UI, STRIPE: window.STRIPE, LABEL: window.LABEL, colors: tailwind.config.theme.extend.colors,
                fonts: tailwind.config.theme.extend.fontFamily, dark: tailwind.config.darkMode}; };
      console.log(JSON.stringify({pub: load(process.argv[1]), imp: load(process.argv[2])}));
    """
    out = subprocess.run(["node", "-e", script, str(PUBLISH / "theme.js"), str(FRONTEND / "theme.js")],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    data = json.loads(out)
    pub, imp = data["pub"], data["imp"]
    assert pub["colors"] == imp["colors"] and pub["fonts"] == imp["fonts"] and pub["dark"] == imp["dark"]
    for group in ("UI", "STRIPE", "LABEL"):
        for key, value in pub[group].items():
            assert imp[group].get(key) == value, f"{group}.{key} 값이 publish 와 다름"
    assert set(imp["UI"]) > set(pub["UI"])  # 이름은 늘었다


def test_pages_exist_and_load_theme_and_app_scripts():
    for name in PAGES:
        html = (FRONTEND / f"{name}.html").read_text(encoding="utf-8")
        assert '<script src="theme.js">' in html
        assert 'src="js/app.js"' in html and f'src="js/{name}.js"' in html


def test_static_pages_are_served_with_extensions(client):
    for name in PAGES:
        r = client.get(f"/{name}.html")
        assert r.status_code == 200, name
    assert client.get("/theme.js").status_code == 200
    assert client.get("/docs").status_code == 200  # 정적 연결이 문서 경로를 가리지 않음


def test_root_redirects_to_login(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307) and r.headers["location"] == "/login.html"


@pytest.mark.skipif(shutil.which("node") is None, reason="node 가 없어 문법을 검사하지 못함")
def test_every_frontend_script_parses():
    """화면 스크립트에 문법 오류가 없어야 한다 (파이썬 시험은 JS 를 읽지 않아 따로 검사)"""
    for path in sorted(FRONTEND.rglob("*.js")):
        r = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
        assert r.returncode == 0, f"{path.relative_to(ROOT)}: {r.stderr[:300]}"
