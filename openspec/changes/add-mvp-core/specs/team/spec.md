# Spec Delta

## Purpose

사용자가 팀을 만들거나 초대코드로 합류해 한 팀에 속하게 하고, 멤버 목록 · 초대코드 · 팀 이름과 owner 전용 권한을 관리하는 팀 기능과 팀 설정 화면(team.html)의 동작을 정의한다.

## ADDED Requirements

### Requirement: 팀 생성
<!-- 근거: F-02 · team.html / 정의서 7-4 -->
시스템은 `POST /api/teams` 로 팀 이름을 받아 팀을 만들고, 만든 사람을 owner 로 등록하며, 초대코드 하나를 발급한다(SHALL). 이미 팀에 속한 사람이 만들려 하면 400 `VALIDATION_ERROR` 를 MUST 돌려준다. 팀 생성은 활동 기록에 남기지 않는다.

#### Scenario: 팀 만들기
- **WHEN** 소속 팀이 없는 사용자가 이름 `기획팀` 으로 팀을 만들면
- **THEN** 201 과 팀 정보를 받고, 그 사용자의 role 은 owner, 초대코드는 `MN-` 뒤 영숫자 4자 형식이다

#### Scenario: 이미 소속된 사람
- **WHEN** 팀에 속한 사용자가 팀 생성을 요청하면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 내 팀 목록
<!-- 근거: B-04 · F-01 · team.html -->
시스템은 `GET /api/teams` 로 내가 속한 팀 목록을 MUST 돌려준다. 한 사람은 한 팀에만 속하므로 원소는 0개 또는 1개다.

#### Scenario: 소속 팀 없음
- **WHEN** 팀이 없는 사용자가 팀 목록을 조회하면
- **THEN** 200 과 빈 배열을 받는다

### Requirement: 소속 팀 없는 화면
<!-- 근거: F-02 · team.html -->
화면은 소속 팀이 없으면 상단 메뉴의 회의록 · 할 일을 흐리게 하고 들어가지 못하게 MUST 막는다. 팀 설정 화면은 「팀 만들기」와 「초대코드로 합류」 두 칸을 보여 준다.

#### Scenario: 팀 없이 회의록 화면 접근
- **WHEN** 팀이 없는 사용자가 meetings.html 을 열면
- **THEN** team.html 로 보내지고 「소속 팀이 없어 회의록 · 할 일 화면에 들어갈 수 없음. 팀을 만들거나 초대코드로 합류」 안내가 보인다

### Requirement: 초대코드로 합류
<!-- 근거: F-03 · team.html / 정의서 7-4 -->
시스템은 `POST /api/teams/join` 으로 초대코드를 받아 그 팀의 member 로 등록하고 활동 `member_join` 을 남긴다(SHALL). 없는 코드는 404 `INVITE_NOT_FOUND`, 이미 소속된 사람은 400 `VALIDATION_ERROR` 를 MUST 돌려준다. 합류에 실패해도 계정은 그대로다.

#### Scenario: 정상 합류
- **WHEN** 팀이 없는 사용자가 `MN-7K2D` 로 합류하면
- **THEN** 200 을 받고 role 은 member, 팀 활동에 member_join 이 생긴다

#### Scenario: 없는 초대코드
- **WHEN** `MN-0000` 으로 합류하면
- **THEN** 404 `INVITE_NOT_FOUND` 를 받고 입력칸 아래에 「없는 초대코드 - 계정은 그대로 유지」가 뜬다

### Requirement: 팀 정원
<!-- 근거: F-06 · team.html / 정의서 8-1 -->
팀당 멤버는 6명을 넘지 못한다. 6명인 팀에 합류하면 시스템은 409 `TEAM_FULL` 을 MUST 돌려준다.

#### Scenario: 정원 초과
- **WHEN** 이미 6명인 팀의 초대코드로 합류하면
- **THEN** 409 `TEAM_FULL` 을 받고 팝업 「팀 정원이 찼음」 / 「기획팀은 이미 6명. owner 에게 문의」가 뜬다

### Requirement: 멤버 목록
<!-- 근거: F-01 · D-03 · team.html / 정의서 7-1 -->
시스템은 `GET /api/teams/{id}/members` 로 `id · name · email · role · todo_count` 를 MUST 돌려준다. todo_count 는 그 멤버에게 배정된 할 일 전부(완료 포함)의 수다. 다른 팀의 멤버 목록은 403 `FORBIDDEN` 이다. 담당자 고르기 후보도 이 목록이다.

#### Scenario: 멤버 목록
- **WHEN** 4명인 팀의 멤버가 목록을 조회하면
- **THEN** 4명과 각자의 role · todo_count 를 받고, 화면은 「멤버 (4/6)」로 보여 준다

### Requirement: 초대코드 복사
<!-- 근거: F-04 · team.html -->
화면은 「복사」를 누르면 초대코드를 클립보드에 넣고 띠 알림 「초대코드를 복사함 - MN-7K2D」를 MUST 띄운다. 복사는 member 도 할 수 있다. 팀당 코드는 하나다.

#### Scenario: member 의 코드 복사
- **WHEN** member 가 「복사」를 누르면
- **THEN** 코드가 복사되고 띠 알림이 뜬다

### Requirement: 초대코드 재발급
<!-- 근거: F-05 · F-08 · team.html / 정의서 7-4 -->
시스템은 `PUT /api/teams/{id}/code` 로 새 초대코드를 발급하고 이전 코드를 폐기한다(SHALL). 이미 합류한 멤버는 그대로다. owner 만 할 수 있으며 member 가 부르면 403 `OWNER_ONLY` 를 MUST 돌려준다.

#### Scenario: owner 의 재발급
- **WHEN** owner 가 「재발급」을 누르면
- **THEN** 200 과 새 코드를 받고, 이전 코드로 합류하면 404 `INVITE_NOT_FOUND` 다

#### Scenario: member 의 재발급
- **WHEN** member 가 재발급 API 를 부르면
- **THEN** 403 `OWNER_ONLY` 를 받고, 화면에서는 「재발급」 버튼이 비활성이다

### Requirement: 팀 이름 변경
<!-- 근거: F-07 · F-08 · team.html / 정의서 7 -->
시스템은 `PUT /api/teams/{id}` 로 팀 이름을 바꾼다(SHALL). owner 만 할 수 있으며 member 가 부르면 403 `OWNER_ONLY` 를 MUST 돌려준다.

#### Scenario: owner 의 이름 변경
- **WHEN** owner 가 팀 이름을 `기획2팀` 으로 저장하면
- **THEN** 200 을 받고 띠 알림 「팀 이름 저장」이 뜬다

#### Scenario: member 화면
- **WHEN** member 가 팀 설정 화면을 열면
- **THEN** 팀 이름 칸과 「저장」 · 「재발급」은 잠겨 있고 「복사」만 켜져 있다
