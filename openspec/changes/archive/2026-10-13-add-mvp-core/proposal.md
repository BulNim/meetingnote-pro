# Proposal

## Why

기초편 MeetingNote 의 확장 항목(JWT 로그인 · 팀 공유)을 심화편으로 구현한다. 프로그램정의서 · 스토리보드(화면 6종 · 상태 62종) · 디자인 시스템 · `publish/` 퍼블리싱이 모두 확정되어, AI 가 임의로 정할 자리가 없는 상태에서 1회차로 기능 6종을 한 번에 구현한다.

## What Changes

- FastAPI 백엔드 신설: API 26개, DB 7테이블(users · teams · memberships · meetings · todos · comments · activities), 로컬 SQLite / 배포 Neon Postgres 한 줄 분기(`DATABASE_URL`)
- `publish/` 의 6개 화면(login · meetings · detail · todos · team · profile)을 `frontend/` 로 옮겨 API 에 연결. 색 · 클래스는 `theme.js` 의 `window.UI` · `STRIPE` · `LABEL` 이름만 쓰고 새 조합 · 새 색을 만들지 않음. `stateBar` 는 넣지 않음
- 화면과 API 의 연결은 스토리보드 I-01 통합 매핑표(73쪽)를 그대로 따름. 표에 없는 경로는 만들지 않음
- 녹취 업로드(25MB · mp3 wav) → Gemini 받아쓰기 → 요약 · 결정사항 · 할 일 3항목 구분 (키는 `.env` 의 `GEMINI_API_KEY` · `GEMINI_MODEL`)
- Swagger UI(`/docs`) 활성화: 화면 없이 브라우저에서 JWT 를 넣고 API 26개를 직접 호출해 볼 수 있게 함 (스펙 단위가 아니라 design · tasks 로 다룸)
- pytest 작성 · 실행 · 결과 보고. 외부 Gemini 호출은 mock 으로 막음
- 로그인 직후 소속 팀 확인은 `login.html` 이 `GET /api/teams` 로 하고 팀 id 를 `localStorage` 에 저장 (매핑표 login 행에 경로 1개 추가, 고유 경로는 26개 그대로)
- 범위 외(만들지 않음): 실시간 녹음 · 화자 자동 구분 · 외부 연동 · owner/member 외 권한 등급 · 분할 업로드 · 푸시 알림

## Capabilities

### New Capabilities
- `auth`: 회원가입 · 로그인 · JWT(24h) 발급 · bcrypt 해시 · 내 정보 조회와 수정 · 로그아웃
- `team`: 팀 생성 · 초대코드 발급과 재발급 · 합류 · 멤버 목록 · 팀 이름 변경(owner)
- `meeting`: 녹취 업로드와 받아쓰기 · 3항목 구분 · 회의록 CRUD · 제목과 참석자 검색 · 기간 필터
- `todo`: 대기 · 진행 · 완료 3열 칸반 · 상태 변경 · 담당자 배정 · 삭제 · 내 할 일
- `comment`: 회의록 댓글 달기 · 목록 · 삭제(작성자와 owner)
- `activity`: 팀 활동과 내 활동 기록(kind 5종)

### Modified Capabilities
(없음 - `openspec/specs/` 가 비어 있음)

## Impact

- 신규 코드: `backend/`(FastAPI · SQLAlchemy · 테스트), `frontend/`(publish 에서 이관)
- 의존성: fastapi · uvicorn · sqlalchemy · bcrypt · PyJWT · python-multipart · google-genai(또는 동급 SDK) · pytest · httpx
- 환경: `.env`(`GEMINI_API_KEY` · `GEMINI_MODEL` · `JWT_SECRET` · `DATABASE_URL` 선택), Python 3.14. 배포(Vercel + Neon)는 이 change 의 구현 범위에 넣지 않고 로컬 동작까지만 다룸
- 기존 `docs/` · `publish/` 는 원본으로 보존하고 수정하지 않음
