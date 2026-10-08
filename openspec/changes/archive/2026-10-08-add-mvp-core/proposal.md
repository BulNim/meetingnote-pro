# Proposal

## Why

MeetingNote Pro 는 로그인한 팀이 함께 쓰는 회의록이다. 녹취를 받아쓴 본문을 요약 · 결정사항 · 할 일로 나누고, 할 일은 칸반으로 추적하며, 댓글과 활동 기록을 남긴다. 기획 자료(프로그램정의 · 스토리보드 · 디자인시스템)와 확정 퍼블리싱(`publish/`)은 끝났고 구현체가 없다. 스펙을 먼저 확정해 같은 입력에서 같은 산출물이 나오게 한다.

## What Changes

- FastAPI 백엔드 신규: API 26개, DB 7테이블 (스토리보드 I-01 통합 매핑표 기준. 경로를 더하지 않음)
- 바닐라 JS 프론트엔드 신규: 화면 6종과 상태 62종. `publish/` 의 클래스 규칙과 `theme.js` 이름을 그대로 쓰고, 규칙 위반 부분은 규칙에 맞게 고쳐 구현
- 녹취 받아쓰기와 요약 · 결정사항 · 할 일 구분은 Google Gemini 한 모델로 처리 (키는 `.env`)
- 업로드 상한은 원본 25MB 에서 **4.4MB** 로 낮춤 (사용자 결정. 배포 환경의 요청 본문 한도는 구현 전에 확인). **BREAKING**: 원본 문서의 25MB 를 따르지 않음
- 받아쓰기 60초 규칙은 **폐기**. 어떤 상황에도 60초 값을 적용하지 않음
- Swagger UI(`/docs`) 를 켜서 화면에서 API 를 시험할 수 있게 함
- 로컬은 SQLite, 배포는 Vercel + Neon Postgres. `DATABASE_URL` 유무로 한 줄 분기
- 개발이 끝나면 pytest 를 실행해 결과를 보고 (실제 Gemini 호출 테스트 포함)

## Capabilities

### New Capabilities

- `auth`: 회원가입 · 로그인 · 로그아웃 · 내 정보 조회와 수정. JWT 24시간, 세션 만료 처리, 공통 오류 형식, API 문서 화면
- `team`: 팀 생성 · 초대코드 합류와 재발급 · 멤버 목록 · 팀 이름 변경. 한 사람 한 팀, 팀당 6명, owner 와 member 두 등급
- `meeting`: 녹취 업로드와 받아쓰기, 회의록 저장과 세 항목 구분, 목록 · 검색 · 상세 · 수정 · 삭제
- `todo`: 회의에서 나온 할 일의 칸반 3열, 상태 · 담당자 · 기한 변경, 삭제(owner), 내 할 일과 팀 전체
- `comment`: 회의록 댓글 등록 · 목록 · 삭제
- `activity`: 팀 활동과 내 활동 기록. 행위 5종의 기록 규칙과 표시 문장

### Modified Capabilities

없음. `openspec/specs/` 가 비어 있어 전부 신규다.

## Impact

- 신규 디렉터리: `backend/` (FastAPI · SQLAlchemy · pytest), `frontend/` (HTML · `theme.js` · 화면별 JS)
- 신규 파일: `.env.example`, `pyproject.toml`, `index.py`(Vercel 진입점), `.vercelignore`, `backend/migrate.py`(Neon 테이블 생성). `.env` 와 `.gitignore` 는 이미 준비됨
- 외부 의존: Google Gemini API (`GEMINI_API_KEY` · `GEMINI_MODEL`), Neon Postgres (배포), Vercel (배포)
- 기존 `publish/` 와 `docs/` 는 수정하지 않는다 (구현체가 규칙을 어긴 곳만 `frontend/` 에서 고침)
- 범위 외(Out of Scope): 실시간 녹음, 화자 자동 구분, 외부 연동(캘린더 · 메일), owner/member 외 권한 등급, 25MB 초과 분할 업로드(이번에는 4.4MB 초과), 푸시 알림
- 확정 결정과 헤비 이슈는 `docs/결정기록.md` 에 있다
