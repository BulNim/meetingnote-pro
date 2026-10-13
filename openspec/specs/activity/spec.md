# activity Specification

## Purpose
팀에서 누가 언제 무엇을 했는지 기록해 이번 주 팀 흐름과 내 활동을 한눈에 보게 하는 기능이다. 기록은 서버가 문장으로 만들어 화면은 그대로 그린다.

## Requirements

### Requirement: 활동 종류 고정
<!-- F-01 team.html, 정의서 6절 -->
시스템은 활동 기록의 `kind` 를 `meeting_add` · `todo_assign` · `todo_done` · `comment_add` · `member_join` 다섯 가지만 만들어야 하며(MUST), 이 밖의 값을 만들지 않는다. 각 동작이 성공하면 행위자 · 시점 · 대상을 함께 기록한다.

#### Scenario: 회의록 추가 기록
- **WHEN** 멤버가 회의록을 저장한다
- **THEN** `kind=meeting_add` 활동이 행위자와 회의록 제목으로 남는다

### Requirement: 팀 활동 조회
<!-- F-01 team.html -->
시스템은 `GET /api/teams/{id}/activities` 로 `id · kind · actor_name · text · created_at` 을 최신순으로 최근 50건까지 돌려줘야 한다(SHALL). `text` 는 서버가 만든 완성 문장이다.

#### Scenario: 50건 제한
- **WHEN** 활동이 60건 쌓인 팀을 조회한다
- **THEN** 가장 최근 50건만 최신순으로 돌아온다

### Requirement: 내 활동 조회
<!-- J-07 profile.html -->
시스템은 `GET /api/me/activities` 로 로그인한 사용자 본인의 활동을 같은 형식으로 돌려줘야 하며(SHALL), 없으면 200 과 빈 배열이다.

#### Scenario: 활동 없음
- **WHEN** 합류 직후 활동이 없는 사용자가 조회한다
- **THEN** 200 과 빈 배열이 돌아오고 화면은 "활동 0건" 을 보인다

### Requirement: 활동 띠 색
<!-- 정의서 7-2 활동 기록 띠 색 -->
화면은 활동 종류별 띠 색을 `meeting_add=blue` · `todo_assign=orange` · `todo_done=green` · `comment_add=purple` · `member_join=purple` 로 그려야 하며(SHALL), 팔레트 5색 밖의 색을 쓰지 않는다.

#### Scenario: 완료 활동의 색
- **WHEN** `todo_done` 활동이 목록에 그려진다
- **THEN** 좌측 띠가 green 이다
