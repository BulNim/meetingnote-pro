# Spec Delta

## ADDED Requirements

### Requirement: 회의 날짜를 고치면 할 일 기한 다시 환산
<!-- 근거: D-02 · detail.html · modify-todo-due-date (지시) -->
시스템은 `PUT /api/meetings/{id}` 로 met_at 이 바뀌면 그 회의록에서 뽑힌 할 일의 due_date 를 새 회의 날짜를 기준일로 MUST 다시 환산한다. due_text 와 그 밖의 칸은 바꾸지 않는다. 본문 · 제목 · 참석자만 고치면 기한은 그대로다.

#### Scenario: 회의 날짜 변경
- **GIVEN** 회의 날짜 2026-11-12 회의록에 기한 「내일」(due_date 2026-11-13)인 할 일이 있고
- **WHEN** 회의 시각을 2026-11-19 로 고치면
- **THEN** 그 할 일의 due_date 는 2026-11-20 이 되고 due_text 는 「내일」 그대로다

#### Scenario: 제목만 수정
- **WHEN** 제목만 고치면
- **THEN** 딸린 할 일의 due_date 는 바뀌지 않는다

## MODIFIED Requirements

### Requirement: 할 일 담당자 대조
<!-- 근거: 정의서 7-3 · 6 · modify-todo-due-date -->
시스템은 뽑힌 할 일의 담당자 이름을 팀 멤버 이름과 공백 · 존칭(님)을 무시하고 MUST 대조해, 맞는 멤버가 없으면 담당자를 미정(null)으로 둔다. 할 일은 `내용 | 담당자 | 기한` 한 줄씩이며, 기한은 받아쓴 글자 그대로 due_text 에 두고, 회의 시각(met_at)의 한국 날짜를 기준일로 환산한 날짜를 due_date 에 둔다. 담당자가 붙은 할 일마다 활동 todo_assign 을 남긴다.

#### Scenario: 존칭 붙은 담당자
- **WHEN** 할 일 줄이 `목록 정리 | 이주임님 | 다음 주 금요일` 이고 멤버 `이주임` 이 있으면
- **THEN** 담당자는 이주임, due_text 는 「다음 주 금요일」이고 todo_assign 활동이 생긴다

#### Scenario: 멤버가 아닌 담당자
- **WHEN** 할 일 줄의 담당자가 팀에 없는 이름이면
- **THEN** 담당자는 미정으로 저장되고 이름을 지어내지 않는다

#### Scenario: 회의 날짜 기준 기한
- **GIVEN** 회의 시각이 2026-11-12(목) 14:00(한국)이고
- **WHEN** 할 일 줄이 `목록 정리 | 이주임 | 다음 주 금요일` 이면
- **THEN** due_text 는 「다음 주 금요일」, due_date 는 2026-11-20 이다
