# Spec Delta

## Purpose

팀 회의록을 쓰는 사람이 이메일과 비밀번호로 가입하고 로그인하며, 발급받은 JWT 로 이후 모든 API 와 화면에서 본인임을 증명하게 하는 인증 기능이다. 비밀번호는 해시로만 저장한다.

## ADDED Requirements

### Requirement: 회원가입
<!-- B-05, B-08, B-09, B-10 login.html -->
시스템은 `POST /api/auth/signup` 으로 이메일 · 비밀번호 · 이름을 받아 계정을 만들고 201 과 JWT 를 돌려줘야 한다(SHALL). 이메일 형식이 틀리면 400 `EMAIL_INVALID`, 이미 가입된 이메일이면 409 `EMAIL_DUPLICATED`, 비밀번호가 8자 미만이면 400 `PASSWORD_TOO_WEAK` 를 돌려줘야 한다. 계정을 만들지 못한 경우 아무것도 저장하지 않아야 한다.

#### Scenario: 가입 성공
- **WHEN** 새 이메일 `kim@example.com`, 비밀번호 8자 이상, 이름으로 가입을 요청한다
- **THEN** 201 과 JWT 가 돌아오고 같은 이메일로 로그인할 수 있다

#### Scenario: 이메일 형식 오류
- **WHEN** 이메일에 `@` 가 없는 값으로 가입을 요청한다
- **THEN** 400 과 `{code: "EMAIL_INVALID", msg}` 가 돌아온다

#### Scenario: 이메일 중복
- **WHEN** 이미 가입된 이메일로 가입을 요청한다
- **THEN** 409 와 `{code: "EMAIL_DUPLICATED", msg}` 가 돌아오고 기존 계정은 바뀌지 않는다

#### Scenario: 약한 비밀번호
- **WHEN** 7자 비밀번호로 가입을 요청한다
- **THEN** 400 과 `{code: "PASSWORD_TOO_WEAK", msg}` 가 돌아온다

### Requirement: 비밀번호 해시 저장
<!-- 정의서 8-1 ACME C, 9절 보안 -->
시스템은 비밀번호를 bcrypt 해시로만 저장해야 하며(MUST), 어떤 응답에도 비밀번호나 해시를 담아서는 안 된다.

#### Scenario: 저장값 확인
- **WHEN** 가입 직후 users 테이블의 `password_hash` 를 읽는다
- **THEN** 원문 비밀번호와 다른 bcrypt 해시이고, 어떤 API 응답에도 그 값이 나오지 않는다

### Requirement: 로그인과 JWT 발급
<!-- B-01, B-02, B-04 login.html -->
시스템은 `POST /api/auth/login` 으로 이메일과 비밀번호를 검증해 200 과 JWT(유효 24시간, 갱신 없음)를 돌려줘야 한다(SHALL). 이메일이 없거나 비밀번호가 틀린 경우는 구분하지 않고 같은 401 `INVALID_CREDENTIALS` 를 돌려줘야 한다.

#### Scenario: 로그인 성공
- **WHEN** 가입한 이메일과 맞는 비밀번호로 로그인한다
- **THEN** 200 과 만료 24시간인 JWT 가 돌아온다

#### Scenario: 로그인 실패
- **WHEN** 없는 이메일이거나 틀린 비밀번호로 로그인한다
- **THEN** 두 경우 모두 401 `INVALID_CREDENTIALS` 와 같은 메시지가 돌아온다

### Requirement: 토큰 만료와 세션 만료 처리
<!-- B-03 login.html -->
시스템은 만료되었거나 유효하지 않은 JWT 로 인증이 필요한 API 를 호출하면 401 `TOKEN_EXPIRED` 를 돌려줘야 한다(SHALL). 화면은 이를 받으면 저장된 토큰을 지우고 로그인 화면으로 보내며 "세션이 만료되었습니다" 알림을 보여줘야 한다.

#### Scenario: 만료된 토큰
- **WHEN** 발급 후 24시간이 지난 JWT 로 `GET /api/auth/me` 를 호출한다
- **THEN** 401 `TOKEN_EXPIRED` 가 돌아온다

#### Scenario: 화면의 세션 만료 처리
- **WHEN** 어느 화면이든 API 가 401 `TOKEN_EXPIRED` 로 응답한다
- **THEN** `localStorage` 의 토큰이 지워지고 login.html 이 열리며 세션 만료 알림이 보인다

### Requirement: 로그인 직후 소속 팀 분기
<!-- B-04 login.html -->
화면은 로그인 성공 직후 `GET /api/teams` 로 소속 팀을 확인해 팀 id 를 `localStorage` 에 저장하고, 소속 팀이 있으면 meetings.html 로, 없으면 team.html 로 보내야 한다(SHALL).

#### Scenario: 소속 팀이 있는 로그인
- **WHEN** 팀에 속한 사용자가 로그인한다
- **THEN** 팀 id 가 `localStorage` 에 저장되고 meetings.html 로 이동한다

#### Scenario: 소속 팀이 없는 로그인
- **WHEN** 팀이 없는 사용자가 로그인한다
- **THEN** team.html 로 이동해 팀 만들기 또는 초대코드 입력을 안내받는다

### Requirement: 가입 후 초대코드 합류 실패 처리
<!-- B-05, B-11 login.html -->
회원가입 화면은 초대코드 칸을 가입 모드에서만 보여줘야 한다(SHALL). 초대코드를 적으면 가입 직후 `POST /api/teams/join` 을 호출하고, 404 `INVITE_NOT_FOUND` 이면 가입은 유지한 채 초대코드 칸에 오류를 보이고 team.html 로 보내야 한다.

#### Scenario: 틀린 초대코드로 가입
- **WHEN** 가입과 함께 존재하지 않는 초대코드를 적어 제출한다
- **THEN** 계정은 만들어져 있고 합류는 404 `INVITE_NOT_FOUND` 로 실패하며 team.html 로 이동한다

### Requirement: 내 정보 조회와 수정
<!-- J-01 ~ J-06 profile.html -->
시스템은 `GET /api/auth/me` 로 `id · name · email · role` 을 돌려주고, `PUT /api/auth/me` 로 이름과 비밀번호를 바꾸게 해야 한다(SHALL). 새 비밀번호가 8자 미만이면 400 `PASSWORD_TOO_WEAK` 를 돌려줘야 하고, 새 비밀번호와 확인값이 다른 경우는 화면에서 먼저 막아야 한다.

#### Scenario: 이름 변경
- **WHEN** 로그인한 사용자가 이름만 바꿔 `PUT /api/auth/me` 를 호출한다
- **THEN** 200 이 돌아오고 `GET /api/auth/me` 에 새 이름이 보인다

#### Scenario: 약한 새 비밀번호
- **WHEN** 7자 새 비밀번호로 `PUT /api/auth/me` 를 호출한다
- **THEN** 400 `PASSWORD_TOO_WEAK` 가 돌아오고 기존 비밀번호가 유지된다

#### Scenario: 비밀번호 불일치
- **WHEN** 새 비밀번호와 확인값이 다르게 입력된 채 저장을 누른다
- **THEN** 화면이 요청을 보내지 않고 불일치 오류를 보여준다

### Requirement: 로그아웃
<!-- 정의서 7-2 로그아웃 -->
시스템은 `POST /api/auth/logout` 에 200 을 돌려줘야 하며(SHALL), 서버에 블랙리스트를 두지 않는다. 화면은 응답을 받으면 `localStorage` 의 토큰을 지워야 한다.

#### Scenario: 로그아웃
- **WHEN** 로그인한 사용자가 로그아웃한다
- **THEN** 200 이 돌아오고 화면의 토큰이 지워져 로그인 화면으로 이동한다

### Requirement: 인증 응답 속도
<!-- 정의서 8-1 ACME M -->
시스템은 회원가입과 로그인 요청을 bcrypt 비용을 포함해 250ms 이내에 처리해야 하고(SHALL), 그 밖의 인증 API 는 100ms 이내에 처리해야 한다.

#### Scenario: 응답 시간 측정
- **WHEN** 로컬 환경에서 로그인을 반복 호출해 평균을 낸다
- **THEN** 평균이 250ms 이내이다
