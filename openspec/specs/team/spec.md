# team Specification

## Purpose
3~6명 규모의 팀을 만들고 초대코드 하나로 멤버를 합류시키며, owner 와 member 두 역할로 팀 설정을 관리하게 하는 기능이다. 모든 팀 자원의 접근 경계를 정한다.

## Requirements

### Requirement: 팀 생성과 초대코드
<!-- F-01, F-02 team.html -->
시스템은 `POST /api/teams` 로 팀 이름을 받아 팀을 만들고, 만든 사람을 owner 로 등록하며, `MN-7K2D` 형식(MN- 뒤 영숫자 4자리)의 고유 초대코드를 발급해 201 로 돌려줘야 한다(SHALL).

#### Scenario: 팀 만들기
- **WHEN** 팀이 없는 사용자가 팀 이름 "기획팀" 으로 팀을 만든다
- **THEN** 201 과 `MN-` 형식 초대코드가 돌아오고 그 사용자가 owner 이다

### Requirement: 내 팀 조회
<!-- F-01, F-02 team.html, B-04 login.html -->
시스템은 `GET /api/teams` 로 로그인한 사용자의 소속 팀 목록을 돌려줘야 하며(SHALL), 소속 팀이 없으면 200 과 빈 배열을 돌려줘야 한다.

#### Scenario: 소속 팀 없음
- **WHEN** 어느 팀에도 속하지 않은 사용자가 호출한다
- **THEN** 200 과 빈 배열이 돌아오고 team.html 은 소속 팀 없음 상태를 보인다

### Requirement: 초대코드로 합류
<!-- F-03, F-06, B-11 team.html -->
시스템은 `POST /api/teams/join` 으로 초대코드를 받아 호출자를 member 로 등록해야 한다(SHALL). 코드가 없으면 404 `INVITE_NOT_FOUND`, 팀이 이미 6명이면 409 `TEAM_FULL` 을 돌려주고, 합류 성공 시 활동 기록 `member_join` 을 남겨야 한다.

#### Scenario: 합류 성공
- **WHEN** 팀이 없는 사용자가 유효한 초대코드로 합류한다
- **THEN** member 로 등록되고 팀 활동 기록에 `member_join` 이 남는다

#### Scenario: 없는 초대코드
- **WHEN** 존재하지 않는 코드로 합류를 요청한다
- **THEN** 404 `INVITE_NOT_FOUND` 가 돌아온다

#### Scenario: 정원 초과
- **WHEN** 이미 6명인 팀의 코드로 합류를 요청한다
- **THEN** 409 `TEAM_FULL` 이 돌아오고 멤버는 늘지 않는다

### Requirement: 멤버 목록
<!-- F-01 team.html -->
시스템은 `GET /api/teams/{id}/members` 로 각 멤버의 `id · name · email · role · todo_count` 를 돌려줘야 한다(SHALL). `todo_count` 는 그 멤버에게 배정된 할 일 수이다.

#### Scenario: 멤버 목록 조회
- **WHEN** 팀 멤버가 자기 팀의 멤버 목록을 조회한다
- **THEN** 모든 멤버가 role 과 배정된 할 일 수와 함께 돌아온다

### Requirement: 팀 이름 변경 (owner 전용)
<!-- F-07, F-08 team.html -->
시스템은 `PUT /api/teams/{id}` 로 팀 이름 변경을 owner 에게만 허용해야 한다(SHALL). member 가 호출하면 403 `OWNER_ONLY` 를 돌려줘야 한다.

#### Scenario: owner 가 이름 변경
- **WHEN** owner 가 새 이름으로 호출한다
- **THEN** 200 이 돌아오고 팀 이름이 바뀐다

#### Scenario: member 가 이름 변경
- **WHEN** member 가 호출한다
- **THEN** 403 `OWNER_ONLY` 가 돌아오고 이름은 그대로이다

### Requirement: 초대코드 재발급 (owner 전용)
<!-- F-05, F-08 team.html -->
시스템은 `PUT /api/teams/{id}/code` 로 초대코드 재발급을 owner 에게만 허용해야 하며(SHALL), 재발급 즉시 앞의 코드는 합류에 쓸 수 없어야 한다. member 가 호출하면 403 `OWNER_ONLY` 이다.

#### Scenario: 재발급
- **WHEN** owner 가 코드를 재발급한다
- **THEN** 새 코드가 돌아오고 앞의 코드로 합류하면 404 `INVITE_NOT_FOUND` 가 돌아온다

### Requirement: 팀 자원 접근 경계
<!-- 정의서 3절 범위 외 권한 등급 -->
시스템은 팀 단위 자원(멤버 · 회의록 · 할 일 · 활동 기록)을 그 팀의 멤버에게만 보여줘야 한다(SHALL). 소속이 아닌 사용자의 요청은 403 `FORBIDDEN` 으로 거절해야 한다.

#### Scenario: 다른 팀 접근
- **WHEN** 팀 A 의 멤버가 팀 B 의 `GET /api/teams/{B}/members` 를 호출한다
- **THEN** 403 `FORBIDDEN` 이 돌아온다

### Requirement: 팀 설정 화면 보조 동작
<!-- F-04 team.html -->
팀 설정 화면은 초대코드 복사 버튼을 눌렀을 때 코드를 클립보드로 복사하고 복사됨을 알려줘야 한다(SHALL).

#### Scenario: 코드 복사
- **WHEN** 사용자가 복사 버튼을 누른다
- **THEN** 초대코드가 클립보드에 들어가고 알림이 보인다
