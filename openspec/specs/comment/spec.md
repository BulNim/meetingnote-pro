# comment Specification

## Purpose
팀원이 회의록의 결정에 의견을 남기고 읽을 수 있도록 회의록마다 댓글을 등록 · 조회 · 삭제하는 기능과 회의록 상세 화면(detail.html) 댓글 영역의 동작을 정의한다.

## Requirements

### Requirement: 댓글 목록
<!-- 근거: D-11 · detail.html / 정의서 7-1 -->
시스템은 `GET /api/meetings/{id}/comments` 로 `id · user_id · user_name · content · created_at · can_delete` 를 created_at 오름차순으로 MUST 돌려준다. can_delete 는 쓴 사람이거나 owner 일 때 true 다. 없으면 200 과 빈 배열이다.

#### Scenario: 댓글 없음
- **WHEN** 댓글이 없는 회의록을 열면
- **THEN** 머리는 건수 없이 「댓글」이고 「아직 댓글이 없음 - 결정에 의견이 있으면 여기에」가 보인다

#### Scenario: 댓글 순서
- **WHEN** 댓글이 2건 있는 회의록을 열면
- **THEN** 먼저 쓴 댓글이 위에 오고 머리는 「댓글 2건」이다

### Requirement: 댓글 등록
<!-- 근거: D-09 · D-10 · detail.html / 정의서 8-1 -->
시스템은 `POST /api/meetings/{id}/comments` 로 내용을 받아 201 을 MUST 돌려주고 활동 comment_add 를 남긴다. 내용은 1~500자이며 벗어나면 400 `VALIDATION_ERROR` 다. 팀원 누구나 쓸 수 있다. 화면은 글자 수(`16 / 500`)를 보여 주고 등록 뒤 입력칸을 비운다.

#### Scenario: 댓글 등록
- **WHEN** 「16 / 500」인 의견을 적고 「등록」을 누르면
- **THEN** 201 뒤 띠 알림 「댓글 등록 - 입력칸 비움」이 뜨고 새 댓글이 「방금」으로 맨 아래에 붙는다

#### Scenario: 500자 초과
- **WHEN** 501자 댓글을 보내면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 댓글 삭제
<!-- 근거: D-12 · detail.html / 정의서 7-4 -->
시스템은 `DELETE /api/comments/{id}` 로 댓글을 지우고 204 를 MUST 돌려준다. 쓴 사람과 owner 만 할 수 있고, 그 밖은 403 `FORBIDDEN` 이다. 화면은 지우기 전에 확인받는다.

#### Scenario: owner 의 삭제
- **WHEN** owner 가 박과장의 댓글에서 「삭제」를 누르면
- **THEN** 팝업 「댓글을 삭제할까요?」 / 「박과장의 댓글. 쓴 사람과 owner 만 삭제 가능」이 뜨고, 확인하면 204 를 받는다

#### Scenario: 남의 댓글 삭제 시도
- **WHEN** 쓴 사람도 owner 도 아닌 member 가 삭제 API 를 부르면
- **THEN** 403 `FORBIDDEN` 을 받고, 화면에서는 그 댓글의 「삭제」가 보이지 않는다
