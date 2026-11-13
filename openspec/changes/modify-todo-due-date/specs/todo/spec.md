# Spec Delta

## ADDED Requirements

### Requirement: 기한 글자를 날짜로 환산
<!-- 근거: modify-todo-due-date (지시) -->
시스템은 할 일의 기한 글자 `due_text` 를 기준일에서 날짜 `due_date`(YYYY-MM-DD)로 MUST 환산해 저장한다. 원래 글자는 지우지 않는다. 정할 수 없는 글자면 `due_date` 를 null 로 둔다. 환산은 고정 규칙으로 하며 같은 글자 · 같은 기준일이면 늘 같은 날짜다. 한 주는 월요일에 시작하고, 날짜는 한국 시간 기준이다.

#### Scenario: 다음 주 금요일
- **GIVEN** 기준일이 2026-11-12(목)이고
- **WHEN** 기한 글자가 「다음 주 금요일」이면
- **THEN** due_date 는 2026-11-20 이고 due_text 는 「다음 주 금요일」 그대로다

#### Scenario: 다음 주까지
- **GIVEN** 기준일이 2026-11-12 이고
- **WHEN** 기한 글자가 「다음 주까지」이면
- **THEN** due_date 는 7일 뒤인 2026-11-19 다

#### Scenario: 정할 수 없는 글자
- **WHEN** 기한 글자가 「이번 주 안」 · 「미정」 · 「곧」 · 빈 값 중 하나이면
- **THEN** due_date 는 null 이고 due_text 는 받은 글자 그대로 남는다

### Requirement: 환산 규칙
<!-- 근거: modify-todo-due-date (지시) -->
시스템은 기한 글자 끝의 「까지 · 안에 · 내 · 중 · 쯤」과 공백을 지운 뒤 아래 표현만 날짜로 MUST 바꾼다(B=기준일). 오늘 B · 내일 B+1 · 모레 B+2 · 어제 B-1 · N일 뒤(후) B+N · N주 뒤(후) B+7N · 다음 주 B+7 · 지난 주 B-7 · (이번 주) X요일 그 주 X요일 · 다음 주 X요일 · 지난 주 X요일 · 이번 달 말 · 다음 달 말 · (이번 달) N일 · 다음 달 N일 · M월 N일 · M/D · YYYY-MM-DD. 그 밖은 null 이다.

#### Scenario: 요일만 적힌 기한
- **GIVEN** 기준일이 2026-11-12(목)이고
- **WHEN** 기한 글자가 「금요일까지」이면
- **THEN** due_date 는 같은 주 금요일 2026-11-13 이다

#### Scenario: 지난 요일
- **GIVEN** 기준일이 2026-11-12(목)이고
- **WHEN** 기한 글자가 「월요일」이면
- **THEN** due_date 는 같은 주 월요일 2026-11-09 다 (이미 지난 날이어도 같은 주로 본다)

#### Scenario: 다음 달 며칠
- **GIVEN** 기준일이 2026-11-12 이고
- **WHEN** 기한 글자가 「다음 달 10일」이면
- **THEN** due_date 는 2026-12-10 이다

#### Scenario: 월 일이 기준일보다 앞
- **GIVEN** 기준일이 2026-11-12 이고
- **WHEN** 기한 글자가 「1월 5일」이면
- **THEN** due_date 는 다음 해 2027-01-05 다

#### Scenario: 없는 날짜
- **WHEN** 기한 글자가 「2월 30일」이면
- **THEN** due_date 는 null 이다

### Requirement: 기준일
<!-- 근거: modify-todo-due-date (지시) -->
환산 기준일은 회의록에서 뽑힌 할 일이면 그 회의록의 회의 시각(met_at)의 한국 날짜이고, 직접 등록한 할 일이면 등록한 날의 한국 날짜다(MUST). 기한 글자를 고치면 같은 기준일로 다시 환산한다.

#### Scenario: 회의 날짜 기준
- **GIVEN** 회의 시각이 2026-11-11T23:30:00Z(한국 11-12 08:30)인 회의록에서
- **WHEN** 「내일」 기한의 할 일이 뽑히면
- **THEN** due_date 는 2026-11-13 이다

#### Scenario: 기한 글자 수정
- **GIVEN** 회의 날짜 2026-11-12 회의록에서 뽑힌 할 일의 기한 글자를
- **WHEN** `PUT /api/todos/{id}` 로 「다음 주 월요일」로 바꾸면
- **THEN** 응답의 due_text 는 「다음 주 월요일」, due_date 는 2026-11-16 이다

### Requirement: 이미 저장된 할 일의 기한 채우기
<!-- 근거: modify-todo-due-date (지시) -->
시스템은 시작할 때 할 일 표에 `due_date` 칸이 없으면 MUST 추가하고, `due_date` 가 비어 있고 `due_text` 가 있는 할 일을 같은 규칙과 기준일로 한 번 채운다. 이미 채워진 값은 바꾸지 않는다. SQLite 와 Postgres 모두 같다.

#### Scenario: add-mvp-core 데이터
- **GIVEN** due_date 칸이 없는 DB 에 「다음 주 금요일」 기한의 할 일이 있고
- **WHEN** 서버를 시작하면
- **THEN** 칸이 추가되고 그 할 일의 due_date 가 회의 날짜 기준 날짜로 채워진다

#### Scenario: 두 번 시작
- **WHEN** 이미 채운 뒤 서버를 다시 시작하면
- **THEN** 칸을 다시 만들지 않고 값도 바뀌지 않는다

## MODIFIED Requirements

### Requirement: 팀 할 일 목록
<!-- 근거: E-02 · todos.html / 정의서 7-1 · modify-todo-due-date -->
시스템은 `GET /api/teams/{id}/todos` 로 `id · what · assignee_id · assignee_name · due_text · due_date · status · meeting_title · can_delete` 를 status 다음 due_date 순(due_date 가 null 인 것은 각 상태의 뒤)으로 MUST 돌려준다. due_date 는 YYYY-MM-DD 문자열 또는 null 이다. 직접 등록한 할 일은 meeting_title 이 null 이며 화면은 출처를 「직접 등록」으로 그린다.

#### Scenario: 전체 탭
- **WHEN** 칸반에서 「전체」 탭을 누르면
- **THEN** 팀 할 일 전부가 대기 · 진행 · 완료 칸에 나뉘어 보이고 카드마다 출처 회의록 제목이 있다

#### Scenario: 기한 순 정렬
- **GIVEN** 대기 할 일 셋의 due_date 가 2026-11-20 · null · 2026-11-13 이면
- **WHEN** 팀 할 일 목록을 조회하면
- **THEN** 2026-11-13 · 2026-11-20 · null 순으로 온다

### Requirement: 할 일 직접 등록
<!-- 근거: E-13 · todos.html / 정의서 7-4 · modify-todo-due-date -->
시스템은 `POST /api/teams/{id}/todos` 로 내용(필수) · 담당자 · 기한을 받아 회의록 없이 할 일을 만들고 201 을 MUST 돌려준다. 상태는 OPEN 으로 시작한다. 기한 글자는 등록한 날을 기준일로 due_date 로 환산한다. 담당자가 있으면 활동 todo_assign 을 남긴다.

#### Scenario: 새 할 일
- **WHEN** 「새 할 일」 팝업에서 내용 · 담당자 · 기한을 넣고 「등록」을 누르면
- **THEN** 201 을 받고 대기 칸에 출처 「직접 등록」 카드가 생긴다

#### Scenario: 직접 등록의 기한 환산
- **GIVEN** 오늘(한국)이 2026-11-13(금)이고
- **WHEN** 기한 「다음 주까지」로 직접 등록하면
- **THEN** 응답의 due_date 는 2026-11-20 이다

### Requirement: 담당자 배정
<!-- 근거: D-03 · E-06 · todos.html · detail.html · modify-todo-due-date -->
시스템은 `PUT /api/todos/{id}` 로 assignee_id 와 due_text 를 바꾼다(SHALL). due_text 를 바꾸면 그 할 일의 기준일로 due_date 를 다시 환산한다. 담당자는 팀 멤버이거나 미정(null)이어야 하며, 다른 팀 사람이면 400 `VALIDATION_ERROR` 를 MUST 돌려준다. 담당자가 새로 붙으면 활동 todo_assign 을 남긴다. 후보는 `GET /api/teams/{id}/members` 다.

#### Scenario: 미정에 담당자 지정
- **WHEN** 담당 미정 카드의 배지를 눌러 박과장을 고르면
- **THEN** 200 을 받고 카드에 박과장이 보이며 todo_assign 활동이 생긴다

#### Scenario: 기한을 비움
- **WHEN** due_text 를 빈 문자열로 보내면
- **THEN** due_text 와 due_date 가 모두 비고 카드에 기한 「미정」이 보인다

### Requirement: 화면 필터와 기한 판정
<!-- 근거: E-07 · E-08 · E-09 · E-10 · todos.html / 정의서 7-2 · modify-todo-due-date -->
화면은 담당자 필터를 서버 재호출 없이 MUST 화면에서 거른다. 기한 지남은 화면이 판정하며 due_date 가 오늘(보는 사람의 날짜)보다 앞이고 완료가 아닌 카드에만 붉은 띠를 붙인다. due_date 가 null 이면 판정하지 않는다. 기한 배지는 due_date 를 「11-20 (금)」처럼 보여 주고 원래 글자도 함께 보이게 하며, due_date 가 없으면 글자만 보인다. 담당자가 없으면 「미정」으로 보이고, 완료 카드도 지우지 않고 남긴다.

#### Scenario: 담당자 필터
- **WHEN** 필터를 「담당자: 박과장」으로 바꾸면
- **THEN** 서버 요청 없이 박과장 카드만 남는다

#### Scenario: 기한 지남
- **GIVEN** 오늘이 2026-11-13 이고
- **WHEN** due_date 가 2026-11-12 인 대기 카드와 2026-11-06 인 완료 카드가 있으면
- **THEN** 대기 카드만 붉은 띠이고 완료 카드는 판정하지 않는다

#### Scenario: 날짜를 정하지 못한 기한
- **WHEN** due_text 가 「이번 주 안」이고 due_date 가 null 인 카드가 있으면
- **THEN** 기한 배지에 「이번 주 안」 글자만 보이고 붉은 띠는 붙지 않는다

#### Scenario: 기한 배지
- **WHEN** due_text 가 「다음 주 금요일」, due_date 가 2026-11-20 인 카드를 보면
- **THEN** 기한 배지에 「11-20 (금)」과 원래 글자 「다음 주 금요일」이 함께 보인다
