# Spec Delta

## Purpose

팀원이 회의록 아래에 의견과 질문을 남기고, 신규 합류자가 지난 결정의 맥락을 댓글로 묻게 하는 기능이다. 작성자와 owner 만 지울 수 있다.

## ADDED Requirements

### Requirement: 댓글 달기
<!-- D-09, D-10 detail.html -->
시스템은 `POST /api/meetings/{id}/comments` 로 내용을 받아 댓글을 저장하고 201 을 돌려줘야 한다(SHALL). 내용은 500자 이하이며 비었거나 넘으면 400 `VALIDATION_ERROR` 이다. 성공하면 활동 기록 `comment_add` 를 남긴다.

#### Scenario: 댓글 등록
- **WHEN** 멤버가 500자 이하 내용을 보낸다
- **THEN** 201 이 돌아오고 `comment_add` 가 남는다

#### Scenario: 500자 초과
- **WHEN** 501자 내용을 보낸다
- **THEN** 400 `VALIDATION_ERROR` 가 돌아오고 저장되지 않는다

### Requirement: 댓글 목록
<!-- D-01, D-11 detail.html -->
시스템은 `GET /api/meetings/{id}/comments` 로 `id · user_id · user_name · content · created_at · can_delete` 를 `created_at` 오름차순으로 돌려줘야 한다(SHALL). `can_delete` 는 작성자 본인이거나 owner 일 때 참이며 서버가 판정한다. 댓글이 없으면 200 과 빈 배열이다.

#### Scenario: can_delete 판정
- **WHEN** member 가 남의 댓글이 있는 목록을 조회한다
- **THEN** 본인 댓글만 `can_delete` 가 참이다

### Requirement: 댓글 삭제
<!-- D-12 detail.html -->
시스템은 `DELETE /api/comments/{id}` 를 작성자와 owner 에게만 허용하고 204 를 돌려줘야 한다(SHALL). 그 밖의 사용자는 403 `FORBIDDEN` 이다.

#### Scenario: 남의 댓글 삭제
- **WHEN** 작성자도 owner 도 아닌 member 가 삭제한다
- **THEN** 403 `FORBIDDEN` 이 돌아오고 댓글은 남는다

#### Scenario: owner 의 삭제
- **WHEN** owner 가 member 의 댓글을 삭제한다
- **THEN** 204 가 돌아오고 목록에서 사라진다
