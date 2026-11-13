# Design

## Context

- 저장소에는 코드가 없다. 있는 것은 `docs/`(정의서 · 스토리보드 · 디자인시스템 PDF), `publish/`(확정 화면 6종 · `theme.js` · `components.html` · `index.html`), 전사 시험용 `회의_녹음.wav`(모노 22,050Hz 16bit, 약 100초, 4.21MB) 뿐이다.
- 자료 우선순위는 정의서 > 스토리보드 > 퍼블리싱이다. 다만 색 · 클래스 · 마크업은 퍼블리싱이 확정본이다.
- 스토리보드 I-01 통합 매핑표(화면 × API × DB)가 화면마다 부를 API 와 건드릴 테이블의 기준이다. 고유 경로 27개 · 테이블 7개와 정의서가 서로 맞는 것을 확인했다.
- 로컬 Python 은 3.15 이다. uv 는 없고 pip 를 쓴다. 저장소는 아직 git 저장소가 아니다.

## Goals / Non-Goals

**Goals:**
- 코드 한 벌이 로컬(SQLite · 정적 파일 일체형)과 배포(Vercel · Neon)에서 그대로 돈다
- 화면은 퍼블리싱과 픽셀 단위로 같은 클래스를 쓴다. 새 색 · 새 모서리 · 인라인 style · `!important` · 새 클래스 조합을 만들지 않는다
- pytest 는 네트워크와 키 없이 돈다. 실제 Gemini 전사는 키가 있을 때만 도는 별도 시험으로 둔다

**Non-Goals:**
- 프런트 빌드 도구(번들러 · npm) 도입 - Tailwind 는 CDN 그대로
- 마이크로서비스 분리 · 캐시 · 로그 수집(Sentry) - logging 모듈만 쓴다
- DB 마이그레이션 도구 - 1회차는 `create_all` 로 테이블을 만든다

## Decisions

### 1. 폴더 구조

```
meetingnote-pro/
  .env  .env.example  .gitignore  .vercelignore
  pyproject.toml  requirements.txt  vercel.json
  backend/
    main.py          FastAPI app, 라우터 묶기, /docs, StaticFiles
    config.py        .env 읽기 (루트 기준 경로), 상수(JWT 24h, 업로드 상한 등)
    db.py            엔진 · 세션. DATABASE_URL 있으면 Postgres, 없으면 SQLite
    models.py        7테이블 ORM
    errors.py        AppError(code, status) + {code,msg} 핸들러
    security.py      bcrypt, JWT 발급 · 검증, 현재 사용자 의존성
    activity.py      활동 기록 생성 · 문장(text) 만들기
    gemini.py        받아쓰기 · 세 항목 구분 (교체 가능한 한 곳)
    routers/         auth · teams · meetings · todos · comments · activities
  frontend/
    theme.js         publish/theme.js 를 그대로 복사 (STATE 바 함수 제외)
    api.js           fetch 래퍼: 토큰 헤더, 401 TOKEN_EXPIRED 처리, {code,msg} 해석
    login.html meetings.html detail.html todos.html team.html profile.html
  tests/
    conftest.py      임시 SQLite, 가짜 Gemini, 사용자 · 팀 만드는 도우미
    test_*.py        capability 별
    test_gemini_live.py   키가 있을 때만 회의_녹음.wav 로 실제 전사
```

- `.env` 는 프로젝트 루트에 둔다. `config.py` 는 자기 파일 위치에서 루트를 계산해 읽는다. 실행 위치가 달라도 키를 찾는다.
- 대안: `backend/.env` - 정의서 7-5 가 루트를 정했으므로 쓰지 않는다.

### 2. DB 전환

- `DATABASE_URL` 이 있으면 그 값(Neon), 없으면 루트의 `meetingnote.db`(SQLite)를 쓴다. 분기는 `db.py` 한 줄이다.
- Neon 이 주는 `postgres://` 는 SQLAlchemy 가 읽도록 `postgresql+psycopg://` 로 바꿔 쓴다.
- 앱 시작 때 `create_all` 로 7테이블을 만든다. 배포에서는 콜드 스타트마다 돌지만 이미 있으면 건너뛴다.
- 시각은 UTC ISO 8601 로 저장 · 응답한다. 화면이 현지 시각으로 바꿔 그린다.
- decisions 는 줄바꿈으로 구분한 TEXT 한 칸이다. decision_count 는 빈 줄을 뺀 줄 수로 응답할 때 계산한다.

### 3. 인증

- bcrypt 로 해시하고 PyJWT(HS256)로 서명한다. 만료 24h, 갱신 없음이다.
- `JWT_SECRET` 은 `.env` 에 넣지 않는다. 코드 기본값을 쓰고, 배포에서는 Vercel 환경 변수로 덮는다(정의서 7-5).
- 토큰 없음 · 위조 · 만료는 모두 401 `TOKEN_EXPIRED` 다.
- Swagger 의 Authorize 버튼은 `HTTPBearer` 보안 스키마로 단다. 로그인 응답의 token 을 그대로 붙여 넣으면 된다.
- 대안: OAuth2PasswordBearer(폼 로그인 창) - 로그인 본문이 JSON 이라 맞지 않는다.

### 4. 오류

- `AppError(status, code, msg)` 하나로 던지고 핸들러가 `{code, msg}` 로 바꾼다.
- FastAPI 의 기본 422 는 400 `VALIDATION_ERROR` 로, 없는 경로 404 는 `NOT_FOUND` 로 바꾼다.

### 5. 권한 판정

| 대상 | 읽기 | 수정 | 삭제 |
|---|---|---|---|
| 회의록 | 팀원 | 작성자 · owner | 작성자 · owner |
| 할 일 | 팀원 | 팀원 누구나(상태 · 담당자) | 만든 사람 · 담당자 · owner |
| 댓글 | 팀원 | - | 쓴 사람 · owner |
| 팀 이름 · 초대코드 재발급 | 팀원 | owner (`OWNER_ONLY`) | - |

- 응답의 `can_edit` · `can_delete` 와 API 의 403 판정은 같은 함수를 쓴다. 화면 잠금과 서버 거부가 어긋나지 않게 한다.
- 할 일의 「만든 사람」은 todos.author_id 다. 회의록에서 뽑힌 할 일은 회의록 작성자가 author_id 다.
- 다른 팀의 회의록 단건은 존재를 드러내지 않도록 404 `MEETING_NOT_FOUND` 로 답한다(D-13). 다른 팀 id 로 목록류를 부르면 403 `FORBIDDEN` 이다.

### 6. 업로드와 Gemini

- 형식은 파일 머리 바이트로 판정한다. wav 는 `RIFF....WAVE`, mp3 는 `ID3` 또는 프레임 동기 `0xFFE`. 확장자는 보지 않는다.
- 상한은 배포(`VERCEL` 환경 변수가 있음)에서 4.5MB, 로컬에서 20MB 다. 로컬에서 20MB 를 넘으면 Gemini Files API 로 올린다(정의서 9). 넘는 상한은 400 `VALIDATION_ERROR` 다.
- 모델은 `GEMINI_MODEL`(기본 `gemini-3.1-flash-lite`) 하나로 받아쓰기와 세 항목 구분을 모두 한다. SDK 는 google-genai 다.
- 세 항목 구분은 JSON 응답 스키마(`summary`, `decisions[]`, `todos[{what, assignee, due}]`)로 받는다. 읽지 못하면 저장하지 않고 502 다. 공급자 5xx 는 1회 재시도한다.
- 키가 비어 있으면 Gemini 를 부르지 않고 바로 502 `VALIDATION_ERROR`(msg 「GEMINI_API_KEY 없음」)를 돌려준다.
- 시험에서는 `gemini.py` 의 두 함수를 가짜로 바꾼다(pytest 의 monkeypatch). 그래서 모든 경로를 키 없이 시험할 수 있다.
- 담당자 대조: 공백과 끝의 「님」을 지운 이름이 멤버 이름과 같으면 그 멤버, 아니면 null 이다.

### 7. 프런트엔드

- `publish/*.html` 을 `frontend/` 로 옮기며 다음만 바꾼다.
  - `window.stateBar(...)` 호출과 STATE 전용 장면 함수, 예시 데이터(SAMPLE)를 지운다
  - 장면 해설 글(`qNote` · `headNote` · `note` 같은 설명 줄)을 지운다. 사용자에게 보이는 안내 문구(빈 상태 · 오류 · 띠 알림)는 남긴다
  - 그 자리에 `api.js` 로 실제 API 를 부르고 같은 마크업 함수로 그린다
- 클래스는 publish 에 적힌 문자열을 그대로 쓴다. 새 조합이 필요하면 `theme.js` 의 `window.UI` 에 먼저 넣고 이름으로 쓴다.
- 끌기는 pointerdown · pointermove · pointerup 으로 만든다. 놓을 때 PUT 을 한 번 부르고, 실패하면 되돌린다.
- 화면 주소는 `/login.html` 처럼 확장자를 붙인다. `/` 는 `/login.html` 로 보낸다.
- 각 화면은 시작할 때 토큰을 확인한다. 없으면 login.html 로, 팀이 없으면 team.html 로 보낸다.

### 8. 정적 파일과 /docs

- API 라우터와 `/docs` 를 먼저 등록하고 `frontend/` 를 `/` 에 StaticFiles 로 맨 마지막에 붙인다. 그래야 `/docs` · `/api/*` 가 정적 파일에 가려지지 않는다.
- 배포도 같은 앱 하나가 화면과 API 를 함께 낸다. 같은 주소라 CORS 는 기본으로 localhost 개발 주소만 허용한다.

### 9. 배포 설정

- `vercel.json`: `{"framework": "fastapi"}`
- `pyproject.toml`: `[tool.vercel] entrypoint = "backend.main:app"` (모듈:객체 형식. 파일 경로로 적으면 빌드가 실패한다)
- `.vercelignore`: `.agents/` · `.claude/` · `skills-lock.json` · `.env.local` · `docs/` · `publish/` · `tests/` · `*.wav` · `meetingnote.db`
- Vercel 프로젝트 연결 · Neon 연결 · `GEMINI_API_KEY` · `GEMINI_MODEL` · `JWT_SECRET` 등록은 사용자가 한다.

### 10. 환경 변수 파일

- `.env` 와 `.env.example` 은 `GEMINI_API_KEY=` · `GEMINI_MODEL=gemini-3.1-flash-lite` 두 줄뿐이다. 키 값은 사용자가 직접 넣는다.
- `.gitignore` 는 `.env` · `meetingnote.db` · `__pycache__/` · `.venv/` · `.pytest_cache/` 를 뺀다.

## Risks / Trade-offs

- [배포 업로드 4.5MB 한도] → 배포에서는 4.5MB 넘는 녹취를 받지 못한다. 화면 안내와 400 메시지에 상한을 적는다. 큰 파일 직접 업로드는 범위 밖이다
- [Gemini 지연] → 받아쓰기와 세 항목 구분은 100ms 기준에서 제외한다(정의서 9). 화면은 처리 중 잠금과 진행 표시로 기다리게 한다
- [Gemini 출력 흔들림] → JSON 응답 스키마로 받고, 읽지 못하면 저장하지 않고 502 를 낸다. 본문은 화면에 남는다
- [Python 3.15 와 패키지 호환] → 설치가 막히면 해당 패키지의 최신판을 먼저 시도하고, 그래도 안 되면 사용자에게 알린다
- [create_all 만 씀] → 2회차에 칼럼이 바뀌면 마이그레이션이 필요하다. 1회차 범위에서는 받아들인다
- [기한 판정이 글자 셋뿐] → 「어제 · 지난 주 · 지난 달」 밖의 글자는 판정하지 않는다. 정의서가 정한 동작이다

## Migration Plan

1. 로컬: `pip install -r requirements.txt` → `.env` 에 키 입력 → `uvicorn backend.main:app --reload` → `http://127.0.0.1:8000`
2. 배포: Vercel 프로젝트 연결 → Vercel Storage 에서 Neon 연결(`DATABASE_URL` 자동 주입) → 환경 변수 등록 → 배포
3. 되돌리기: 배포는 Vercel 의 이전 배포로 되돌린다. DB 는 Neon 시점 복구를 쓴다
