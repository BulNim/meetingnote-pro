# todo Specification

## Purpose

회의에서 나온 할 일을 대기 · 진행 · 완료 3열 칸반으로 추적하고, 담당자와 기한을 바꾸고, 내 할 일과 팀 전체를 보는 동작을 정한다. 할 일은 회의록 저장 때 만들어지며 따로 만드는 API 는 없다.

## Requirements

### Requirement: 할 일 목록 조회
<!-- 근거: E-01 · E-02 · E-12 / todos.html -->
`GET /api/teams/{id}/todos` 는 팀 전체 할 일을, `GET /api/me/todos` 는 로그인한 사람에게 배정된 것만 돌려줘야 한다(SHALL). 각 항목은 `id` · `what` · `assignee_id` · `assignee_name` · `due_text` · `status` 에 `meeting_title` 을 더한다. 정렬은 `status` 다음 `due_text` 순이다. 없으면 200 과 빈 배열이고 화면은 「배정된 할 일이 없음」 을 보인다.

#### Scenario: 내 할 일
- **WHEN** `GET /api/me/todos` 를 부른다
- **THEN** 로그인한 사람에게 배정된 할 일만 오고 각 항목에 회의록 제목이 있다

#### Scenario: 팀 전체
- **WHEN** `GET /api/teams/{id}/todos` 를 부른다
- **THEN** 팀의 모든 할 일이 오고 회의록 제목이 함께 온다

#### Scenario: 할 일 없음
- **WHEN** 배정된 할 일이 없다
- **THEN** 200 과 빈 배열이고 칸반 대신 빈 안내가 보인다

### Requirement: 칸반 3열
<!-- 근거: E-01 · E-10 / todos.html -->
칸반은 대기(`OPEN`, orange) · 진행(`DOING`, blue) · 완료(`DONE`, green) 세 열이어야 한다(SHALL). 상태는 이 셋뿐이고 되돌림도 허용한다. 완료된 할 일도 지우지 않고 남긴다. 화면은 완료 건수 합계(「N / M 완료」)를 보인다.

#### Scenario: 완료만 보기
- **WHEN** 완료 열을 본다
- **THEN** 완료된 할 일이 지워지지 않고 남아 있다

### Requirement: 상태 변경
<!-- 근거: E-03 · E-04 · E-05 / todos.html · D-04 / detail.html -->
`PUT /api/todos/{id}` 는 `status` 를 바꿀 수 있어야 하며 팀원 누구나 할 수 있다(SHALL). 화면은 카드를 끌어 놓을 때 한 번만 호출하고, 실패하면 카드를 원래 칸으로 돌린다. 좁은 화면에서는 카드를 눌러 대기 · 진행 · 완료 버튼 중 하나를 고른다. `DONE` 으로 바뀌면 `todo_done` 활동을 남긴다.

#### Scenario: 끌어서 이동
- **WHEN** 대기의 카드를 진행 칸에 놓는다
- **THEN** `PUT /api/todos/{id}` 가 한 번 호출되고 200 이면 카드가 진행에 남는다

#### Scenario: 이동 실패
- **WHEN** 이동 호출이 실패한다
- **THEN** 카드가 원래 칸으로 돌아간다

#### Scenario: 누르는 길
- **WHEN** 끌 수 없는 좁은 화면에서 카드를 누른다
- **THEN** 대기 · 진행 · 완료 버튼 세 개가 나타나 고른 칸으로 옮겨진다

#### Scenario: 완료 활동
- **WHEN** 상태를 `DONE` 으로 바꾼다
- **THEN** `todo_done` 활동이 한 건 남는다

### Requirement: 담당자 배정
<!-- 근거: E-06 · E-09 / todos.html · D-03 / detail.html -->
`PUT /api/todos/{id}` 는 `assignee_id` 를 팀 멤버 중 한 명으로 바꾸거나 비워 담당자 미정으로 만들 수 있어야 한다(SHALL). 팀원 누구나 할 수 있다. 담당자가 바뀌어 새 담당자가 생기면 `todo_assign` 활동을 남긴다. 미정은 회의에서 정해지지 않은 것이며 임의로 채우지 않는다.

#### Scenario: 담당자 배정
- **WHEN** 담당자 미정 할 일에 최선임을 지정한다
- **THEN** 200 을 받고 `todo_assign` 활동이 남는다

#### Scenario: 다른 팀 사람은 배정 불가
- **WHEN** 팀에 속하지 않은 사용자 id 로 배정을 요청한다
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 기한 변경과 지남 표시
<!-- 근거: E-08 / todos.html -->
`PUT /api/todos/{id}` 로 `due_text` 를 바꿀 수 있어야 한다(SHALL). 서버는 기한을 날짜로 해석하거나 비교하지 않는다. 화면은 완료되지 않은 할 일 중 기한이 `YYYY-MM-DD` 형식이고 오늘보다 앞서거나, 글자가 「어제」 · 「지난 주」 · 「지난 달」 이면 카드 좌측에 red 띠와 red 글자를 보인다. 기한 입력 방식은 이번 회차에서 `publish/todos.html` 의 방식을 따르며 차후 논의한다.

#### Scenario: 지난 날짜
- **WHEN** 완료되지 않은 할 일의 기한이 오늘보다 앞선 `2026-09-12` 다
- **THEN** 카드에 red 띠가 보인다

#### Scenario: 완료한 것은 제외
- **WHEN** 기한이 「지난 주」 인 할 일이 완료 상태다
- **THEN** 붉은 띠가 보이지 않는다

#### Scenario: 서버는 비교하지 않음
- **WHEN** `due_text` 에 「다음 주 금요일」 을 저장한다
- **THEN** 서버는 형식 검사나 날짜 비교 없이 그대로 저장한다

### Requirement: 담당자 필터
<!-- 근거: E-07 / todos.html -->
담당자 필터는 이미 받은 목록에서 화면이 거르고 서버를 다시 부르지 않아야 한다(SHALL). 「담당자 전체」 와 각 멤버 · 미정을 고를 수 있다.

#### Scenario: 필터는 서버를 부르지 않음
- **WHEN** 담당자를 박과장으로 거른다
- **THEN** 추가 API 호출 없이 박과장의 카드만 보인다

### Requirement: 할 일 삭제는 owner 만
<!-- 근거: E-11 · F-08 / todos.html -->
`DELETE /api/todos/{id}` 는 팀의 owner 만 할 수 있고 204 를 돌려줘야 한다(SHALL). member 가 부르면 403 `OWNER_ONLY` 다. 화면은 member 에게 삭제 버튼을 비활성으로 보인다.

#### Scenario: owner 의 삭제
- **WHEN** owner 가 할 일을 삭제한다
- **THEN** 204 를 받고 목록에서 사라진다

#### Scenario: member 의 삭제 시도
- **WHEN** member 가 삭제를 요청한다
- **THEN** 403 `OWNER_ONLY` 를 받고 할 일은 남는다

### Requirement: 회의록 상세의 할 일 칸
<!-- 근거: D-03 · D-04 · D-06 / detail.html -->
회의록 상세의 「할 일」 칸은 그 회의에서 나온 할 일을 담당자 선택과 기한 · 상태 라벨과 함께 보여야 한다(SHALL). 담당자 선택에는 「미정」 과 팀 멤버가 있다. 할 일이 없으면 「담당자와 기한이 드러난 항목 없음」 을 보인다.

#### Scenario: 담당자 선택
- **WHEN** 상세 화면에서 담당자 선택을 바꾼다
- **THEN** `PUT /api/todos/{id}` 가 호출되고 200 이면 화면에 반영된다

#### Scenario: 할 일 없는 회의
- **WHEN** 그 회의에서 나온 할 일이 0건이다
- **THEN** 할 일 칸에 「담당자와 기한이 드러난 항목 없음」 이 보인다
