# meeting Specification

## Purpose
녹취 파일을 받아쓰고 요약 · 결정사항 · 할 일 세 항목으로 나눠 회의록으로 저장하며, 팀이 목록 · 검색 · 상세 · 수정 · 삭제로 지난 회의의 맥락을 찾게 하는 기능이다.

## Requirements

### Requirement: 녹취 업로드 제한
<!-- C-08, C-09 meetings.html -->
시스템은 `POST /api/upload` 로 mp3 와 wav 파일만 받아야 하며(SHALL), 25MB 를 넘으면 413 `PAYLOAD_TOO_LARGE`, 다른 형식이면 415 `UNSUPPORTED_MEDIA_TYPE` 를 돌려줘야 한다. 거절된 파일은 저장하지 않아야 한다.

#### Scenario: 용량 초과
- **WHEN** 25MB 를 넘는 wav 를 올린다
- **THEN** 413 `PAYLOAD_TOO_LARGE` 가 돌아온다

#### Scenario: 허용되지 않는 형식
- **WHEN** m4a 파일을 올린다
- **THEN** 415 `UNSUPPORTED_MEDIA_TYPE` 가 돌아온다

### Requirement: 받아쓰기와 3항목 구분
<!-- C-06, C-07, C-10 meetings.html -->
시스템은 올라온 녹취를 외부 음성 인식으로 받아쓰고, 받아쓴 전문을 같은 모델에 다시 넣어 요약 · 결정사항 · 할 일 세 항목으로 나눠 200 으로 돌려줘야 한다(SHALL). 받아쓰기는 60초 이내에 끝나야 하고, 처리 중에는 화면이 진행 상태를 보여줘야 한다.

#### Scenario: 받아쓰기 완료
- **WHEN** 허용된 녹취를 올린다
- **THEN** 200 과 함께 전문, 요약, 결정사항 목록, 할 일 목록이 돌아온다

### Requirement: 회의록 저장
<!-- C-05, C-11 meetings.html -->
시스템은 `POST /api/teams/{id}/meetings` 로 제목 · 회의 시각 · 본문을 필수로 받아 회의록을 저장하고 201 을 돌려줘야 한다(SHALL). 함께 받은 할 일은 대기 상태로 저장하고 활동 기록 `meeting_add` 를 남겨야 한다. 필수 값이 비면 400 `VALIDATION_ERROR` 이다.

#### Scenario: 저장 성공
- **WHEN** 제목 · 회의 시각 · 본문과 할 일 2건을 보낸다
- **THEN** 201 이 돌아오고 할 일 2건이 대기 상태로 생기며 `meeting_add` 가 남는다

#### Scenario: 필수 값 누락
- **WHEN** 제목 없이 저장을 요청한다
- **THEN** 400 `VALIDATION_ERROR` 가 돌아온다

### Requirement: 회의록 목록
<!-- C-01, C-02 meetings.html -->
시스템은 `GET /api/teams/{id}/meetings` 로 `id · title · met_at · attendees · summary · created_at · todo_done_count · todo_total_count · decision_count` 를 `met_at` 내림차순으로 돌려줘야 한다(SHALL). 본문(`body`)은 목록에 싣지 않으며, 회의록이 없으면 200 과 빈 배열이다.

#### Scenario: 목록 조회
- **WHEN** 회의록 3건이 있는 팀을 조회한다
- **THEN** 최근 회의 순으로 3건이 돌아오고 어느 항목에도 `body` 가 없다

#### Scenario: 빈 목록
- **WHEN** 회의록이 없는 팀을 조회한다
- **THEN** 200 과 빈 배열이 돌아온다

### Requirement: 검색과 기간
<!-- C-03, C-04 meetings.html -->
시스템은 `?q=` 로 제목과 참석자만 검색해야 하고(SHALL) 본문은 검색 대상이 아니다. `?from=&to=` 는 ISO 날짜로 회의 기간을 거른다. 결과가 없으면 404 가 아니라 200 과 빈 배열이다.

#### Scenario: 제목 검색
- **WHEN** `?q=스프린트` 로 조회한다
- **THEN** 제목이나 참석자에 "스프린트" 가 든 회의록만 돌아온다

#### Scenario: 본문에만 있는 단어
- **WHEN** 본문에만 나오는 단어로 검색한다
- **THEN** 200 과 빈 배열이 돌아온다

#### Scenario: 기간 필터
- **WHEN** `?from=2026-09-01&to=2026-09-30` 으로 조회한다
- **THEN** 그 기간에 열린 회의록만 돌아온다

### Requirement: 회의록 상세
<!-- D-01, D-05, D-06, D-07 detail.html -->
시스템은 `GET /api/meetings/{id}` 로 본문 · 요약 · 결정사항 · 할 일을 돌려줘야 한다(SHALL). 결정사항은 줄바꿈으로 구분한 한 칸의 텍스트로 저장하고 `decision_count` 는 빈 줄을 뺀 줄 수이다. 없는 회의록은 404 `MEETING_NOT_FOUND` 이다.

#### Scenario: 상세 조회
- **WHEN** 팀 멤버가 회의록 상세를 조회한다
- **THEN** 본문과 3항목이 돌아온다

#### Scenario: 없는 회의록
- **WHEN** 존재하지 않는 id 를 조회한다
- **THEN** 404 `MEETING_NOT_FOUND` 가 돌아온다

### Requirement: 회의록 수정과 삭제
<!-- D-02, D-08 detail.html -->
시스템은 `PUT /api/meetings/{id}` 와 `DELETE /api/meetings/{id}` 를 쓴 사람과 owner 에게만 허용해야 한다(SHALL). 삭제는 204 이고 딸린 할 일과 댓글도 함께 지운다. 그 밖의 사용자는 403 `FORBIDDEN` 이다.

#### Scenario: 작성자의 삭제
- **WHEN** 작성자가 회의록을 삭제한다
- **THEN** 204 가 돌아오고 그 회의록의 할 일과 댓글도 조회되지 않는다

#### Scenario: 남의 회의록 삭제
- **WHEN** 작성자도 owner 도 아닌 member 가 삭제를 요청한다
- **THEN** 403 `FORBIDDEN` 이 돌아오고 회의록은 남는다

### Requirement: 시각 저장과 표시
<!-- 정의서 9절 시각 기준 -->
시스템은 시각을 UTC ISO 8601 로 저장하고 돌려줘야 하며(SHALL), 화면은 현지 시간으로 표시해야 한다. 목록 응답은 100ms 이내, 화면의 목록 렌더링은 50ms 이내이다.

#### Scenario: 시각 형식
- **WHEN** 회의록을 조회한다
- **THEN** `met_at` 과 `created_at` 이 `2026-09-24T05:00:00Z` 형식으로 돌아온다
