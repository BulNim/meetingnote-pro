# Tasks

## 1. 백엔드 기반

- [x] 1.1 `backend/` 구조(`app/`, `routers/`, `services/`, `tests/`)와 `pyproject.toml` · 의존성(FastAPI, SQLAlchemy, bcrypt, PyJWT, pytest, httpx, Gemini SDK)을 만들고, `uvicorn app.main:app` 이 기동되는지 확인한다
- [x] 1.2 `config.py` 가 `.env` 에서 `GEMINI_API_KEY` · `GEMINI_MODEL` 을 읽고, `JWT_SECRET` · CORS 는 코드 기본값을 쓰게 만든다. `.env.example`(이름만 두 줄)을 만들고, `.env` 가 git 에서 무시되는지 `git check-ignore` 로 확인한다
- [x] 1.3 `db.py` 가 `DATABASE_URL` 이 있으면 Postgres, 없으면 `meetingnote.db` SQLite 를 고르게 하고 `.gitignore` 에 SQLite 파일을 더한다. 테스트: 환경변수 유무에 따라 엔진 URL 이 바뀌는 단위 테스트가 통과한다
- [x] 1.4 `models.py` 에 테이블 7개(`users` · `teams` · `memberships` · `meetings` · `todos` · `comments` · `activities`)를 만든다. 사용자당 멤버십 1행, `activities.kind` 5종 제약, 회의록 삭제 cascade 를 포함한다. 테스트: 제약 위반 삽입이 실패하고 cascade 삭제가 동작하는 테스트가 통과한다
- [x] 1.5 `errors.py` 에 `{code, msg}` 예외 핸들러와 16개 코드를 만든다. 테스트: 임의 오류 응답의 본문이 `code` · `msg` 두 키이고 집합 밖의 코드가 없는 테스트가 통과한다
- [x] 1.6 `main.py` 가 라우터를 먼저 등록하고 `frontend/` 를 마지막에 정적 파일로 연결하며, Bearer 스킴으로 `/docs` · `/openapi.json` 을 연다. 테스트: `/docs` 가 200 으로 Swagger UI 를 돌려주고 정적 연결 뒤에도 가려지지 않는다

## 2. 인증 (auth)

- [x] 2.1 `security.py` 에 bcrypt 해시와 JWT 발급 · 검증(24시간, `TOKEN_EXPIRED` / `UNAUTHORIZED` 구분)을 만든다. 테스트: 만료 토큰 · 변조 토큰 · 토큰 없음이 각각 올바른 코드로 거절되는 테스트가 통과한다
- [x] 2.2 `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/logout` 을 만든다. 테스트: 정상 가입 201 + JWT, `EMAIL_INVALID` · `EMAIL_DUPLICATED` · `PASSWORD_TOO_WEAK`, 로그인 실패가 이메일 존재와 상관없이 같은 `INVALID_CREDENTIALS` 인 것을 확인한다
- [x] 2.3 `GET` · `PUT /api/auth/me` 를 만든다(`role` 포함, 이름만 보내면 비밀번호 유지, 새 비밀번호는 `current_password` 확인 필수). 테스트: owner 배지용 `role`, 이름만 변경, 현재 비밀번호 틀림 401 `INVALID_CREDENTIALS`, 약한 새 비밀번호 400 이 통과한다

## 3. 팀 (team)

- [x] 3.1 `POST /api/teams`, `GET /api/teams` 를 만든다(`MN-XXXX` 코드, 만든 사람 owner, 이미 팀이 있으면 `VALIDATION_ERROR`, 팀 생성은 활동 없음). 테스트: 코드 형식과 한 사람 한 팀 제약이 통과한다
- [x] 3.2 `POST /api/teams/join` 을 만든다(`INVITE_NOT_FOUND`, `TEAM_FULL` 6명, 이미 팀 있음). 테스트: 정상 합류 · 없는 코드 · 정원 초과가 통과하고 실패해도 계정이 남는다
- [x] 3.3 `PUT /api/teams/{id}`(이름), `PUT /api/teams/{id}/code`(재발급) 를 owner 전용으로 만든다. 테스트: member 는 `OWNER_ONLY`, 재발급 뒤 이전 코드로는 합류 불가, 기존 멤버 유지가 통과한다
- [x] 3.4 `GET /api/teams/{id}/members` 를 만든다(`todo_count` 는 배정 전체 수). 다른 팀의 `{id}` 는 404 로 응답한다. 테스트: `todo_count` 와 남의 팀 404 가 통과한다

## 4. 활동 기록 (activity)

- [x] 4.1 `services/activity.py` 에 기록 함수와 문장 만들기(5종)를 만들고, 합류(3.2)에 `member_join` 을 연결한다. 테스트: 합류가 `member_join` 한 건을 남기고 팀 생성 · 이름 변경은 남기지 않는다
- [x] 4.2 `GET /api/teams/{id}/activities`, `GET /api/me/activities` 를 만든다(최근 순, 최대 50건, 내 활동은 행위자 기준). 테스트: 60건 중 50건, 내 것만, 빈 배열이 통과한다

## 5. 회의록 (meeting)

- [x] 5.1 `services/gemini.py` 에 받아쓰기 함수와 세 항목 구분 함수를 만든다(JSON 스키마 응답, 담당자 이름은 멤버와 일치할 때만 id 로 변환, 기한은 원문 또는 `미정`). 테스트: 가짜 클라이언트로 구조 변환 · 담당자 미정 · 호출 실패 시 빈 세 항목 처리가 통과한다
- [x] 5.2 `POST /api/upload` 를 만든다(내용 형식 검사 mp3/wav → `UNSUPPORTED_MEDIA_TYPE`, 4.4MB 초과 → `PAYLOAD_TOO_LARGE`, 길이 검사 없음, Gemini 실패 → 502 `UPSTREAM_ERROR`, 파일 미저장). 테스트: 정상(mp3 · wav 둘 다) · 415 · 413 · 502 · 확장자만 바꾼 파일이 통과하고, 시험 파일 `회의_녹음.wav`(4,390,962 바이트)가 413 없이 올라간다
- [x] 5.3 `POST /api/teams/{id}/meetings` 를 만든다(필수 항목 검사, 본문 보존, 할 일 생성, `meeting_add` 활동, 정리 실패 시에도 201). 테스트: 정상 · `VALIDATION_ERROR` · 정리 실패 시 세 칸 비움 · 활동 한 건이 통과한다
- [x] 5.4 `GET /api/teams/{id}/meetings`(`met_at` 내림차순, 개수 3종, `body` 없음, `?q` 제목과 참석자만, `?from` · `?to` 양 끝 포함) 를 만든다. 테스트: 본문은 검색되지 않음, 참석자 검색, 기간 거름, 빈 배열이 통과한다
- [x] 5.5 `GET` · `PUT` · `DELETE /api/meetings/{id}` 를 만든다(올린 사람 또는 owner, 본문 수정해도 세 항목 유지, 삭제 시 할 일 · 댓글 cascade, 없는 id 는 `MEETING_NOT_FOUND`). 테스트: 다른 member 는 `FORBIDDEN`, cascade, 404 가 통과한다

## 6. 할 일 (todo)

- [x] 6.1 `GET /api/teams/{id}/todos`, `GET /api/me/todos` 를 만든다(`meeting_title` 포함, `status` 다음 `due_text` 정렬). 테스트: 내 것만 · 팀 전체 · 빈 배열이 통과한다
- [x] 6.2 `PUT /api/todos/{id}` 를 만든다(`status` · `assignee_id`(미정 허용, 같은 팀 멤버만) · `due_text` 자유 글자 저장, `todo_done` 은 DONE 이 될 때, `todo_assign` 은 새 담당자가 생길 때). 테스트: 활동이 규칙대로만 남고 다른 팀 사용자 배정은 `VALIDATION_ERROR` 인 것이 통과한다
- [x] 6.3 `DELETE /api/todos/{id}` 를 owner 전용으로 만든다. 테스트: owner 204, member `OWNER_ONLY` 가 통과한다

## 7. 댓글 (comment)

- [x] 7.1 `POST` · `GET /api/meetings/{id}/comments` 를 만든다(500자 이내, 오름차순, `can_delete` 판정, `comment_add` 활동). 테스트: 501자 거절, `can_delete` 가 쓴 사람과 owner 만 참, 활동 한 건이 통과한다
- [x] 7.2 `DELETE /api/comments/{id}` 를 만든다(쓴 사람 또는 owner). 테스트: 다른 member 는 `FORBIDDEN`, 쓴 사람은 204 가 통과한다

## 8. 프론트엔드 기반

- [x] 8.1 `frontend/theme.js` 를 `publish/theme.js` 복사본으로 시작하고, 규칙 위반을 풀기 위해 필요한 이름(선택 박스 · 날짜 입력 · 텍스트영역 · 탭 · 내비 링크 등)을 `UI` 에만 더한다. 기존 값은 바꾸지 않는다. 확인: `publish/theme.js` 와 비교해 추가분만 다르다
- [x] 8.2 공통 스크립트를 만든다(API 호출 한 곳, 토큰 저장 · 401 `TOKEN_EXPIRED` 처리 후 로그인 화면 이동, 소속 팀 검사 후 이동, 사람이 읽는 토스트). 확인: 만료 토큰으로 어느 화면을 열어도 로그인 화면의 세션 만료 안내로 가는 것을 서버를 띄워 확인한다
- [x] 8.3 디자인 규칙 정적 검사 테스트를 만든다(`frontend/` 에서 `style=` · `!important` · `h-7`~`h-10` · 16진 색 직접 입력 · `stateBar` 호출을 찾으면 실패). 확인: 위반을 일부러 넣으면 실패하고 되돌리면 통과한다

## 9. 로그인 / 회원가입 화면 (login.html)

- [x] 9.1 `login.html` 을 `publish/login.html` 과 같은 구조로 만들되 `UI` 이름만 쓴다. 로그인 · 회원가입 전환, 제출 전 검증, 처리 중 버튼 잠금, 오류 위치(입력 아래 vs 상자)를 스토리보드 B-01 ~ B-11 11종과 맞춘다. 확인: 11종 상태를 서버를 띄워 직접 재현해 `publish` 와 같은지 확인하고 8.3 테스트가 통과한다
- [x] 9.2 가입 후 초대코드 합류 실패(B-11) 때 계정을 유지한 채 팀 화면으로 보내는 흐름을 연결한다. 확인: 없는 코드로 가입하면 계정이 만들어지고 팀 화면(소속 팀 없음)이 열린다

## 10. 회의록 목록 화면 (meetings.html)

- [x] 10.1 `meetings.html` 에 목록 · 빈 상태 · 검색 · 기간 · 카드 띠 색 순환(blue → green → orange → purple → red)을 만든다. 확인: C-01 ~ C-04 상태를 재현해 `publish` 와 같은지 확인한다
- [x] 10.2 새 회의록 패널을 만든다(제목 · 회의 시각 · 참석자 · 업로드 · 본문, 올리는 중 `<progress>`, 415 · 413 · 502 알림, 「mp3 · wav · 4.4MB 이하」 문구, 저장 중 잠금, 저장 후 초기화). 확인: C-05 ~ C-11 상태를 재현하고 4.4MB 초과와 mp4 업로드가 해당 알림을 보이는 것을 확인한다

## 11. 회의록 상세 화면 (detail.html)

- [x] 11.1 세 칸 · 본문 접기 · 수정 · 삭제 확인을 만든다(수정 · 삭제 버튼 44px). 확인: D-01 ~ D-08, D-13 상태를 재현하고 삭제 취소 시 아무것도 지워지지 않는다
- [x] 11.2 할 일 칸의 담당자 선택과 댓글 입력 · 목록 · 삭제를 연결한다(500자, `can_delete`). 확인: D-03, D-04, D-09 ~ D-12 상태를 재현하고 남의 댓글에는 삭제 버튼이 없다

## 12. 할 일 칸반 화면 (todos.html)

- [x] 12.1 3열 칸반 · 내 할 일 / 전체 탭 · 담당자 필터(서버 재호출 없음) · 빈 상태를 만든다. 확인: E-01, E-02, E-07, E-10, E-12 상태를 재현한다
- [x] 12.2 포인터 이벤트 끌어 옮기기 · 눌러서 칸 고르기 · 담당자와 기한 배지 변경 · 기한 지남 띠(날짜 형식과 「어제」 · 「지난 주」 · 「지난 달」) · owner 전용 삭제(member 는 비활성)를 연결한다. 확인: E-03 ~ E-06, E-08, E-09, E-11 상태를 재현하고 이동 실패 시 카드가 되돌아오는 것을 확인한다

## 13. 팀 설정 화면 (team.html)

- [x] 13.1 팀 만들기 / 합류(소속 팀 없음) · 팀 정보 · 코드 복사와 재발급 · 이름 저장 · 멤버 목록 · 활동 기록을 만든다. 확인: F-01 ~ F-07 상태를 재현한다(이름 저장 버튼은 `btnPrimary`)
- [x] 13.2 member 읽기 전용(F-08)과 정원 초과(F-06) 알림을 만든다. 확인: member 계정으로 입력과 버튼이 비활성이고 7번째 합류가 `TEAM_FULL` 알림을 보인다

## 14. 내 정보 화면 (profile.html)

- [x] 14.1 이름 · 현재 비밀번호(구현에서 추가) · 새 비밀번호 · 확인 · 저장 · 로그아웃 · 내 할 일 · 내 활동을 만든다(불일치는 서버로 보내지 않음, 활동 없음 빈 상태). 확인: J-01 ~ J-07 상태를 재현하고, 추가한 「현재 비밀번호 틀림」 상태가 `UI` 이름만으로 그려지며 8.3 정적 검사가 통과한다

## 15. 배포

- [x] 15.1 Vercel 진입점(루트 `index.py`, 제로 설정)과 `.vercelignore` 를 만들고, 환경변수(`JWT_SECRET` · `GEMINI_API_KEY` · `GEMINI_MODEL` 은 직접 등록, `DATABASE_URL` 은 Neon 통합이 주입)를 정리했다. Vercel 문서와 운영 실측으로 요청 본문 한도와 함수 시간을 확인해 `docs/결정기록.md` 의 H-2 · H-3 을 갱신했다. 확인: 갱신된 문서와 설정 파일이 존재한다
- [x] 15.2 Vercel CLI 로 배포해 `/login.html` · `/docs` 가 열리고 가입 → 로그인 → 받아쓰기 → 저장 → 칸반까지 동작하며, 4,400,000 바이트 파일은 통과하고 4,400,001 바이트부터 413 `PAYLOAD_TOO_LARGE` 가 되는 것을 확인했다. Neon DB 를 새로 만들어 테이블 7개를 마이그레이션했다

## 16. 통합 검증

- [x] 16.1 `pytest` 를 전체 실행(`gemini` 표시 포함)해 통과 · 실패 · 건너뜀 수와 실패 내용을 사용자에게 보고한다. 실제 호출 테스트는 `회의_녹음.wav` 로 받아쓰기와 세 항목 구분까지 돌린다. 확인: 실행 로그와 요약을 보고에 붙인다
- [x] 16.2 360px 폭에서 가로 스크롤이 없고 카드가 한 열로 접히고 글자가 잘리지 않는지 3화면(목록 · 상세 · 칸반)을 확인한다. 확인: 확인한 화면 목록과 결과를 보고에 적는다

## 17. 수락 확인 (사람이 눈으로)

- [x] 17.1 (사람이 확인) 화면 6종을 라이트와 다크 모드, 360px 폭에서 `publish/` 의 같은 화면과 나란히 열어 색 · 띠 · 버튼 높이가 같게 보이는지 눈으로 확인하고 이 칸을 직접 체크한다 (내 정보 화면은 현재 비밀번호 칸 하나가 더 있는 것이 정상)
