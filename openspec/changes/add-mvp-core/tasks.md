# Tasks

## 1. 준비

- [x] 1.1 `requirements.txt` · `pyproject.toml`(의존성과 `[tool.vercel] entrypoint = "backend.main:app"`)을 만들고 `pip install -r requirements.txt` 가 끝까지 성공하는지 확인
- [x] 1.2 `.gitignore`(`.env` · `meetingnote.db` · `__pycache__/` · `.venv/` · `.pytest_cache/`)를 만들고, propose 에서 만든 `.env` · `.env.example` 이 `GEMINI_API_KEY` · `GEMINI_MODEL` 두 줄뿐인지 확인
- [x] 1.3 `backend/` · `backend/routers/` · `frontend/` · `tests/` 폴더 뼈대를 만들고 `python -c "import backend.main"` 이 오류 없이 도는지 확인

## 2. 백엔드 공통

- [x] 2.1 `config.py`: 루트 `.env` 를 실행 위치와 상관없이 읽고, 상수(JWT 24h · 업로드 상한 로컬 20MB / 배포 4.5MB · 댓글 500자 · 팀 6명 · 활동 50건)를 둔다. 다른 폴더에서 실행해도 `GEMINI_MODEL` 이 읽히는지 확인
- [x] 2.2 `db.py`: `DATABASE_URL` 있으면 Postgres(`postgresql+psycopg://` 로 바꿈), 없으면 SQLite `meetingnote.db`. 로컬 실행에서 SQLite 파일이 생기는지 확인
- [x] 2.3 `models.py`: 7테이블(users · teams · memberships · meetings · todos · comments · activities)을 정의서 6 의 칼럼대로 만들고, 시작 때 `create_all` 로 7테이블이 생기는지 확인
- [x] 2.4 `errors.py`: `AppError` 와 `{code, msg}` 핸들러, 기본 422 → 400 `VALIDATION_ERROR`, 없는 경로 → 404 `NOT_FOUND`. 잘못된 JSON 요청이 400 `{code,msg}` 로 오는지 확인
- [x] 2.5 `security.py`: bcrypt 해시, JWT(HS256 · 24h) 발급 · 검증, `HTTPBearer` 현재 사용자 의존성. 토큰 없음 · 위조 · 만료가 모두 401 `TOKEN_EXPIRED` 인지 확인
- [x] 2.6 `activity.py`: kind 5종만 받는 기록 함수와 완성 문장(text) 만들기. 5종 밖의 kind 를 넣으면 예외가 나는지 확인
- [x] 2.7 `gemini.py`: 받아쓰기(20MB 초과는 Files API) · 세 항목 구분(JSON 응답 스키마) · 5xx 1회 재시도 · 키 없으면 바로 502. 키가 빈 상태에서 호출하면 502 `VALIDATION_ERROR` 를 내는지 확인
- [ ] 2.8 `main.py`: 라우터 등록 → `/docs`(Authorize 버튼) → `frontend/` StaticFiles 를 맨 마지막에, `/` 는 `/login.html` 로. `uvicorn backend.main:app` 실행 뒤 `/docs` 와 `/login.html` 이 각각 열리는지 확인

## 3. 백엔드 API (27개)

- [x] 3.1 auth 5개(signup · login · me GET · me PUT · logout): 응답 `{token, user}`, user 에 role 포함, 오류 코드는 specs/auth 대로. `/docs` 에서 signup → Authorize → me 가 200 인지 확인
- [x] 3.2 team 6개(POST · GET /api/teams, join, members, code, PUT {id}): 초대코드 `MN-XXXX`, 한 사람 한 팀, 6명 정원(409 `TEAM_FULL`), owner 전용(403 `OWNER_ONLY`), join 은 member_join 기록. `/docs` 에서 생성 → join 흐름 확인
- [x] 3.3 meeting 6개(목록 · 생성 · 단건 · 수정 · 삭제 · upload): 목록에 body 없음과 집계 3종, `?q=` 제목 · 참석자만, `?from=&to=`, 머리 바이트 형식 판정(415), 상한 400, 저장 때 세 항목 구분 · 담당자 대조 · meeting_add / todo_assign 기록, 단건에 body · todos · can_edit, 삭제는 딸린 할 일 · 댓글까지. `/docs` 에서 upload → 생성 → 단건 확인
- [x] 3.4 todo 5개(팀 목록 · 생성 · 수정 · 내 목록 · 삭제): status 다음 due_text 정렬, meeting_title · can_delete, OPEN/DOING/DONE 외 400, DONE 은 todo_done 기록, 담당자 새로 붙으면 todo_assign, 삭제 권한은 만든 사람 · 담당자 · owner. `/docs` 에서 상태 변경 확인
- [x] 3.5 comment 3개(등록 · 목록 · 삭제): 1~500자, created_at 오름차순, can_delete, comment_add 기록, 삭제는 쓴 사람 · owner. `/docs` 에서 등록 → 삭제 확인
- [x] 3.6 activity 2개(팀 · 내 활동): 최신 순 50건, `id · kind · actor_name · text · created_at`. `/docs` 에서 앞 단계 활동이 쌓였는지 확인
- [x] 3.7 `/docs` 에 27개 경로가 모두 보이고 그 밖의 `/api/` 경로가 없는지 확인

## 4. 백엔드 테스트

- [x] 4.1 `tests/conftest.py`: 시험마다 임시 SQLite, `gemini.py` 두 함수를 가짜로 바꾸는 픽스처, 사용자 · 팀 · 토큰 도우미. `pytest --collect-only` 가 오류 없이 도는지 확인
- [x] 4.2 `test_auth.py`: specs/auth 의 시나리오(가입 · 중복 · 약한 비밀번호 · 형식 · 로그인 실패 두 경우 동일 응답 · 만료 토큰 · 토큰 없음 · 내 정보 수정 · 로그아웃 · 오류 본문 `{code,msg}`)가 통과하는지 확인
- [x] 4.3 `test_team.py`: 생성 · 이미 소속 400 · 합류 · 없는 코드 404 · 정원 초과 409 · 재발급 뒤 옛 코드 404 · member 의 owner 전용 403 · todo_count 가 통과하는지 확인
- [x] 4.4 `test_meeting.py`: 목록 필드(body 없음 · 집계) · 정렬 · 검색(본문 제외) · 기간 · 빈 결과 200 · 415(확장자만 바꾼 파일 포함) · 상한 400 · 키 없음 502 · 구분 실패 502 · 담당자 대조(님 · 공백 · 없는 이름) · 수정이 세 항목을 안 바꿈 · 권한 403 · 삭제 연쇄 · 다른 팀 404 가 통과하는지 확인
- [x] 4.5 `test_todo.py`: 직접 등록 · 상태 3종과 되돌림 · 잘못된 상태 400 · 다른 팀 담당자 400 · can_delete 와 403 판정 일치 · 정렬이 통과하는지 확인
- [x] 4.6 `test_comment.py` · `test_activity.py`: 500자 경계 · 순서 · 삭제 권한 · kind 5종만 생김(팀 생성 · 계정 변경 · DOING 은 0건) · 50건 상한이 통과하는지 확인
- [x] 4.7 `test_gemini_live.py`: `GEMINI_API_KEY` 가 있을 때만 `회의_녹음.wav` 를 업로드해 본문이 비지 않고, 그 본문으로 저장하면 summary 가 채워지는지 확인. 키가 없으면 skip 으로 표시되는지 확인
- [ ] 4.8 `pytest -q` 전체를 돌려 통과 · 실패 · skip 수를 사용자에게 보고

## 5. 프런트엔드

- [ ] 5.1 `frontend/theme.js` 를 `publish/theme.js` 에서 복사하고 `stateBar` 만 뺀다. `diff` 로 그 밖의 차이가 없는지 확인
- [ ] 5.2 `frontend/api.js`: 토큰 헤더, 401 `TOKEN_EXPIRED` 면 토큰 삭제 후 `/login.html`, `{code,msg}` 해석, 팀 없으면 team.html 로 보내는 공통 진입 검사. 만료 토큰을 넣고 화면을 열면 로그인 화면으로 가는지 확인
- [ ] 5.3 login.html: publish 마크업 그대로, B-01~B-11 동작(화면 검사 · 처리 중 잠금 · 가입 뒤 join · 초대코드 실패 시 team.html). 브라우저에서 가입 → 로그인 흐름 확인
- [ ] 5.4 meetings.html: C-01~C-11(목록 · 빈 상태 · 검색 · 기간 · 끌어 놓기와 눌러 선택 · 진행 표시 · 415 / 502 안내 · 정리 중 잠금 · 저장 뒤 맨 위). `회의_녹음.wav` 를 끌어 놓아 본문이 채워지는지 확인
- [ ] 5.5 detail.html: D-01~D-13(3단 · 본문 접기 · 수정 · 담당자 · 상태 · 삭제 확인 · 댓글 등록과 삭제 · 없는 회의록). can_edit / can_delete 가 false 인 사용자로 버튼이 꺼지는지 확인
- [ ] 5.6 todos.html: E-01~E-13(탭 · 포인터 끌기 · 눌러서 칸 고르기 · 담당자 배정과 필터 · 기한 지남 띠 · 삭제 잠금 · 빈 상태 · 직접 등록). 마우스 끌기와 360px 에서 눌러 옮기기가 모두 되는지 확인
- [ ] 5.7 team.html: F-01~F-08(소속 팀 없음 두 칸 · 초대코드 오류 · 복사 · 재발급 · 정원 초과 팝업 · 팀 이름 저장 · member 잠금). member 계정으로 잠금 상태 확인
- [ ] 5.8 profile.html: J-01~J-07(이메일 고정 · 이름 변경 · 확인 불일치 · 약한 비밀번호 · 저장 중 잠금 · 내 할 일 · 내 활동 · 로그아웃). 저장 뒤 비밀번호 칸이 비는지 확인
- [ ] 5.9 6개 화면에서 `stateBar` · 인라인 `style=`(진행 막대 width 제외) · `!important` · theme.js 밖의 색 값이 없는지 grep 으로 확인

## 6. 배포 설정

- [ ] 6.1 `vercel.json`(`{"framework": "fastapi"}`) · `.vercelignore`(`.agents/` · `.claude/` · `skills-lock.json` · `.env.local` · `docs/` · `publish/` · `tests/` · `*.wav` · `meetingnote.db`)를 만들고 파일 내용 확인
- [ ] 6.2 `VERCEL` 환경 변수를 켠 로컬 실행에서 업로드 상한이 4.5MB 로 바뀌는지 확인

## 7. 통합 확인

- [ ] 7.1 로컬 서버에서 시나리오 4종(정의서 2: 리더 · 팀원 · 신규 합류자 · 내 정보)을 브라우저로 끝까지 따라가 막히는 곳이 없는지 확인
- [ ] 7.2 360px 폭에서 6개 화면에 가로 스크롤이 없고 카드가 한 열로 접히는지 확인(N-01)
- [ ] 7.3 라이트 · 다크 전환이 6개 화면 모두에서 되는지 확인

## 8. 사람 수락

- [ ] 8.1 (사람) 로컬과 Vercel 배포 주소에서 화면 6종이 publish 와 같은 색 · 배치로 보이고, `회의_녹음.wav` 업로드 → 정리하기 → 할 일 칸반 이동까지 눈으로 확인

## Workflow follow-up

- 사람 수락이 끝나면 `openspec-archive-change` 로 add-mvp-core 를 아카이브한다
