# comment Specification

## Purpose

팀원이 회의록의 결정과 내용에 의견을 달고 지우는 댓글 동작을 정한다. 댓글은 회의록 상세 화면에서 보고 쓴다.

## Requirements

### Requirement: 댓글 등록
<!-- 근거: D-09 · D-10 / detail.html -->
`POST /api/meetings/{id}/comments` 는 내용을 받아 댓글을 만들고 201 을 돌려줘야 한다(SHALL). 내용은 500자 이내이며 비었거나 500자를 넘으면 400 `VALIDATION_ERROR` 다. 등록하면 `comment_add` 활동을 남기고, 화면은 입력칸을 비우고 목록 맨 아래에 새 댓글을 붙인다.

#### Scenario: 정상 등록
- **WHEN** 팀원이 「받아쓰기 실패는 세 칸을 비우기로 했습니다」 를 등록한다
- **THEN** 201 을 받고 입력칸이 비워지며 목록 맨 아래에 붙고 `comment_add` 활동이 남는다

#### Scenario: 500자 초과
- **WHEN** 501자 내용을 보낸다
- **THEN** 400 `VALIDATION_ERROR` 를 받고 댓글은 만들어지지 않는다

### Requirement: 댓글 목록
<!-- 근거: D-01 · D-11 / detail.html -->
`GET /api/meetings/{id}/comments` 는 `created_at` 오름차순으로 `id` · `user_id` · `user_name` · `content` · `created_at` 에 `can_delete` 를 더해 돌려줘야 한다(SHALL). `can_delete` 는 로그인한 사람이 쓴 사람이거나 팀 owner 이면 참이며 서버가 판정한다. 댓글이 없으면 200 과 빈 배열이고 화면은 「아직 댓글이 없음」 을 보인다.

#### Scenario: 삭제 가능 표시
- **WHEN** member 가 목록을 부른다
- **THEN** 자기가 쓴 댓글만 `can_delete` 가 참이다

#### Scenario: 댓글 없음
- **WHEN** 댓글이 없는 회의록을 연다
- **THEN** 200 과 빈 배열이고 빈 안내가 보인다

### Requirement: 댓글 삭제
<!-- 근거: D-12 / detail.html -->
`DELETE /api/comments/{id}` 는 쓴 사람과 팀 owner 만 할 수 있고 204 를 돌려줘야 한다(SHALL). 그 밖의 사람은 403 `FORBIDDEN` 이다. 화면은 `can_delete` 가 참인 댓글에만 삭제 버튼을 보인다.

#### Scenario: 쓴 사람의 삭제
- **WHEN** 쓴 사람이 삭제한다
- **THEN** 204 를 받고 목록에서 사라진다

#### Scenario: 남의 댓글 삭제 시도
- **WHEN** owner 가 아닌 다른 member 가 삭제를 요청한다
- **THEN** 403 `FORBIDDEN` 을 받고 댓글은 남는다
