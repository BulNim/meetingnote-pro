# Design

## Context

문서 3종(프로그램정의서 · 스토리보드 · 디자인시스템)과 `publish/` 가 확정본이다. 코드는 아직 없다. 스택은 정의서 9절이 고정한다: FastAPI + SQLAlchemy(로컬 SQLite / 배포 Neon) + Vanilla JS + Tailwind CDN. 로컬 Python 은 3.14.7 이다. `.env` 에는 `GEMINI_API_KEY` · `GEMINI_MODEL` 이 있다(정의서의 `STT_API_KEY` 대신 이 이름을 쓴다). 동기는 proposal.md 의 Why 를 따른다.

## Goals / Non-Goals

**Goals:**
- API 26개의 경로 · 응답 필드 · 오류 `{code, msg}` 를 정의서 7절과 스토리보드 상태에 맞춘다
- 화면은 `publish/` 를 옮겨 쓰고, 화면 ↔ API 연결은 스토리보드 I-01 매핑표와 일치시킨다
- 사람이 Swagger UI 에서, 기계가 pytest 에서 같은 동작을 확인한다

**Non-Goals:**
- Vercel · Neon 배포 실행(분기 코드만 넣고 배포는 하지 않음)
- 디자인 변경, 새 색 · 새 클래스 조합, 새 엔드포인트

## Decisions

**1. 폴더 구조.** `backend/app/` 아래에 `main.py` · `db.py` · `models.py` · `security.py` · `errors.py` · `routers/{auth,team,meeting,todo,comment,activity}.py`, 테스트는 `backend/tests/`, 화면은 `frontend/`. 라우터 이름이 스펙 6묶음과 같다. 정의서 H-01 이 말하는 `frontend/` 를 StaticFiles 로 제공한다.

**2. DB 분기.** `DATABASE_URL` 이 있으면 Postgres, 없으면 `meetingnote.db`(SQLite). SQLAlchemy 한 벌. SQLite 파일은 git 에 넣지 않는다.

**3. 오류 형식.** 모든 오류는 전역 예외 처리기로 `{code, msg}` 를 돌려준다. 검증 오류(FastAPI 기본 422)도 400 `VALIDATION_ERROR` 로 바꾼다. 코드 목록은 정의서 7-2 의 13종만 쓴다.

**4. 인증.** PyJWT HS256, 만료 24시간, 비밀은 `.env` 의 `JWT_SECRET`. 비밀번호는 bcrypt. 만료 · 위조 토큰은 모두 401 `TOKEN_EXPIRED`. 서버 블랙리스트 없음. Swagger 의 Authorize 가 로그인에서 받은 토큰을 붙여넣는 방식이 되도록 `HTTPBearer` 로 선언한다(로그인이 JSON 이라 OAuth2 폼 방식은 맞지 않는다).

**5. 팀 소속.** 한 사용자는 팀 하나에만 속한다고 본다(스토리보드 F-02 "소속 팀 없음", 로그인 후 단일 분기). `GET /api/teams` 는 배열을 돌려주되 항목은 최대 1개이다. 로그인 후 팀 id 는 `login.html` 이 이 API 로 얻어 `localStorage` 에 둔다(proposal 의 결정).

**6. 권한 판정.** owner 전용: 팀 이름 변경 · 초대코드 재발급 · 할 일 삭제(정의서 3절 범위 외). 회의록 · 댓글 삭제는 작성자 + owner. 회의록 수정은 문서에 명시가 없어 삭제와 같은 규칙(작성자 + owner)으로 둔다 — 가정이다.

**7. 받아쓰기.** `transcriber` 모듈 하나가 Gemini 를 부른다(`GEMINI_MODEL` 사용): 1단계 전문 받아쓰기, 2단계 전문을 같은 모델에 넣어 요약 · 결정사항 · 할 일 JSON 으로 구분. 이 모듈이 테스트에서 바꿔 끼우는 유일한 지점이다. 업로드 파일은 응답 후 보관하지 않는다.

**8. 화면 이관.** `publish/*.html` 과 `theme.js` 를 `frontend/` 로 복사한 뒤 각 화면에 공통 `api.js`(fetch 래퍼: 토큰 헤더, 401 처리)를 붙이고 `stateBar` 호출을 제거한다. 색 · 클래스는 `window.UI` · `STRIPE` · `LABEL` 이름만 쓴다. 원본 `publish/` 는 그대로 둔다.

**9. Swagger.** FastAPI 기본 `/docs` 를 켜고 태그를 6묶음 이름으로 나눈다. API 는 모두 `/api/` 접두사. 로컬에서만 쓰는 도구이므로 배포 설정에서는 끌 수 있게 환경변수 하나(`ENABLE_DOCS`, 기본 켬)로 둔다.

**10. 테스트.** pytest + FastAPI TestClient. 테스트마다 임시 SQLite, `transcriber` 는 고정 응답으로 대체(Gemini 실호출 없음). 스펙의 Scenario 를 테스트 이름에 대응시키고, 매핑표 검증 테스트가 `frontend/*.html` 의 호출 경로를 I-01 표와 맞춰 본다.

## Risks / Trade-offs

- [Python 3.14 에서 일부 패키지 휠이 없을 수 있음] → 설치를 가장 먼저 검증하고, 막히면 사용자에게 보고(임의로 버전을 바꾸지 않음)
- [bcrypt 비용이 250ms 목표를 넘음] → 측정해 조정한다. 이 PC 에서 cost 12 는 bcrypt 만 평균 224ms(최대 271ms)라 기준을 넘나들어 기본값을 11(평균 106ms)로 정함. 운영 환경에서 `BCRYPT_ROUNDS` 로 바꿀 수 있음
- [Gemini 응답이 JSON 형식을 어김] → 파싱 실패 시 한 번 재시도, 그래도 실패하면 처리 실패 오류로 응답(새 오류 코드는 만들지 않고 `VALIDATION_ERROR` 계열 대신 500 처리 후 보고)
- [`meetings.html` 진행바의 인라인 `style="width:%"`] → 디자인 시스템의 인라인 금지와 어긋나지만 확정 디자인이므로 그대로 둠(사용자 결정)
- [소속 팀 1개 가정이 틀림] → `GET /api/teams` 가 배열이라 확장 시 응답 형식은 바뀌지 않음
