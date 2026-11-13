# todo Specification

## Purpose
회의록에서 뽑히거나 칸반에서 직접 등록한 할 일을 대기 · 진행 · 완료 3열로 추적하고, 끌거나 눌러서 상태를 바꾸며 담당자를 배정 · 삭제하는 할 일 기능과 todos.html 화면의 동작을 정의한다.

## Requirements

### Requirement: 팀 할 일 목록
<!-- 근거: E-02 · todos.html / 정의서 7-1 -->
시스템은 `GET /api/teams/{id}/todos` 로 `id · what · assignee_id · assignee_name · due_text · status · meeting_title · can_delete` 를 status 다음 due_text 순으로 MUST 돌려준다. 직접 등록한 할 일은 meeting_title 이 null 이며 화면은 출처를 「직접 등록」으로 그린다.

#### Scenario: 전체 탭
- **WHEN** 칸반에서 「전체」 탭을 누르면
- **THEN** 팀 할 일 전부가 대기 · 진행 · 완료 칸에 나뉘어 보이고 카드마다 출처 회의록 제목이 있다

### Requirement: 내 할 일 목록
<!-- 근거: E-01 · E-12 · todos.html · profile.html -->
시스템은 `GET /api/me/todos` 로 로그인한 사람에게 배정된 할 일만 같은 필드로 MUST 돌려준다. 없으면 200 과 빈 배열이다.

#### Scenario: 내 할 일 탭
- **WHEN** 김대리가 「내 할 일」 탭을 보면
- **THEN** 김대리에게 배정된 카드만 보이고, 대기 칸이 비면 「김대리에게 배정된 대기 할 일 없음」이 보인다

#### Scenario: 배정된 할 일 0건
- **WHEN** 배정된 할 일이 없는 사람이 칸반을 열면
- **THEN** 「배정된 할 일이 없음」 / 「전체 탭에서 팀 할 일을 보거나 새 할 일로 직접 등록」이 보인다

### Requirement: 할 일 직접 등록
<!-- 근거: E-13 · todos.html / 정의서 7-4 -->
시스템은 `POST /api/teams/{id}/todos` 로 내용(필수) · 담당자 · 기한을 받아 회의록 없이 할 일을 만들고 201 을 MUST 돌려준다. 상태는 OPEN 으로 시작한다. 담당자가 있으면 활동 todo_assign 을 남긴다.

#### Scenario: 새 할 일
- **WHEN** 「새 할 일」 팝업에서 내용 · 담당자 · 기한을 넣고 「등록」을 누르면
- **THEN** 201 을 받고 대기 칸에 출처 「직접 등록」 카드가 생긴다

### Requirement: 상태 변경
<!-- 근거: D-04 · E-04 · todos.html · detail.html / 정의서 7-4 -->
시스템은 `PUT /api/todos/{id}` 로 status 를 OPEN · DOING · DONE 중 하나로 바꾼다(SHALL). 되돌림도 허용한다. 그 밖의 값은 400 `VALIDATION_ERROR` 다. DONE 이 되면 활동 todo_done 을 남기고, DOING 이동은 활동을 남기지 않는다(MUST). 상태 변경은 팀원 누구나 할 수 있다.

#### Scenario: 완료로 이동
- **WHEN** 진행 칸 카드를 완료로 옮기면
- **THEN** 200 을 받고 todo_done 활동이 생긴다

#### Scenario: 진행으로 이동
- **WHEN** 대기 카드를 진행으로 옮기면
- **THEN** 200 을 받고 활동 기록은 늘지 않는다

### Requirement: 끌어서 옮기기
<!-- 근거: E-03 · E-04 · todos.html / 정의서 5 · 7-2 -->
화면은 포인터 이벤트로 카드 끌기를 MUST 구현하고 HTML5 draggable 은 쓰지 않는다. 집으면 반투명 사본이 따라붙고 놓을 칸이 점선이 된다. 놓기 전에는 서버를 부르지 않고, 놓는 순간 한 번만 호출하며, 실패하면 카드가 원래 칸으로 돌아간다.

#### Scenario: 대기에서 진행으로 끌기
- **WHEN** 대기 칸 카드를 진행 칸 빈 자리에 놓으면
- **THEN** `PUT /api/todos/{id}` 가 한 번 나가고 띠 알림 「이동 완료 - 대기 > 진행」이 뜬다

#### Scenario: 저장 실패
- **WHEN** 놓은 뒤 PUT 이 실패하면
- **THEN** 카드는 원래 칸으로 돌아간다

### Requirement: 눌러서 칸 고르기
<!-- 근거: E-05 · N-01 · todos.html -->
화면은 카드를 누르면 대기 · 진행 · 완료 버튼이 든 「칸 고르기」 팝업을 MUST 띄운다. 지금 칸 버튼은 비활성이다. 360px 처럼 칸이 세로로 쌓여 끌 수 없는 화면은 이 길로 옮긴다.

#### Scenario: 좁은 화면에서 이동
- **WHEN** 360px 화면에서 대기 카드를 누르고 「진행」을 고르면
- **THEN** PUT 200 뒤 카드가 진행 칸으로 간다

### Requirement: 담당자 배정
<!-- 근거: D-03 · E-06 · todos.html · detail.html -->
시스템은 `PUT /api/todos/{id}` 로 assignee_id 와 due_text 를 바꾼다(SHALL). 담당자는 팀 멤버이거나 미정(null)이어야 하며, 다른 팀 사람이면 400 `VALIDATION_ERROR` 를 MUST 돌려준다. 담당자가 새로 붙으면 활동 todo_assign 을 남긴다. 후보는 `GET /api/teams/{id}/members` 다.

#### Scenario: 미정에 담당자 지정
- **WHEN** 담당 미정 카드의 배지를 눌러 박과장을 고르면
- **THEN** 200 을 받고 카드에 박과장이 보이며 todo_assign 활동이 생긴다

### Requirement: 화면 필터와 기한 판정
<!-- 근거: E-07 · E-08 · E-09 · E-10 · todos.html / 정의서 7-2 -->
화면은 담당자 필터를 서버 재호출 없이 MUST 화면에서 거른다. 기한 지남은 화면이 판정하며 due_text 가 「어제 · 지난 주 · 지난 달」인 미완료 카드에만 붉은 띠를 붙인다. 담당자가 없으면 「미정」으로 보이고, 완료 카드도 지우지 않고 남긴다.

#### Scenario: 담당자 필터
- **WHEN** 필터를 「담당자: 박과장」으로 바꾸면
- **THEN** 서버 요청 없이 박과장 카드만 남는다

#### Scenario: 기한 지남
- **WHEN** due_text 가 「어제」인 대기 카드와 「지난 주」인 완료 카드가 있으면
- **THEN** 대기 카드만 붉은 띠이고 완료 카드는 판정하지 않는다

### Requirement: 할 일 삭제
<!-- 근거: E-11 · todos.html / 정의서 7-4 -->
시스템은 `DELETE /api/todos/{id}` 로 할 일을 지우고 204 를 MUST 돌려준다. 만든 사람(회의록 올린 사람 또는 직접 등록한 사람) · 담당자 · owner 만 할 수 있고, 그 밖은 403 `FORBIDDEN` 이다. 목록의 can_delete 가 이 판정과 같아 화면은 삭제 버튼을 미리 끈다.

#### Scenario: 권한 없는 삭제
- **WHEN** 만든 사람도 담당자도 owner 도 아닌 이주임이 카드를 보면
- **THEN** can_delete 는 false 라 삭제가 꺼져 있고, API 를 직접 부르면 403 `FORBIDDEN` 이다

#### Scenario: 담당자의 삭제
- **WHEN** 담당자가 자기 카드를 삭제하면
- **THEN** 204 를 받고 카드가 사라진다
