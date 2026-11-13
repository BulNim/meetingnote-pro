# Proposal

## Why

기초편 MeetingNote 는 혼자 쓰는 회의록 정리기라, 팀이 결정사항과 할 일의 행방을 함께 추적할 수 없다. 프로그램 정의서 · 스토리보드(63개 상태) · 퍼블리싱(화면 6종)이 모두 확정되었으므로, 1회차 범위 전체를 change 하나로 구현해 로그인한 팀이 함께 쓰는 회의록 서비스(MeetingNote Pro)를 연다.

## What Changes

- 백엔드(FastAPI)를 새로 만든다. API 27개(`/api/` 접두사), DB 7테이블(users · teams · memberships · meetings · todos · comments · activities)
- 인증: 회원가입 · 로그인 · JWT(24h, 갱신 없음) · bcrypt 해시 · 내 정보 조회와 수정 · 로그아웃
- 팀: 생성 · 목록 · 초대코드(`MN-XXXX`) 발급과 재발급 · 합류 · 멤버 목록 · 팀 이름 변경. 한 사람은 한 팀, 팀당 6명, owner / member 두 등급
- 회의록: 녹취(mp3 · wav) 업로드와 Gemini 받아쓰기, 저장할 때 본문을 요약 · 결정사항 · 할 일로 구분, CRUD, 제목 · 참석자 검색과 기간 조회
- 할 일 칸반: 대기(OPEN) · 진행(DOING) · 완료(DONE) 3열, 회의록에서 뽑히거나 직접 등록, 끌어서 또는 눌러서 상태 변경, 담당자 배정, 삭제
- 댓글: 회의록에 등록 · 목록 · 삭제 (500자 이내)
- 활동 기록: kind 5종(meeting_add · todo_assign · todo_done · comment_add · member_join)을 팀 활동 · 내 활동으로 조회
- 프런트엔드(Vanilla JS + Tailwind CDN): `publish/` 의 화면 6종과 `theme.js` 를 확정 디자인으로 삼아 마크업 · 클래스를 그대로 옮기고 API 를 연결한다. 퍼블리싱 확인용 STATE 바와 장면 해설 글은 넣지 않는다
- Swagger UI(`/docs`)에서 JWT 를 넣고 API 를 직접 시험할 수 있게 한다
- 로컬은 SQLite + 정적 파일 일체형, 배포는 Vercel + Neon Postgres. `DATABASE_URL` 유무로 갈린다. 배포 설정 파일(`vercel.json` · `pyproject.toml` entrypoint · `.vercelignore`)까지 만든다
- 업로드 상한: 로컬 20MB(초과분은 Gemini Files API), 배포 4.5MB(Vercel 요청 본문 한도)
- 환경 변수 파일 `.env` · `.env.example` 은 `GEMINI_API_KEY` · `GEMINI_MODEL` 두 줄뿐이다

### Out of Scope

- 실시간 녹음(브라우저 녹음) - 파일 업로드만 지원
- 화자 자동 구분 - 본문은 단일 블록
- 외부 연동 - 캘린더 연동 · 메일 발송 없음
- 권한 등급 확장 - owner / member 둘뿐
- 푸시 알림 - 활동 기록 화면 표시까지만
- 큰 녹취 파일의 배포 환경 직접 업로드(Blob 저장소 등) - 배포에서는 4.5MB 까지만

## Capabilities

### New Capabilities

- `auth`: 회원가입 · 로그인 · 토큰 인증 · 내 정보 조회와 수정 · 로그아웃, 그리고 로그인 화면(login.html)의 동작
- `team`: 팀 생성 · 초대코드 · 합류 · 멤버 · 팀 이름과 owner 전용 권한, 그리고 팀 설정 화면(team.html)의 동작
- `meeting`: 녹취 업로드와 받아쓰기, 요약 · 결정사항 · 할 일 구분, 회의록 CRUD · 검색, 그리고 회의록 목록(meetings.html) · 상세(detail.html) 화면의 동작
- `todo`: 할 일 칸반의 조회 · 등록 · 상태 변경 · 담당자 배정 · 삭제, 그리고 칸반 화면(todos.html)의 동작
- `comment`: 회의록 댓글의 등록 · 목록 · 삭제와 상세 화면 댓글 영역의 동작
- `activity`: 팀 활동 · 내 활동 기록의 생성 규칙과 조회, 내 정보 화면(profile.html)의 할 일 · 활동 영역

### Modified Capabilities

(없음 - 첫 change)

## Impact

- 새 코드: `backend/`(FastAPI 앱 · 라우터 · ORM 모델 · Gemini 호출), `frontend/`(화면 6종 + `theme.js`), `tests/`(pytest)
- 새 설정: `.env` · `.env.example` · `.gitignore` · `pyproject.toml` · `requirements.txt` · `vercel.json` · `.vercelignore`
- 새 의존성: fastapi · uvicorn · sqlalchemy · psycopg(배포 Postgres) · pyjwt · bcrypt · python-multipart · python-dotenv · google-genai · pytest · httpx
- 외부 서비스: Gemini API(받아쓰기 · 세 항목 구분), Vercel(배포), Neon Postgres(배포 DB)
- `publish/` 와 `docs/` 는 참고 자료로만 쓰고 고치지 않는다
