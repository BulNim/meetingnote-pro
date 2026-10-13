# Tasks

## 1. 백엔드 뼈대

- [ ] 1.1 `backend/` 구조(`app/` · `routers/` · `tests/`)와 `requirements.txt`(fastapi · uvicorn · sqlalchemy · bcrypt · PyJWT · python-multipart · google-genai · pytest · httpx)를 만들고 `pip install -r requirements.txt` 가 Python 3.14 에서 성공하는지 확인
- [ ] 1.2 `db.py` 에 `DATABASE_URL` 유무로 Postgres / SQLite 를 가르는 한 줄 분기와 7테이블 모델(`models.py`)을 만들고, 테스트로 빈 DB 에 7테이블이 생기는지 확인
- [ ] 1.3 `errors.py` 에 `{code, msg}` 전역 예외 처리기(13종 코드, 검증 오류 → 400 `VALIDATION_ERROR`)를 만들고, 테스트로 존재하지 않는 경로와 잘못된 입력이 같은 형식으로 응답하는지 확인
- [ ] 1.4 `security.py` 에 bcrypt 해시 · JWT(24h) 발급과 검증, 인증 의존성(만료 → 401 `TOKEN_EXPIRED`)을 만들고, 단위 테스트로 발급 · 만료 · 위조 3경우를 확인. `JWT_SECRET` 은 환경에서 읽고 `.env` 파일은 수정하지 않음
- [ ] 1.5 `.gitignore` 에 `.env` · `*.db` · `__pycache__/` · `회의_녹음.wav` 를 넣고 `git status` 에 해당 파일이 나타나지 않는지 확인

## 2. auth (스펙 `auth`)

- [ ] 2.1 `POST /api/auth/signup` · `POST /api/auth/login` 을 구현하고 가입 성공 · EMAIL_INVALID · EMAIL_DUPLICATED · PASSWORD_TOO_WEAK · 로그인 성공 · INVALID_CREDENTIALS 시나리오 pytest 가 통과하는지 확인
- [ ] 2.2 `GET /api/auth/me` · `PUT /api/auth/me` · `POST /api/auth/logout` 을 구현하고 이름 변경 · 약한 새 비밀번호 · 만료 토큰 시나리오 pytest 가 통과하는지 확인
- [ ] 2.3 `password_hash` 가 bcrypt 이고 응답 어디에도 비밀번호가 없다는 pytest, 로그인 평균 250ms 이내 측정 pytest 가 통과하는지 확인

## 3. team (스펙 `team`)

- [ ] 3.1 `POST /api/teams` · `GET /api/teams`(빈 배열 포함) · 초대코드 `MN-XXXX` 발급을 구현하고 팀 만들기 · 소속 팀 없음 시나리오 pytest 가 통과하는지 확인
- [ ] 3.2 `POST /api/teams/join` 을 구현하고 합류 성공(`member_join` 기록) · INVITE_NOT_FOUND · TEAM_FULL(6명) 시나리오 pytest 가 통과하는지 확인
- [ ] 3.3 `GET /api/teams/{id}/members`(`todo_count` 포함) · `PUT /api/teams/{id}` · `PUT /api/teams/{id}/code` 를 구현하고 owner 성공 · member OWNER_ONLY · 옛 코드 무효 · 다른 팀 접근 FORBIDDEN pytest 가 통과하는지 확인

## 4. meeting (스펙 `meeting`)

- [ ] 4.1 `transcriber` 모듈(Gemini 2단계: 받아쓰기 → 3항목 구분)과 `POST /api/upload`(25MB · mp3 wav 제한)를 구현하고, Gemini 를 고정 응답으로 바꾼 pytest 로 완료 · 413 · 415 시나리오가 통과하는지 확인. 정상 파일 샘플은 `회의_녹음.wav`(약 4.4MB)를 쓰고, 파일이 없는 환경에서는 그 테스트를 건너뜀
- [ ] 4.2 `POST /api/teams/{id}/meetings`(할 일 동시 저장 · `meeting_add` 기록)와 `GET /api/teams/{id}/meetings`(집계 필드 · `met_at` 내림차순 · body 제외 · 빈 배열)를 구현하고 저장 · 필수 누락 · 목록 · 빈 목록 pytest 가 통과하는지 확인
- [ ] 4.3 `?q=`(제목 · 참석자만) · `?from=&to=` 를 구현하고 제목 검색 · 본문 단어 0건 · 기간 필터 pytest 가 통과하는지 확인
- [ ] 4.4 `GET` · `PUT` · `DELETE /api/meetings/{id}`(작성자 + owner, 하위 할 일 · 댓글 연쇄 삭제, `decision_count` 계산)를 구현하고 상세 · MEETING_NOT_FOUND · 작성자 삭제 · 남의 회의록 FORBIDDEN pytest 가 통과하는지 확인

## 5. todo (스펙 `todo`)

- [ ] 5.1 `GET /api/teams/{id}/todos` · `GET /api/me/todos` 를 구현하고 정렬(`status` → `due_text`) · `meeting_title` · 빈 배열 pytest 가 통과하는지 확인
- [ ] 5.2 `PUT /api/todos/{id}`(상태 · 담당자, `todo_assign` · `todo_done` 기록)와 `DELETE /api/todos/{id}`(owner 전용)를 구현하고 완료 이동 · 잘못된 상태 · 팀 밖 담당자 · OWNER_ONLY pytest 가 통과하는지 확인

## 6. comment · activity (스펙 `comment` · `activity`)

- [ ] 6.1 댓글 3개 API 를 구현하고 등록(`comment_add`) · 501자 거절 · `can_delete` 판정 · 남의 댓글 FORBIDDEN · owner 삭제 pytest 가 통과하는지 확인
- [ ] 6.2 `GET /api/teams/{id}/activities` · `GET /api/me/activities` 를 구현하고 kind 5종 고정 · 최신순 50건 제한 · 빈 배열 pytest 가 통과하는지 확인

## 7. Swagger UI

- [ ] 7.1 `/docs` 를 켜고 태그를 `auth · team · meeting · todo · comment · activity` 6묶음으로 나누며 `HTTPBearer` Authorize 를 붙이고, pytest 로 `/openapi.json` 의 경로 · 메서드 조합이 정확히 26개이고 모두 `/api/` 로 시작하는지 확인
- [ ] 7.2 `uvicorn app.main:app --reload` 로 띄워 `http://127.0.0.1:8000/docs` 가 열리고, 로그인 응답의 JWT 를 Authorize 에 넣으면 인증 API 가 200 으로 호출되는지 확인

## 8. 화면 연결 (`frontend/`)

- [ ] 8.1 `publish/` 의 6개 화면과 `theme.js` 를 `frontend/` 로 복사하고 `stateBar` 호출을 제거한 뒤, 같은 서버가 `/login.html` 처럼 확장자를 붙인 경로로 제공하는지 확인. 원본 `publish/` 는 변경하지 않음(파일 해시 비교)
- [ ] 8.2 공통 `api.js`(토큰 헤더 · 401 TOKEN_EXPIRED 시 토큰 삭제 후 로그인으로 이동)와 `login.html` · `team.html` 연결(로그인 후 `GET /api/teams` → 팀 id 저장 → 분기, 초대코드 합류, 코드 복사)을 구현하고 스토리보드 B · F 의 상태 19종이 화면에서 재현되는지 확인
- [ ] 8.3 `meetings.html` · `detail.html` 연결(목록 · 검색 · 기간 · 업로드 진행 · 저장, 상세 · 수정 · 삭제 · 댓글)을 구현하고 스토리보드 C · D 의 상태 24종이 재현되는지 확인
- [ ] 8.4 `todos.html` · `profile.html` 연결(포인터 이벤트 끌기와 눌러서 칸 고르기, 내 정보 수정 · 내 할 일 · 내 활동)을 구현하고 스토리보드 E · J 의 상태 19종이 재현되는지 확인
- [ ] 8.5 pytest 매핑표 테스트: `frontend/*.html` 과 `api.js` 에서 호출하는 경로를 모아 스토리보드 I-01 표(login 행의 `GET /api/teams` 추가분 포함)와 일치하고, 쓰이지 않는 경로가 0개이며, 인라인 `!important` · 새 색이 없는지 확인

## 9. 통합 검증과 보고

- [ ] 9.1 `pytest` 전체를 실행해 통과 · 실패 · 건너뜀 수와 실패 내용을 사용자에게 그대로 보고(실패는 숨기지 않음)

## 10. 사람 수락 확인

- [ ] 10.1 사람이 브라우저로 `http://127.0.0.1:8000/docs` 를 열어 회원가입 → 로그인 → Authorize 에 JWT 입력 → 팀 생성 → `회의_녹음.wav` 를 `/api/upload` 로 올려 실제 Gemini 받아쓰기와 3항목 구분 결과 확인 → 회의록 저장 → 할 일 상태 변경까지 직접 호출해 모두 의도한 응답이 오는지 눈으로 확인
