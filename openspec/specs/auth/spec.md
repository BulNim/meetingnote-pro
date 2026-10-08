# auth Specification

## Purpose

사용자가 이메일과 비밀번호로 가입하고 로그인해 JWT 로 자신을 증명하며, 이름과 비밀번호를 바꾸고, 세션이 만료되면 다시 로그인하게 하는 계정 동작을 정한다. 모든 API 가 공유하는 오류 형식과 API 시험 화면도 여기서 정한다.

## Requirements

### Requirement: 회원가입
<!-- 근거: B-05 · B-06 · B-07 · B-08 · B-09 · B-10 / login.html -->
시스템은 `POST /api/auth/signup` 으로 이메일 · 비밀번호 · 이름을 받아 계정을 만들고 201 과 JWT 를 돌려줘야 한다(SHALL). 비밀번호는 bcrypt 로 해시해 저장하고 원문은 저장하지 않는다. 이메일 형식이 틀리면 400 `EMAIL_INVALID`, 이미 있는 이메일이면 409 `EMAIL_DUPLICATED`, 비밀번호가 8자 미만이면 400 `PASSWORD_TOO_WEAK` 를 돌려준다.

#### Scenario: 정상 가입
- **WHEN** `user@example.com` · `mypassword` · `홍길동` 으로 가입을 요청한다
- **THEN** 201 과 JWT 를 받고, DB 에 해시된 비밀번호가 저장된다

#### Scenario: 이메일 형식 오류
- **WHEN** 이메일에 `user@@example` 을 보낸다
- **THEN** 400 `EMAIL_INVALID` 를 받고 계정은 만들어지지 않는다

#### Scenario: 이메일 중복
- **WHEN** 이미 가입된 이메일로 가입을 요청한다
- **THEN** 409 `EMAIL_DUPLICATED` 를 받는다

#### Scenario: 약한 비밀번호
- **WHEN** 비밀번호에 `1234` 를 보낸다
- **THEN** 400 `PASSWORD_TOO_WEAK` 를 받는다

### Requirement: 회원가입 화면의 입력 검증과 중복 제출 방지
<!-- 근거: B-05 · B-06 · B-07 · B-08 · B-10 / login.html -->
회원가입 화면은 이메일 형식과 비밀번호 8자 이상을 제출 전에 화면에서 먼저 검사해야 한다(SHALL). 입력 중에는 오류를 띄우지 않고, 제출 중에는 버튼을 잠가 두 번 눌리지 않게 한다. 초대코드 칸은 회원가입에서만 보이며 비워 두면 가입 후 팀을 새로 만든다.

#### Scenario: 입력 중에는 오류를 띄우지 않음
- **WHEN** 사용자가 이메일과 비밀번호를 입력하는 중이다
- **THEN** 제출 전에는 어떤 오류 문구도 보이지 않는다

#### Scenario: 처리 중 버튼 잠금
- **WHEN** 가입 요청을 보내고 응답을 기다린다
- **THEN** 버튼이 비활성이고 문구가 「처리 중...」 으로 바뀐다

### Requirement: 가입 후 초대코드 합류 실패 시 계정 유지
<!-- 근거: B-11 / login.html · F-03 / team.html -->
회원가입 화면에서 초대코드를 넣으면 가입이 끝난 뒤 `POST /api/teams/join` 이 이어서 호출돼야 한다(SHALL). 합류가 404 `INVITE_NOT_FOUND` 로 실패해도 가입한 계정은 그대로 유지하고, 사용자를 팀 화면(소속 팀 없음 상태)으로 보낸다.

#### Scenario: 없는 초대코드
- **WHEN** 유효한 정보와 존재하지 않는 초대코드 `MN-0000` 으로 가입한다
- **THEN** 계정은 만들어지고, 초대코드 칸에 「없는 초대코드」 가 보이며, 팀 화면으로 이동한다

### Requirement: 로그인
<!-- 근거: B-01 · B-02 · B-04 / login.html -->
시스템은 `POST /api/auth/login` 으로 이메일과 비밀번호를 받아 맞으면 200 과 JWT 를 돌려줘야 한다(SHALL). 이메일이 없거나 비밀번호가 틀리면 어느 쪽인지 알리지 않고 같은 401 `INVALID_CREDENTIALS` 를 돌려준다. 성공하면 화면은 토큰을 `localStorage` 에 저장하고 소속 팀을 검사해 팀이 없으면 팀 화면, 있으면 회의록 화면으로 보낸다.

#### Scenario: 로그인 성공
- **WHEN** 올바른 이메일과 비밀번호로 로그인한다
- **THEN** 200 과 JWT 를 받고 토큰이 저장된다

#### Scenario: 이메일 존재 여부를 숨김
- **WHEN** 없는 이메일로 로그인하거나 비밀번호를 틀리게 보낸다
- **THEN** 두 경우 모두 401 `INVALID_CREDENTIALS` 와 같은 메시지를 받는다

#### Scenario: 소속 팀이 없는 사용자
- **WHEN** 팀이 없는 사용자가 로그인에 성공한다
- **THEN** 회의록 화면이 아니라 팀 화면(소속 팀 없음)으로 이동한다

### Requirement: JWT 와 세션 만료
<!-- 근거: B-03 / login.html -->
JWT 는 발급 24시간 뒤 만료되며 갱신 토큰은 없어야 한다(SHALL). 인증이 필요한 API 를 만료된 토큰으로 부르면 401 `TOKEN_EXPIRED` 를, 토큰이 없거나 형식이 틀리면 401 `UNAUTHORIZED` 를 돌려준다. 화면은 401 `TOKEN_EXPIRED` 를 받으면 저장된 토큰을 지우고 로그인 화면으로 가서 「세션 만료」 안내를 보인다.

#### Scenario: 만료된 토큰
- **WHEN** 24시간이 지난 토큰으로 `GET /api/auth/me` 를 부른다
- **THEN** 401 `TOKEN_EXPIRED` 를 받고, 화면이 토큰을 지우고 로그인 화면에 세션 만료 안내를 보인다

#### Scenario: 토큰 없음
- **WHEN** Authorization 헤더 없이 인증이 필요한 API 를 부른다
- **THEN** 401 `UNAUTHORIZED` 를 받는다

### Requirement: 로그아웃
<!-- 근거: A-01 · J / profile.html -->
`POST /api/auth/logout` 은 200 을 돌려줘야 한다(SHALL). 서버는 토큰 블랙리스트를 두지 않으며, 화면이 저장된 토큰을 지우고 로그인 화면으로 이동한다.

#### Scenario: 로그아웃
- **WHEN** 내 정보 화면에서 로그아웃을 누른다
- **THEN** 200 을 받고 토큰이 지워지며 로그인 화면으로 이동한다

### Requirement: 내 정보 조회
<!-- 근거: J-01 / profile.html -->
`GET /api/auth/me` 는 로그인한 사람의 `id` · `name` · `email` 과, 소속 팀에서의 `role`(`owner` 또는 `member`, 팀이 없으면 null)을 돌려줘야 한다(SHALL). 이메일은 고칠 수 없다.

#### Scenario: 소속 팀의 owner
- **WHEN** 팀을 만든 사용자가 내 정보를 조회한다
- **THEN** `role` 이 `owner` 로 오고 화면에 owner 배지가 보인다

### Requirement: 내 정보 수정
<!-- 근거: J-02 · J-03 · J-04 · J-05 · J-06 / profile.html (현재 비밀번호 칸은 구현에서 추가, 프로그램정의 7-4) -->
`PUT /api/auth/me` 는 이름만 보내면 비밀번호를 그대로 두고, 새 비밀번호를 보내면 현재 비밀번호(`current_password`)가 맞고 새 비밀번호가 8자 이상일 때만 바꿔야 한다(SHALL). 현재 비밀번호가 틀리면 401 `INVALID_CREDENTIALS`, 8자 미만이면 400 `PASSWORD_TOO_WEAK` 다. 화면은 현재 비밀번호 칸을 두고, 새 비밀번호와 확인 칸이 다르면 서버로 보내지 않고 「두 비밀번호가 다름」 을 보인다. 저장해도 기존 토큰은 계속 유효하고 활동 기록에는 남기지 않는다.

#### Scenario: 이름만 변경
- **WHEN** 이름만 담아 `PUT /api/auth/me` 를 부른다
- **THEN** 200 을 받고 이름이 바뀌며 비밀번호는 그대로다

#### Scenario: 비밀번호 확인이 다름
- **WHEN** 새 비밀번호와 확인 칸이 다르다
- **THEN** 화면이 요청을 보내지 않고 「두 비밀번호가 다름」 을 보인다

#### Scenario: 약한 새 비밀번호
- **WHEN** 현재 비밀번호가 맞고 새 비밀번호가 `1234` 다
- **THEN** 400 `PASSWORD_TOO_WEAK` 를 받는다

#### Scenario: 현재 비밀번호가 틀림
- **WHEN** 새 비밀번호와 함께 틀린 현재 비밀번호를 보낸다
- **THEN** 401 `INVALID_CREDENTIALS` 를 받고 비밀번호는 바뀌지 않으며 화면에 「현재 비밀번호가 올바르지 않음」 이 보인다

#### Scenario: 이름만 바꿀 때는 현재 비밀번호가 필요 없음
- **WHEN** 이름만 보내고 현재 비밀번호는 보내지 않는다
- **THEN** 200 을 받고 이름이 바뀐다

#### Scenario: 저장 중 중복 제출 방지
- **WHEN** 저장을 눌러 응답을 기다린다
- **THEN** 버튼이 비활성이고 문구가 「저장 중...」 이다

### Requirement: 공통 오류 본문
<!-- 근거: 프로그램정의 7-2 · B-02 ~ B-11 / login.html -->
모든 오류 응답은 `{code, msg}` 본문을 가져야 한다(SHALL). 코드는 `EMAIL_INVALID` · `PASSWORD_TOO_WEAK` · `TOKEN_EXPIRED` · `UNAUTHORIZED` · `INVITE_NOT_FOUND` · `MEETING_NOT_FOUND` · `EMAIL_DUPLICATED` · `TEAM_FULL` · `PAYLOAD_TOO_LARGE` · `UNSUPPORTED_MEDIA_TYPE` · `INVALID_CREDENTIALS` · `FORBIDDEN` · `OWNER_ONLY` · `VALIDATION_ERROR` · `NOT_FOUND` · `UPSTREAM_ERROR` 로 한정하고 이 밖의 값은 만들지 않는다.

#### Scenario: 본문 형식
- **WHEN** 어떤 API 든 오류를 돌려준다
- **THEN** 본문이 `code` 와 `msg` 두 키를 가진 JSON 이다

### Requirement: 인증이 필요한 경로
<!-- 근거: 프로그램정의 7 · I-01 / meetings.html -->
`POST /api/auth/signup` 과 `POST /api/auth/login` 을 뺀 모든 `/api/` 경로는 유효한 토큰이 있어야 한다(SHALL). 모든 경로는 `/api/` 접두사를 가진다.

#### Scenario: 로그인 없이 회의록 목록 호출
- **WHEN** 토큰 없이 `GET /api/teams/{id}/meetings` 를 부른다
- **THEN** 401 `UNAUTHORIZED` 를 받는다

### Requirement: API 시험 화면
<!-- 근거: 사용자 요청(결정기록 D-006) / 근거 화면 없음 -->
시스템은 로컬과 배포 모두에서 `/docs` 에 Swagger UI 를, `/openapi.json` 에 스키마를 열어야 한다(SHALL). 화면의 `Authorize` 버튼에 로그인으로 받은 JWT 를 넣으면 나머지 API 를 화면에서 바로 호출할 수 있다. 이 두 경로는 `/api/` 접두사 규칙과 고유 경로 26개 계산에서 제외하고, 정적 파일 연결이 가리지 않아야 한다.

#### Scenario: 시험 화면에서 호출
- **WHEN** `/docs` 를 열어 로그인으로 받은 토큰을 `Authorize` 에 넣고 `GET /api/auth/me` 를 실행한다
- **THEN** 200 과 내 정보를 받는다

#### Scenario: 정적 파일이 문서 경로를 가리지 않음
- **WHEN** 정적 파일이 `/` 에 연결된 상태에서 `/docs` 를 연다
- **THEN** 정적 파일이 아니라 Swagger UI 가 열린다
