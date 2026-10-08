# Design

## Context

- 동기와 범위는 `proposal.md`, 동작 계약은 `specs/` 를 본다. 확정 결정과 헤비 이슈는 `docs/결정기록.md`(D-001 ~, H-1 ~) 가 정본이다.
- 코드는 아직 없다(`backend/` · `frontend/` 신규). 화면 규격은 `publish/` 의 HTML 6종과 `theme.js` 가 확정이며, 상태 62종이 스토리보드 번호(B-01 ~ J-07)와 이어진다.
- 제약: Python FastAPI + SQLAlchemy(Object Relational Mapping), 바닐라 JS, Tailwind CDN. 로컬은 SQLite, 배포는 Vercel + Neon Postgres. 키는 `.env` 두 줄(`GEMINI_API_KEY` · `GEMINI_MODEL`)만 읽고 `JWT_SECRET` · `DATABASE_URL` · CORS 는 코드 기본값이나 배포 환경변수다.
- 로컬은 일체형이라 `uvicorn` 하나가 API 와 정적 파일을 함께 내보낸다. 정적 파일은 `/login.html` 처럼 확장자를 붙여 부른다.

## Goals / Non-Goals

**Goals:**
- 스토리보드 I-01 통합 매핑표의 API 26개와 테이블 7개를 그대로 구현하고 경로를 더하지 않는다.
- 같은 스펙에서 같은 구조가 나오도록 이름 · 코드 · 응답 모양을 고정한다.
- 화면은 `theme.js` 이름만으로 그린다. 새 색 · 새 클래스 조합을 만들지 않는다.
- 로컬과 배포가 코드 한 벌로 돌아간다 (`DATABASE_URL` 유무 한 줄 분기).

**Non-Goals:**
- 기한 입력과 판정의 정교화(이번 회차는 `publish` 방식, 차후 논의 - 결정기록 H-4).
- 녹음 길이 · 처리 시간 제한(60초 규칙은 폐기 - D-009).
- 권한 등급 확장, 실시간 · 푸시, 외부 연동, 분할 업로드.
- 토큰 블랙리스트와 갱신 토큰.

## Decisions

### 구조

```
meetingnote-pro/
  .env  .env.example  .gitignore  pyproject.toml
  backend/
    app/  main.py  config.py  db.py  models.py  security.py  errors.py
          routers/  auth.py teams.py meetings.py todos.py comments.py activities.py
          services/ gemini.py  activity.py
    tests/
  frontend/
    theme.js  *.html  js/  (화면별 스크립트)
```

- `main.py` 는 라우터를 먼저 등록하고 마지막에 `frontend/` 를 정적 파일로 연결한다. 그래서 `/docs` · `/openapi.json` 이 정적 파일에 가려지지 않는다 (spec: auth 「API 시험 화면」).

### 데이터

- 테이블 7개는 프로그램정의 6쪽 그대로: `users` · `teams` · `memberships` · `meetings` · `todos` · `comments` · `activities`. `memberships` 는 `(team_id, user_id)` 가 유일하고 사용자당 행이 하나다(한 사람 한 팀을 DB 에서도 막음).
- `meetings.decisions` 는 줄바꿈 구분 TEXT, `todos.due_text` 는 자유 글자(원본 그대로), `todos.status` 는 `OPEN | DOING | DONE`. `activities.kind` 는 5종 check 제약.
- 회의록 삭제는 할 일과 댓글을 함께 지운다(외래키 cascade). 시각은 UTC ISO 8601 로 저장하고 화면이 현지 시간으로 바꿔 보인다.
- `DATABASE_URL` 이 있으면 그 Postgres, 없으면 `meetingnote.db` SQLite. 엔진 생성 한 곳에서만 분기한다. 로컬 SQLite 파일은 git 에서 제외한다.

### 인증과 권한

- JWT(HS256, 24시간, 갱신 없음), 비밀번호는 bcrypt. 토큰은 화면이 `localStorage` 에 저장한다. 만료는 `TOKEN_EXPIRED`, 없거나 깨진 토큰은 `UNAUTHORIZED` 로 구분한다.
- Swagger 는 HTTP Bearer 스킴으로 만들어 `Authorize` 에 토큰을 붙여 넣게 한다. 로그인 API 가 JSON 본문을 받으므로 OAuth2 폼 방식은 쓰지 않는다.
- 권한 판정은 서버가 한다: 같은 팀 확인(아니면 404) → owner 전용이면 `OWNER_ONLY` → 올린 사람 또는 owner 면 `FORBIDDEN` 판정. 화면의 비활성은 보조 수단일 뿐이다.
- 오류는 예외 핸들러 한 곳에서 `{code, msg}` 로 바꾼다. 코드 집합은 spec 「공통 오류 본문」 의 16개로 닫혀 있고, 검증 오류는 `VALIDATION_ERROR` 로 통일한다.

### Gemini 호출

- 호출은 `services/gemini.py` 한 곳에 모은다. 모델 이름은 `GEMINI_MODEL`, 키는 `GEMINI_API_KEY` 이며 코드에 적지 않는다.
- 받아쓰기(`POST /api/upload`): 업로드 파일을 4.4MB 와 내용 형식(mp3 · wav 매직 바이트)으로 검사한 뒤 한 번 호출해 본문 텍스트만 돌려준다. 파일은 저장하지 않는다. 실패는 502 `UPSTREAM_ERROR`.
- 세 항목 구분(`POST .../meetings`): 본문을 한 번 호출해 `summary` · `decisions[]` · `todos[{what, assignee, due}]` 구조로 받는다. 응답은 JSON 스키마로 받고, `assignee` 는 팀 멤버 이름과 일치할 때만 `assignee_id` 로 바꾼다. 기한은 본문에 드러난 표현 그대로, 없으면 `미정`. 호출이 실패하면 세 칸을 비우고 회의록은 저장한다(201).
- 요청 시간 제한 값은 정하지 않았다. 배포 환경의 함수 실행 시간 설정은 구현 시 Vercel 문서로 확인한다 (결정기록 H-2).

### 활동 기록

- 기록은 `services/activity.py` 의 함수 하나로 모으고, 각 라우터가 같은 트랜잭션 안에서 부른다. 문장은 서버가 만든다: 회의록 「{제목}」 등록 / 할 일 「{내용}」를 {이름}에게 배정 / 할 일 「{내용}」 완료 / 회의록 「{제목}」에 댓글 작성 / 초대코드로 합류.
- `todo_assign` 은 담당자가 다른 사람으로 바뀌어 새 담당자가 생길 때만 남기고, 미정으로 되돌리는 경우는 남기지 않는다.

### 프론트엔드 규칙

- `frontend/theme.js` 는 `publish/theme.js` 를 복사해 시작한다. `stateBar` 는 호출하지 않고(구현에는 넣지 않음) 상태 설명 줄(`#note`)과 퍼블리싱용 API 경로 문구도 넣지 않는다. 토스트 문구는 사람이 읽는 말로 바꾼다(「진행 칸으로 옮겼습니다」).
- 규칙 위반을 고쳐 구현한다(D-005): 버튼과 입력은 모두 `window.UI` 이름으로 쓰고 높이는 44px 하나, 복붙한 클래스 문자열은 `UI` 이름으로 바꾼다. `publish` 에 이름이 없는 요소(선택 박스 · 날짜 입력 · 텍스트영역 · 탭 · 내비 링크)는 새 클래스를 화면에서 조합하지 않고 **`theme.js` 에 먼저 이름으로 등록**해 쓴다. 이 이름은 `UI` 의 기존 토큰(`h-11` · `rounded-xl` · `border-line` 등)만으로 만든다.
- `!important` · 인라인 `style` · 새 색 · 새 모서리 값 · 클래스 조합은 금지. 진행 표시는 `style="width:%"` 대신 `<progress>` 요소(`accent-blue-dot`)를 쓴다.
- 이 규칙은 pytest 로 검사한다: `frontend/*.html` 과 화면 스크립트에서 금지 패턴(`style=`, `!important`, `h-7`~`h-10`, 16진 색 직접 입력)을 찾으면 실패하는 정적 검사 테스트.
- 화면 6종: `login` · `meetings` · `detail` · `todos` · `team` · `profile`. 팀이 없는 사용자는 `team.html` 로 보낸다(회의록 · 할 일 화면 진입 시 소속 팀 검사). 끌어 옮기기는 포인터 이벤트(HTML5 draggable 금지).

### 테스트

- pytest 는 각 작업 그룹이 자기 API 의 테스트를 함께 만든다(SQLite 임시 DB, FastAPI `TestClient`). 마지막 그룹에서 전체를 실행해 결과를 보고한다.
- 실제 Gemini 호출 테스트는 `@pytest.mark.gemini` 를 붙이고 `GEMINI_API_KEY` 가 비면 건너뛴다. 응답 내용 비교는 하지 않고 요약 · 결정사항 · 할 일이 구조대로 오는지와 담당자 · 기한 형식만 검증한다.
- 대안으로 가짜 응답만 쓰는 방식을 검토했으나, 사용자가 실제 연결 확인을 요구해 실제 호출 테스트를 별도 표시로 둔다.

### 배포

- Vercel 한 프로젝트에 프론트와 백엔드를 함께 올린다. `pyproject.toml` 의 `[tool.vercel]` 에 진입점을 지정한다. Neon 은 Vercel Storage 로 연결해 `DATABASE_URL` 이 자동 주입된다. `JWT_SECRET` · `GEMINI_*` 는 Vercel 환경변수에 등록한다.
- SQLite 는 배포 환경에서 쓰지 않는다(요청마다 새 환경이라 파일이 남지 않음).

## Risks / Trade-offs

- [Vercel 요청 본문 한도(공식 4.5MB)에 폼 경계가 더해져 4.49MB 부터 플랫폼이 413] → 운영에서 실측해 상한을 4.4MB(4,400,000 바이트)로 정했다. 플랫폼의 413 은 JSON 이 아니라서 화면은 413 을 받으면 상태 코드만으로 같은 안내를 보인다(결정기록 H-3).
- [wav 는 4.4MB 에 22.05kHz 모노 기준 약 1분 40초, 44.1kHz 스테레오 기준 약 25초 분량] → 413 안내 문구에 mp3 권장을 덧붙일지 구현 때 정한다(결정기록 H-1).
- [Gemini 호출 두 곳이 배포 함수 시간 안에 끝나지 않을 수 있음] → 최대 실행 시간 설정을 확인하고, 초과 시 받아쓰기는 502, 정리는 세 칸 비움으로 처리한다(결정기록 H-2).
- [`due_text` 가 자유 글자라 「다음 주 금요일」 은 영영 붉은 띠가 켜지지 않음] → 이번 회차 알려진 한계. 차후 입력 방식 논의(결정기록 H-4).
- [확정 화면에 없는 현재 비밀번호 칸을 구현에서 추가] → 프로그램정의 7-4 의 보안 요구를 지키려고 `profile.html` 에 칸을 하나 더한다. 새 클래스를 만들지 않고 `UI.input` · `UI.label` · `UI.errText` 이름만 쓰며, `publish/profile.html` 은 수정하지 않는다. 스토리보드 J 의 7상태에 「현재 비밀번호 틀림」 1상태가 더해져 8상태가 된다(결정기록 D-024, 이슈보고 R-01).
- [검색 기간을 UTC 날짜로 비교하면 한국 시간과 최대 9시간 어긋남] → 알려진 한계로 두고 차후 보정.
- [`publish/theme.js` 복사본이 갈라짐] → 복사본에서는 이름 추가만 허용하고 기존 값을 바꾸지 않는다. 바꿔야 하면 `publish` 와 같은 값으로 맞추는 작업을 따로 둔다.
