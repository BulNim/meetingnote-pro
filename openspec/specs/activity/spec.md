# activity Specification

## Purpose

팀 안에서 일어난 행위를 누가 언제 무엇에 했는지 남기고, 팀 활동과 내 활동으로 보여 주는 동작을 정한다. 활동 종류는 다섯 가지로 닫혀 있다.

## Requirements

### Requirement: 활동 종류 다섯 가지
<!-- 근거: 프로그램정의 6 · F-01 / team.html · J-07 / profile.html -->
활동 기록의 `kind` 는 `meeting_add` · `todo_assign` · `todo_done` · `comment_add` · `member_join` 다섯 가지뿐이어야 한다(SHALL). 이 밖의 값은 만들지 않는다. 회의록 저장은 `meeting_add`, 할 일에 새 담당자가 생기면 `todo_assign`, 할 일이 완료되면 `todo_done`, 댓글 등록은 `comment_add`, 초대코드 합류는 `member_join` 을 남긴다. 팀 생성 · 회의록 수정과 삭제 · 상태를 완료가 아닌 값으로 바꾸는 일 · 계정 변경은 남기지 않는다.

#### Scenario: 다섯 가지 밖은 기록하지 않음
- **WHEN** 팀 이름을 바꾸거나 내 이름을 바꾼다
- **THEN** 활동 기록이 늘지 않는다

#### Scenario: 완료가 아닌 상태 변경
- **WHEN** 할 일을 대기에서 진행으로 옮긴다
- **THEN** 활동 기록이 늘지 않는다

### Requirement: 팀 활동 기록
<!-- 근거: F-01 / team.html -->
`GET /api/teams/{id}/activities` 는 최근 순(내림차순)으로 최근 50건까지 `id` · `kind` · `actor_name` · `text` · `created_at` 을 돌려줘야 한다(SHALL). `text` 는 서버가 만든 완성 문장이고 화면은 그대로 그린다. 예: 「회의록 「2차 스프린트 계획 회의」 등록」, 「할 일 「사용자 다섯 분 인터뷰」를 최선임에게 배정」, 「할 일 「배포 키 환경변수 이전」 완료」, 「회의록 「배포 환경 점검」에 댓글 작성」, 「초대코드로 합류」.

#### Scenario: 최근 50건
- **WHEN** 활동이 60건 쌓인 팀이 목록을 부른다
- **THEN** 가장 최근 50건이 최근 순으로 온다

#### Scenario: 완성 문장
- **WHEN** 회의록 등록 활동을 조회한다
- **THEN** `text` 가 「회의록 「제목」 등록」 형태의 완성 문장이다

### Requirement: 내 활동 기록
<!-- 근거: J-01 · J-07 / profile.html -->
`GET /api/me/activities` 는 로그인한 사람이 행위자인 활동만 같은 형식과 같은 정렬로 돌려줘야 한다(SHALL). 합류 직후처럼 활동이 없으면 200 과 빈 배열이고 화면은 「아직 활동이 없음」 을 보인다.

#### Scenario: 내 활동만
- **WHEN** 두 사람의 활동이 섞인 팀에서 내 활동을 부른다
- **THEN** 내가 행위자인 것만 온다

#### Scenario: 활동 없음
- **WHEN** 합류 직후 사용자가 내 활동을 부른다
- **THEN** 200 과 빈 배열이고 빈 안내가 보인다

### Requirement: 활동 띠 색
<!-- 근거: 프로그램정의 7-2 / team.html · profile.html -->
활동 카드의 띠 색은 `kind` 로 정해야 한다(SHALL). `meeting_add` 는 blue, `todo_assign` 은 orange, `todo_done` 은 green, `comment_add` 와 `member_join` 은 purple 이며 팔레트 5색 안에서만 쓴다. 화면은 `theme.js` 의 `STRIPE` 이름으로만 색을 쓴다.

#### Scenario: 완료 활동의 색
- **WHEN** `todo_done` 활동을 그린다
- **THEN** 카드 좌측 띠가 green 이다
