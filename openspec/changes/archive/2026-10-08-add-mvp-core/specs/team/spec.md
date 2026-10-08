# Spec Delta

## Purpose

사용자가 팀을 만들거나 초대코드로 합류하고, 팀 이름과 초대코드와 멤버를 관리하는 동작을 정한다. 한 사람은 한 팀에만 속하고, 팀 안의 권한은 owner 와 member 두 등급이다.

## ADDED Requirements

### Requirement: 팀 생성
<!-- 근거: F-02 / team.html · B-05 / login.html -->
`POST /api/teams` 는 팀 이름을 받아 팀을 만들고 만든 사람을 owner 로 등록하며 201 과 `id` · `name` · `invite_code` 를 돌려줘야 한다(SHALL). 초대코드는 팀마다 하나이고 `MN-XXXX` 형식(대문자 · 숫자 4자)이다. 이미 팀에 속한 사람이 부르면 400 `VALIDATION_ERROR` 다. 팀 생성은 활동 기록을 남기지 않는다.

#### Scenario: 팀 만들기
- **WHEN** 소속 팀이 없는 사용자가 이름 `기획팀` 으로 팀을 만든다
- **THEN** 201 과 `MN-` 로 시작하는 초대코드를 받고, 그 사용자가 owner 가 된다

#### Scenario: 이미 팀이 있는 사용자
- **WHEN** 소속 팀이 있는 사용자가 팀을 만들려 한다
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 내 팀 조회
<!-- 근거: F-01 · F-02 / team.html -->
`GET /api/teams` 는 로그인한 사람이 속한 팀을 돌려줘야 한다(SHALL). 한 사람은 한 팀에만 속하므로 결과는 0개 또는 1개다. 팀이 없으면 200 과 빈 배열이고, 화면은 「소속 팀 없음」 상태로 팀 만들기와 합류 입력을 보이며 회의록 화면으로 넘어가지 못하게 한다.

#### Scenario: 소속 팀 없음
- **WHEN** 팀이 없는 사용자가 팀 화면을 연다
- **THEN** 200 과 빈 배열을 받고 「아직 소속 팀이 없음」 화면이 보인다

### Requirement: 초대코드 합류
<!-- 근거: F-03 · F-06 / team.html · B-11 / login.html -->
`POST /api/teams/join` 은 초대코드를 받아 해당 팀에 member 로 합류시켜야 한다(SHALL). 없는 코드는 404 `INVITE_NOT_FOUND`, 정원(6명)이 찼으면 409 `TEAM_FULL`, 이미 팀에 속한 사람이 부르면 400 `VALIDATION_ERROR` 다. 합류가 실패해도 계정은 유지된다. 합류하면 `member_join` 활동을 남긴다.

#### Scenario: 정상 합류
- **WHEN** 팀이 없는 사용자가 유효한 코드로 합류한다
- **THEN** 200 을 받고 member 가 되며 `member_join` 활동이 남는다

#### Scenario: 없는 코드
- **WHEN** `MN-0000` 으로 합류를 요청한다
- **THEN** 404 `INVITE_NOT_FOUND` 를 받고 화면에 「없는 초대코드」 가 보인다

#### Scenario: 정원 초과
- **WHEN** 멤버가 6명인 팀에 합류를 요청한다
- **THEN** 409 `TEAM_FULL` 을 받고 합류되지 않는다

### Requirement: 초대코드 재발급
<!-- 근거: F-05 · F-08 / team.html -->
`PUT /api/teams/{id}/code` 는 owner 만 부를 수 있으며 새 코드를 만들어 돌려줘야 한다(SHALL). 앞의 코드는 더 쓸 수 없고 이미 합류한 멤버는 그대로다. member 가 부르면 403 `OWNER_ONLY` 다. 화면의 코드 복사 버튼은 코드를 클립보드에 넣고 「복사했습니다」 를 보인다.

#### Scenario: owner 재발급
- **WHEN** owner 가 재발급을 누른다
- **THEN** 200 과 새 코드를 받고, 앞의 코드로는 합류할 수 없으며, 기존 멤버십은 그대로다

#### Scenario: member 의 재발급 시도
- **WHEN** member 가 `PUT /api/teams/{id}/code` 를 부른다
- **THEN** 403 `OWNER_ONLY` 를 받는다

### Requirement: 팀 이름 변경
<!-- 근거: F-07 / team.html -->
`PUT /api/teams/{id}` 는 owner 만 팀 이름을 바꿀 수 있어야 한다(SHALL). member 가 부르면 403 `OWNER_ONLY` 다.

#### Scenario: owner 가 이름을 바꿈
- **WHEN** owner 가 `PUT /api/teams/{id}` 로 이름을 보낸다
- **THEN** 200 을 받고 이름이 바뀐다

#### Scenario: member 가 이름을 바꾸려 함
- **WHEN** member 가 같은 요청을 보낸다
- **THEN** 403 `OWNER_ONLY` 를 받는다

### Requirement: member 에게는 owner 전용 조작을 잠금
<!-- 근거: F-08 / team.html -->
owner 전용 조작은 팀 이름 변경 · 초대코드 재발급 · 할 일 삭제 셋뿐이어야 한다(SHALL). member 로 들어온 팀 화면은 읽기만 가능해서 이름 입력과 저장 · 재발급 · 복사 버튼이 비활성으로 보이고, 「owner 전용 조작 잠김」 상태가 된다. 이 밖의 조작은 팀원 누구나 할 수 있다.

#### Scenario: member 의 팀 화면
- **WHEN** member 가 팀 화면을 연다
- **THEN** 이름 입력과 저장 · 재발급 버튼이 비활성이다

### Requirement: 멤버 목록
<!-- 근거: F-01 / team.html -->
`GET /api/teams/{id}/members` 는 멤버마다 `id` · `name` · `email` · `role` · `todo_count` 를 돌려줘야 한다(SHALL). `todo_count` 는 그 사람에게 배정된 할 일의 전체 개수(완료 포함)다. 팀 화면은 「멤버 N / 6」 을 보인다.

#### Scenario: 멤버별 할 일 수
- **WHEN** 김대리에게 할 일 2건이 배정돼 있다
- **THEN** 멤버 목록의 김대리 항목에 `todo_count` 가 2 로 온다

### Requirement: 팀 안의 정보는 팀원만
<!-- 근거: 프로그램정의 7-4 / team.html -->
다른 팀의 `{id}` 로 팀 · 멤버 · 활동 · 회의록 · 할 일 API 를 부르면 404 로 응답하고 그 팀의 존재 여부를 알리지 않아야 한다(SHALL). 팀 안에서 권한이 모자라면 `FORBIDDEN`(403), owner 전용이면 `OWNER_ONLY`(403) 다.

#### Scenario: 남의 팀 멤버 조회
- **WHEN** 팀 A 의 사용자가 팀 B 의 `GET /api/teams/{B}/members` 를 부른다
- **THEN** 404 를 받는다
