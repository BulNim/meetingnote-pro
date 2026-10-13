# Spec Delta

## Purpose

회의에서 나온 할 일을 대기 · 진행 · 완료 세 열 칸반으로 추적하고, 담당자를 배정하며, 팀원이 자기에게 배정된 일만 모아 볼 수 있게 하는 기능이다.

## ADDED Requirements

### Requirement: 할 일 목록
<!-- E-01, E-02, E-12 todos.html -->
시스템은 `GET /api/teams/{id}/todos` 와 `GET /api/me/todos` 로 `id · what · assignee_id · assignee_name · due_text · status · meeting_title` 을 `status` 다음 `due_text` 순으로 돌려줘야 한다(SHALL). `status` 는 `OPEN` · `DOING` · `DONE` 셋뿐이고, 할 일이 없으면 200 과 빈 배열이다.

#### Scenario: 내 할 일
- **WHEN** 담당자로 배정된 사용자가 `GET /api/me/todos` 를 호출한다
- **THEN** 본인에게 배정된 할 일만 돌아온다

#### Scenario: 팀 전체 할 일
- **WHEN** 멤버가 `GET /api/teams/{id}/todos` 를 호출한다
- **THEN** 그 팀의 모든 할 일이 회의록 제목과 함께 돌아온다

#### Scenario: 빈 상태
- **WHEN** 할 일이 하나도 없다
- **THEN** 200 과 빈 배열이 돌아온다

### Requirement: 상태 변경
<!-- E-03, E-04, E-05, D-04 todos.html, detail.html -->
시스템은 `PUT /api/todos/{id}` 로 상태를 `OPEN` · `DOING` · `DONE` 중 하나로 바꾸게 해야 한다(SHALL). `DONE` 으로 바뀌면 활동 기록 `todo_done` 을 남긴다. 화면은 카드 끌기(포인터 이벤트)와 좁은 화면의 눌러서 칸 고르기를 모두 지원한다.

#### Scenario: 완료로 이동
- **WHEN** 담당 멤버가 진행 중 카드를 완료로 옮긴다
- **THEN** 200 이 돌아오고 `todo_done` 활동이 남는다

#### Scenario: 잘못된 상태 값
- **WHEN** `status` 에 `DONE` 이 아닌 임의 문자열을 보낸다
- **THEN** 400 `VALIDATION_ERROR` 가 돌아오고 상태는 그대로이다

### Requirement: 담당자 배정
<!-- E-06, D-03 todos.html, detail.html -->
시스템은 `PUT /api/todos/{id}` 로 담당자를 같은 팀 멤버로 지정하게 해야 한다(SHALL). 배정하면 활동 기록 `todo_assign` 을 남긴다. 팀 멤버가 아닌 사용자를 지정하면 400 `VALIDATION_ERROR` 이다.

#### Scenario: 담당자 배정
- **WHEN** 멤버가 할 일에 팀 멤버 김대리를 배정한다
- **THEN** 200 이 돌아오고 `assignee_name` 이 김대리이며 `todo_assign` 이 남는다

#### Scenario: 팀 밖 사용자 배정
- **WHEN** 다른 팀 사용자를 담당자로 보낸다
- **THEN** 400 `VALIDATION_ERROR` 가 돌아온다

### Requirement: 할 일 삭제 (owner 전용)
<!-- E-11 todos.html -->
시스템은 `DELETE /api/todos/{id}` 를 owner 에게만 허용해야 하며(SHALL), 성공하면 204 이다. member 가 호출하면 403 `OWNER_ONLY` 이다.

#### Scenario: owner 삭제
- **WHEN** owner 가 할 일을 삭제한다
- **THEN** 204 가 돌아오고 목록에서 사라진다

#### Scenario: member 삭제
- **WHEN** member 가 삭제를 요청한다
- **THEN** 403 `OWNER_ONLY` 가 돌아온다

### Requirement: 기한 지남 판정
<!-- E-08 todos.html -->
시스템은 기한 지남을 판정하지 않아야 한다(MUST). `due_text` 는 자유 글자로 저장하며, 화면이 지난 날짜를 읽어 붉은 띠로 표시하고 완료된 할 일은 제외한다.

#### Scenario: 서버는 비교하지 않음
- **WHEN** `due_text` 가 어제 날짜인 할 일을 조회한다
- **THEN** 응답에는 기한 지남 표시 필드가 없고 `due_text` 만 있다
