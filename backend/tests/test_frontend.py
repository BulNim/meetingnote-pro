"""8. 화면 연결 - 스토리보드 I-01 통합 매핑표(73쪽)와 디자인 시스템 규칙을 정적 검사한다"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONT, PUBLISH = ROOT / "frontend", ROOT / "publish"
SCREENS = ["login", "meetings", "detail", "todos", "team", "profile"]
METHODS = {"get": "GET", "post": "POST", "put": "PUT", "del": "DELETE"}


def C(method, path):
    return (method, "/api/" + path)


# 스토리보드 I-01 표 그대로 (화면 -> 건드리는 엔드포인트 30개)
TABLE = {
    "login": {C("POST", "auth/signup"), C("POST", "auth/login"), C("POST", "teams/join")},
    "meetings": {
        C("POST", "teams/{id}/meetings"), C("GET", "teams/{id}/meetings"), C("POST", "upload"),
        C("GET", "auth/me"), C("POST", "auth/logout"),
    },
    "detail": {
        C("GET", "meetings/{id}"), C("PUT", "meetings/{id}"), C("DELETE", "meetings/{id}"), C("PUT", "todos/{id}"),
        C("POST", "meetings/{id}/comments"), C("GET", "meetings/{id}/comments"), C("DELETE", "comments/{id}"),
    },
    "todos": {C("GET", "teams/{id}/todos"), C("PUT", "todos/{id}"), C("DELETE", "todos/{id}"), C("GET", "me/todos")},
    "team": {
        C("POST", "teams"), C("GET", "teams"), C("PUT", "teams/{id}"), C("POST", "teams/join"),
        C("GET", "teams/{id}/members"), C("PUT", "teams/{id}/code"), C("GET", "teams/{id}/activities"),
    },
    "profile": {C("GET", "auth/me"), C("PUT", "auth/me"), C("GET", "me/todos"), C("GET", "me/activities")},
}

# 표와 다른 곳 - 이유가 있는 것만 여기에 적는다. 여기에 없는 차이가 생기면 테스트가 실패한다
ADDED = {
    # 로그인 직후 소속 팀을 확인해 팀 id 를 저장한다 (proposal 의 결정)
    "login": {C("GET", "teams")},
    # 담당자를 고르려면 팀 멤버 목록이 필요한데 표의 detail 행에 빠져 있다
    "detail": {C("GET", "teams/{id}/members")},
    "todos": {C("GET", "teams/{id}/members")},
    # 확정 디자인(publish)의 로그아웃 버튼은 profile 화면에 있다. 표는 meetings 에 적었다
    "profile": {C("POST", "auth/logout")},
}
MISSING = {
    # publish 의 meetings 화면에는 사용자 표시도 로그아웃도 없다. 팀 id 는 저장값을 쓰므로 auth/me 도 필요 없다
    "meetings": {C("GET", "auth/me"), C("POST", "auth/logout")},
}


def calls(screen: str) -> set:
    text = (FRONT / f"{screen}.html").read_text(encoding="utf-8")
    found = set()
    for method, path in re.findall(r"API\.(get|post|put|del)\(\s*[`\"']([^`\"']+)[`\"']", text):
        path = re.sub(r"\$\{[^}]*\}", "{id}", path).split("?")[0]
        found.add((METHODS[method], path))
    if "API.upload(" in text:
        found.add(("POST", "/api/upload"))
    if "API.resolveTeam(" in text:
        found.add(("GET", "/api/teams"))
    return found


@pytest.mark.parametrize("screen", SCREENS)
def test_화면이_부르는_경로는_매핑표와_기록된_차이만큼만_다르다(screen):
    expected = (TABLE[screen] | ADDED.get(screen, set())) - MISSING.get(screen, set())
    assert calls(screen) == expected


def test_표의_경로를_한_번만_세면_고유_26개(client):
    table_unique = set().union(*TABLE.values())
    assert len(table_unique) == 26
    spec = client.get("/openapi.json").json()
    served = {
        (m.upper(), re.sub(r"\{[^}]*\}", "{id}", path))
        for path, item in spec["paths"].items()
        for m in item
        if m in {"get", "post", "put", "delete"}
    }
    assert table_unique == served


def test_쓰이지_않는_경로는_0개(client):
    spec = client.get("/openapi.json").json()
    served = {
        (m.upper(), re.sub(r"\{[^}]*\}", "{id}", path))
        for path, item in spec["paths"].items()
        for m in item
        if m in {"get", "post", "put", "delete"}
    }
    used = set().union(*(calls(s) for s in SCREENS))
    assert served - used == set()
    assert used - served == set()


def test_화면_6종과_공통_파일만_있다():
    names = {p.name for p in FRONT.iterdir()}
    assert names == {f"{s}.html" for s in SCREENS} | {"index.html", "theme.js", "api.js"}


def test_퍼블리싱_확인용_요소는_구현에_없다():
    for screen in SCREENS:
        text = (FRONT / f"{screen}.html").read_text(encoding="utf-8")
        assert "stateBar" not in text and 'id="note"' not in text, screen


def class_tokens(text: str) -> set:
    text = re.sub(r"\$\{[^}]*\}", " ", text)   # 템플릿 식(${...})은 따옴표를 품을 수 있어 먼저 걷어낸다
    out = set()
    for attr in re.findall(r'class="([^"]*)"', text):
        out |= set(attr.split())
    return out


def published_tokens() -> set:
    tokens = set()
    for f in PUBLISH.glob("*.html"):
        tokens |= class_tokens(f.read_text(encoding="utf-8"))
    tokens |= set(re.findall(r"[A-Za-z0-9\-\[\]/:.%!_]+", (PUBLISH / "theme.js").read_text(encoding="utf-8")))
    return tokens


def test_새_클래스를_만들지_않았다():
    allowed = published_tokens()
    for screen in SCREENS:
        new = class_tokens((FRONT / f"{screen}.html").read_text(encoding="utf-8")) - allowed
        assert not new, f"{screen}: publish 에 없는 클래스 {sorted(new)}"


def test_important_와_새_색_금지():
    other_colors = re.compile(r"\b(?:bg|text|border|ring|from|to)-(?:slate|gray|zinc|neutral|stone|rose|pink|amber|yellow|lime|emerald|teal|cyan|sky|indigo|violet|fuchsia)-\d")
    for screen in SCREENS:
        text = (FRONT / f"{screen}.html").read_text(encoding="utf-8")
        assert "!important" not in text, screen
        assert not re.search(r'class="[^"]*(?:^|\s)![a-z]', text), f"{screen}: ! 수식어"
        assert not other_colors.search(text), f"{screen}: 팔레트 밖의 색"
        assert not re.search(r"#[0-9a-fA-F]{6}\b", text), f"{screen}: 색 값을 직접 적음"


def test_인라인_style은_확정_디자인의_진행바_하나뿐():
    found = {}
    for screen in SCREENS:
        text = (FRONT / f"{screen}.html").read_text(encoding="utf-8")
        hits = re.findall(r'style="[^"]*"', text)
        if hits:
            found[screen] = hits
    assert found == {"meetings": ['style="width:0%"']}


def test_토큰은_localStorage에만_둔다():
    for name in [f"{s}.html" for s in SCREENS] + ["api.js"]:
        text = (FRONT / name).read_text(encoding="utf-8")
        assert "sessionStorage" not in text and "document.cookie" not in text, name
