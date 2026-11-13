# Spec Delta

## Purpose

이메일과 비밀번호로 가입하고 로그인해 24시간짜리 토큰을 받고, 그 토큰으로 내 정보를 조회 · 수정하며 로그아웃하는 인증 기능과 로그인 화면(login.html)의 동작을 정의한다.

## ADDED Requirements

### Requirement: 회원가입
<!-- 근거: B-05 · login.html / 정의서 7-1 · 7-4 -->
시스템은 `POST /api/auth/signup` 으로 이메일 · 비밀번호 · 이름을 받아 계정을 만들고 201 과 `{token, user}` 를 MUST 돌려준다. 비밀번호는 bcrypt 해시로만 저장한다(SHALL). signup 은 초대코드를 받지 않는다. 화면은 초대코드 칸이 채워져 있으면 가입 성공 뒤 `POST /api/teams/join` 을 따로 부른다.

#### Scenario: 정상 가입
- **WHEN** 처음 쓰는 이메일 `hong@example.com`, 8자 이상 비밀번호, 이름 `홍길동` 으로 가입을 요청하면
- **THEN** 201 과 `{token, user:{id, name, email}}` 를 받고, DB 의 password_hash 는 평문과 다르다

#### Scenario: 초대코드를 함께 적은 가입
- **WHEN** 가입 화면에서 초대코드 `MN-7K2D` 를 적고 「가입하기」를 누르면
- **THEN** 화면은 signup 201 뒤에 join 을 따로 호출하고, 성공하면 meetings.html 로 간다

### Requirement: 가입 입력 오류
<!-- 근거: B-08 · B-09 · B-10 · login.html -->
시스템은 이메일 형식이 틀리면 400 `EMAIL_INVALID`, 이미 있는 이메일이면 409 `EMAIL_DUPLICATED`, 비밀번호가 8자 미만이면 400 `PASSWORD_TOO_WEAK` 를 MUST 돌려준다. 화면은 이메일 형식과 8자 미만을 서버를 부르기 전에 먼저 거른다(SHALL). 입력 중에는 오류를 띄우지 않는다.

#### Scenario: 형식 오류는 화면이 거름
- **WHEN** 이메일 칸에 `hong@example` 를 적고 「가입하기」를 누르면
- **THEN** 서버를 부르지 않고 칸 아래에 「이메일 형식이 올바르지 않음」을 띄운다

#### Scenario: 중복 이메일
- **WHEN** 이미 가입된 `kim@example.com` 으로 가입을 요청하면
- **THEN** 409 `{code:"EMAIL_DUPLICATED", msg}` 를 받고 화면은 「이미 가입된 이메일」을 띄운다

#### Scenario: 약한 비밀번호
- **WHEN** 5자 비밀번호로 가입을 요청하면
- **THEN** 서버는 400 `PASSWORD_TOO_WEAK` 를 돌려주고, 화면은 서버 호출 전에 「비밀번호는 8자 이상」을 띄운다

### Requirement: 가입 뒤 초대코드 실패
<!-- 근거: B-11 · login.html -->
가입은 성공했지만 join 이 404 `INVITE_NOT_FOUND` 이면, 시스템은 계정을 그대로 두고 화면은 team.html 로 MUST 보낸다.

#### Scenario: 없는 초대코드로 가입
- **WHEN** 초대코드 `MN-0000` 을 적고 가입하면
- **THEN** signup 201, join 404 를 받고 띠 알림 「가입 완료 - 팀 화면으로 이동」을 띄운 뒤 team.html 로 간다

### Requirement: 로그인
<!-- 근거: B-01 · B-04 · login.html -->
시스템은 `POST /api/auth/login` 으로 이메일 · 비밀번호를 받아 맞으면 200 `{token, user}` 를 MUST 돌려준다. 화면은 토큰을 localStorage 에 저장하고 `GET /api/teams` 로 소속 팀을 확인해, 있으면 meetings.html, 없으면 team.html 로 보낸다(SHALL).

#### Scenario: 팀이 있는 사람의 로그인
- **WHEN** 팀에 속한 사용자가 올바른 이메일과 비밀번호로 로그인하면
- **THEN** 200 `{token, user}` 를 받고 버튼이 「로그인 중...」으로 잠긴 뒤 meetings.html 로 간다

#### Scenario: 팀이 없는 사람의 로그인
- **WHEN** 소속 팀이 없는 사용자가 로그인하면
- **THEN** `GET /api/teams` 가 빈 배열이고 화면은 team.html 로 간다

### Requirement: 로그인 실패
<!-- 근거: B-02 · login.html -->
시스템은 이메일이 없거나 비밀번호가 틀리면 둘을 구분하지 않고 401 `INVALID_CREDENTIALS` 를 MUST 돌려준다.

#### Scenario: 틀린 비밀번호
- **WHEN** 있는 이메일에 틀린 비밀번호로 로그인하면
- **THEN** 401 `INVALID_CREDENTIALS` 를 받고 화면은 「이메일 또는 비밀번호가 올바르지 않음」을 띄운다

#### Scenario: 없는 이메일
- **WHEN** 가입하지 않은 이메일로 로그인하면
- **THEN** 틀린 비밀번호와 같은 401 `INVALID_CREDENTIALS` 와 같은 메시지를 받는다

### Requirement: 토큰 인증과 만료
<!-- 근거: B-03 · login.html / 정의서 7-2 · 8-1 -->
인증이 필요한 모든 API 는 `Authorization: Bearer <token>` 을 MUST 요구한다. 토큰은 발급 24시간 뒤 만료되며 갱신하지 않는다. 토큰 없음 · 위조 · 만료는 모두 401 `TOKEN_EXPIRED` 이다. 화면은 401 `TOKEN_EXPIRED` 를 받으면 토큰을 지우고 login.html 로 보낸다(SHALL).

#### Scenario: 만료된 토큰
- **WHEN** 발급 24시간이 지난 토큰으로 회의록 목록을 요청하면
- **THEN** 401 `TOKEN_EXPIRED` 를 받고, 화면은 토큰을 지운 뒤 login.html 에서 「다시 로그인 필요 - 24시간 지남」을 띄운다

#### Scenario: 토큰 없이 호출
- **WHEN** Authorization 헤더 없이 `GET /api/auth/me` 를 부르면
- **THEN** 401 `TOKEN_EXPIRED` 를 받는다

### Requirement: 처리 중 잠금
<!-- 근거: B-07 · login.html -->
화면은 로그인 · 가입 요청을 보내는 동안 버튼을 MUST 잠가 두 번 눌리지 않게 한다.

#### Scenario: 가입 버튼 연타
- **WHEN** 「가입하기」를 누르고 응답 전에 다시 누르면
- **THEN** 버튼은 「가입 중...」으로 비활성이고 요청은 한 번만 나간다

### Requirement: 내 정보 조회
<!-- 근거: J-01 · profile.html -->
시스템은 `GET /api/auth/me` 로 `{id, name, email, role}` 을 MUST 돌려준다. role 은 소속 팀에서의 owner / member 이고, 팀이 없으면 null 이다. 화면은 이메일을 고칠 수 없게 둔다.

#### Scenario: owner 의 내 정보
- **WHEN** 팀을 만든 사람이 내 정보를 조회하면
- **THEN** 200 과 `role:"owner"` 가 담긴 내 정보를 받는다

### Requirement: 내 정보 수정
<!-- 근거: J-02 · J-04 · J-06 · profile.html / 정의서 7-4 -->
시스템은 `PUT /api/auth/me` 로 이름과 새 비밀번호를 받아 고친다(SHALL). 비밀번호를 보내지 않으면 비밀번호는 그대로 둔다. 새 비밀번호가 8자 미만이면 400 `PASSWORD_TOO_WEAK` 를 MUST 돌려준다. 현재 비밀번호는 받지 않는다. 계정 변경은 활동 기록에 남기지 않는다.

#### Scenario: 이름만 변경
- **WHEN** 이름만 `홍길순` 으로 바꿔 저장하면
- **THEN** 200 을 받고 기존 비밀번호로 계속 로그인된다

#### Scenario: 약한 새 비밀번호
- **WHEN** 새 비밀번호를 5자로 보내면
- **THEN** 400 `PASSWORD_TOO_WEAK` 를 받고 화면은 「비밀번호는 8자 이상」을 띄운다

#### Scenario: 저장 완료
- **WHEN** 이름과 새 비밀번호를 저장하면
- **THEN** 200 뒤 띠 알림 「저장함 - 비밀번호 칸 비움」을 띄우고, 활동 기록은 늘지 않는다

### Requirement: 비밀번호 확인 불일치
<!-- 근거: J-03 · J-05 · profile.html -->
화면은 「새 비밀번호」와 「한 번 더」가 다르면 서버로 보내지 않고 MUST 「두 비밀번호가 다름 - 서버로 보내지 않음」을 띄운다. 저장 중에는 버튼을 「저장 중...」으로 잠근다.

#### Scenario: 확인 칸이 다름
- **WHEN** 새 비밀번호와 확인 칸을 다르게 적고 저장하면
- **THEN** 요청은 나가지 않고 오류 문구가 뜬다

### Requirement: 로그아웃
<!-- 근거: 정의서 7-2 · profile.html -->
시스템은 `POST /api/auth/logout` 에 서버 블랙리스트 없이 200 을 MUST 돌려준다. 화면은 토큰을 지우고 login.html 로 간다.

#### Scenario: 로그아웃
- **WHEN** 내 정보 화면에서 「로그아웃」을 누르면
- **THEN** 200 을 받고 localStorage 의 토큰이 지워진 뒤 login.html 로 간다

### Requirement: 오류 응답 형식
<!-- 근거: 정의서 7-2 -->
모든 API 오류는 본문 `{code, msg}` 로 MUST 돌려준다. code 는 EMAIL_INVALID · PASSWORD_TOO_WEAK · TOKEN_EXPIRED · INVITE_NOT_FOUND · MEETING_NOT_FOUND · EMAIL_DUPLICATED · TEAM_FULL · UNSUPPORTED_MEDIA_TYPE · INVALID_CREDENTIALS · FORBIDDEN · OWNER_ONLY · VALIDATION_ERROR · NOT_FOUND 13종뿐이다. 입력 형식 오류 · 이미 다른 팀 소속은 400 `VALIDATION_ERROR` 다.

#### Scenario: 형식이 틀린 요청 본문
- **WHEN** 필수 필드가 빠진 JSON 으로 API 를 부르면
- **THEN** 400 과 `{code:"VALIDATION_ERROR", msg}` 를 받는다

#### Scenario: 없는 할 일
- **WHEN** 없는 id 로 `PUT /api/todos/{id}` 를 부르면
- **THEN** 404 `{code:"NOT_FOUND", msg}` 를 받는다

### Requirement: Swagger UI 로 API 시험
<!-- 근거: add-mvp-core (지시) -->
시스템은 `/docs` 에 Swagger UI 를 MUST 열어 27개 API 를 화면에서 호출해 볼 수 있게 한다. Authorize 버튼에 로그인 응답의 토큰을 넣으면 인증이 필요한 API 도 그 화면에서 호출된다.

#### Scenario: 토큰을 넣고 호출
- **WHEN** `/docs` 에서 login 을 실행해 받은 토큰을 Authorize 에 넣고 `GET /api/auth/me` 를 실행하면
- **THEN** 200 과 내 정보가 화면에 보인다

#### Scenario: 화면 경로와 겹치지 않음
- **WHEN** `/docs` 와 `/login.html` 을 차례로 열면
- **THEN** 앞은 Swagger UI, 뒤는 로그인 화면이 열린다
