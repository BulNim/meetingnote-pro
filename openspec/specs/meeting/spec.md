# meeting Specification

## Purpose

녹취 파일이나 붙여넣은 메모를 받아쓴 본문으로 만들고, 저장할 때 요약 · 결정사항 · 할 일 세 항목으로 나눠 팀의 회의록으로 보관하는 동작을 정한다. 목록 · 검색 · 상세 · 수정 · 삭제를 포함한다.

## Requirements

### Requirement: 녹취 받아쓰기
<!-- 근거: C-06 · C-07 / meetings.html -->
`POST /api/upload` 는 mp3 또는 wav 녹취 파일을 받아 받아쓴 본문 텍스트만 200 으로 돌려줘야 한다(SHALL). 이 단계는 회의록을 저장하지 않는다. 받아쓰기는 Gemini 로 하며 녹음 길이에는 제한을 두지 않는다. 화면은 올리는 동안 진행 표시를 보이고, 끝나면 본문 칸을 채운다.

#### Scenario: 받아쓰기 성공
- **WHEN** 4.4MB 이하의 mp3 또는 wav 를 올린다
- **THEN** 200 과 받아쓴 본문을 받고 회의록은 아직 저장되지 않는다

#### Scenario: 올리는 중
- **WHEN** 파일이 올라가는 중이다
- **THEN** 화면에 파일 이름과 진행 표시가 보인다

### Requirement: 업로드 파일 검사
<!-- 근거: C-08 · C-09 / meetings.html -->
업로드는 형식과 용량을 검사해야 한다(SHALL). 형식은 확장자가 아니라 파일 내용으로 판정하며 mp3 와 wav 가 아니면 415 `UNSUPPORTED_MEDIA_TYPE` 이다. 용량이 4.4MB(4,500,000 바이트)를 넘으면 413 `PAYLOAD_TOO_LARGE` 이며 분할 업로드는 받지 않는다. 길이 초과 오류는 없다.

#### Scenario: 지원하지 않는 형식
- **WHEN** 확장자만 mp3 로 바꾼 mp4 파일을 올린다
- **THEN** 415 `UNSUPPORTED_MEDIA_TYPE` 를 받는다

#### Scenario: 용량 초과
- **WHEN** 4.4MB 파일을 올린다
- **THEN** 413 `PAYLOAD_TOO_LARGE` 를 받는다

#### Scenario: 길이는 보지 않음
- **WHEN** 4.4MB 이하이지만 아주 긴 녹음을 올린다
- **THEN** 길이 때문에 거절되지 않는다

### Requirement: 받아쓰기 실패
<!-- 근거: C-06 / meetings.html -->
Gemini 호출이 실패하면 502 `UPSTREAM_ERROR` 를 돌려줘야 한다(SHALL). 화면은 기존 빨간 알림 상자로 실패를 알리고 본문 칸을 비워 둔 채 메모 붙여넣기로 이어 갈 수 있게 한다.

#### Scenario: Gemini 실패
- **WHEN** 받아쓰기 호출이 Gemini 오류로 실패한다
- **THEN** 502 `UPSTREAM_ERROR` 를 받고, 화면에 빨간 알림이 보이며, 메모를 직접 붙여넣어 저장할 수 있다

### Requirement: 회의록 저장과 세 항목 구분
<!-- 근거: C-05 · C-10 · C-11 / meetings.html -->
`POST /api/teams/{id}/meetings` 는 제목 · 회의 시각 · 참석자 · 본문을 받아 저장하고, 본문을 요약 · 결정사항 · 할 일로 나눠 함께 저장한 뒤 201 을 돌려줘야 한다(SHALL). 제목 · 회의 시각 · 본문은 필수이고 없으면 400 `VALIDATION_ERROR` 다. 본문은 지우지 않고 그대로 남긴다. 저장하면 `meeting_add` 활동을 남긴다.

#### Scenario: 정상 저장
- **WHEN** 제목 · 회의 시각 · 참석자 · 본문을 보낸다
- **THEN** 201 을 받고 요약 · 결정사항이 저장되고 할 일 항목이 만들어지며 `meeting_add` 활동이 남는다

#### Scenario: 필수 항목 누락
- **WHEN** 제목 없이 저장을 요청한다
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 세 항목의 구분 규칙
<!-- 근거: 프로그램정의 7-3 / detail.html -->
요약은 회의 전체를 3~5줄로 쓰되 없는 사실을 보태지 않아야 한다(SHALL). 결정사항은 합의가 끝난 것만 담고 논의만 한 것은 넣지 않으며 줄바꿈으로 구분해 저장한다. 할 일은 담당자나 기한이 드러난 문장만 뽑고, 담당자가 팀 멤버 이름과 맞지 않으면 담당자 없음(미정)으로, 기한이 없으면 `미정` 으로 저장한다. 상태는 `OPEN` 으로 시작한다.

#### Scenario: 담당자가 드러난 할 일
- **WHEN** 본문에 「목록과 검색은 제가 다음 주 금요일까지 하겠습니다」 가 김대리 발언으로 있다
- **THEN** 할 일 「목록과 검색」 이 담당자 김대리 · 기한 「다음 주 금요일」 로 저장된다

#### Scenario: 담당자를 지어내지 않음
- **WHEN** 본문에서 담당자가 드러나지 않는 할 일이다
- **THEN** 담당자 없음으로 저장되고 임의의 사람이 배정되지 않는다

#### Scenario: 결정사항이 없는 회의
- **WHEN** 논의만 하고 정해진 것이 없다
- **THEN** 결정사항은 빈 값이고 억지로 채워지지 않는다

### Requirement: 세 항목 구분 실패 시 저장 유지
<!-- 근거: C-10 / meetings.html -->
정리 단계에서 Gemini 호출이 실패해도 회의록 자체는 저장돼야 한다(SHALL). 이때 요약과 결정사항은 빈 값이고 할 일은 만들어지지 않으며 응답은 201 이다.

#### Scenario: 정리 실패
- **WHEN** 저장 중 세 항목 구분 호출이 실패한다
- **THEN** 201 을 받고 본문은 저장되며 세 칸은 비어 있다

### Requirement: 같은 회의록의 중복 저장 방지
<!-- 근거: C-10 · C-11 / meetings.html -->
저장 중에는 정리하기 버튼을 잠가야 하고(SHALL), 저장이 끝나면 입력칸을 비우고 목록 맨 위에 새 회의록을 보여 같은 회의록이 두 번 저장되지 않게 한다. 버튼 문구는 저장 중 「정리 중...」 이다.

#### Scenario: 저장 중 버튼
- **WHEN** 정리하기를 눌러 응답을 기다린다
- **THEN** 버튼이 비활성이고 「정리 중...」 으로 보인다

#### Scenario: 저장 후 입력 초기화
- **WHEN** 저장이 201 로 끝난다
- **THEN** 입력칸이 비워지고 목록 맨 위에 새 회의록이 나온다

### Requirement: 회의록 목록
<!-- 근거: C-01 · C-02 / meetings.html -->
`GET /api/teams/{id}/meetings` 는 `met_at` 내림차순으로 `id` · `title` · `met_at` · `attendees` · `summary` · `created_at` 에 `todo_done_count` · `todo_total_count` · `decision_count` 를 더해 돌려줘야 한다(SHALL). 본문(`body`)은 싣지 않는다. 결정사항 수는 빈 줄을 뺀 줄 수다. 회의록이 없으면 200 과 빈 배열이고 화면은 「아직 회의록이 없음」 을 보인다. 카드 띠 색은 목록 순서대로 blue · green · orange · purple · red 를 돌려 쓴다.

#### Scenario: 목록에 본문이 없음
- **WHEN** 회의록 목록을 부른다
- **THEN** 각 항목에 `body` 가 없고 개수 세 가지가 있다

#### Scenario: 빈 목록
- **WHEN** 회의록이 없는 팀이 목록을 부른다
- **THEN** 200 과 빈 배열을 받는다

#### Scenario: 카드 띠 색
- **WHEN** 회의록이 6건이다
- **THEN** 여섯 번째 카드의 띠 색은 첫 번째와 같은 blue 다

### Requirement: 제목과 참석자 검색, 기간 거름
<!-- 근거: C-03 · C-04 / meetings.html -->
목록은 `?q=` 로 제목과 참석자에서만 찾고 본문은 검색 대상이 아니어야 한다(SHALL). `?from=` · `?to=` 는 ISO 날짜이며 양 끝을 포함하고 UTC 기준 날짜로 비교한다. 결과가 없으면 404 가 아니라 200 과 빈 배열이다.

#### Scenario: 본문은 검색되지 않음
- **WHEN** 본문에만 있는 단어로 검색한다
- **THEN** 200 과 빈 배열을 받는다

#### Scenario: 참석자 검색
- **WHEN** `?q=최선임` 으로 검색한다
- **THEN** 참석자에 최선임이 있는 회의록이 나온다

#### Scenario: 검색 결과 없음
- **WHEN** 맞는 회의록이 없다
- **THEN** 200 과 빈 배열이고 화면에 「검색 결과 없음」 이 보인다

### Requirement: 회의록 상세
<!-- 근거: D-01 · D-05 · D-06 · D-07 · D-13 / detail.html -->
`GET /api/meetings/{id}` 는 본문을 포함한 한 건을 돌려줘야 한다(SHALL). 화면은 요약 · 결정사항 · 할 일 세 칸을 먼저 보이고 받아쓴 본문은 접어 둔다. 결정사항이나 할 일이 없으면 해당 칸이 빈 상태로 보이며 억지로 채우지 않는다. 없는 회의록은 404 `MEETING_NOT_FOUND` 이고 화면은 목록으로 돌려보낸다.

#### Scenario: 본문은 접힘
- **WHEN** 상세 화면을 연다
- **THEN** 세 칸이 먼저 보이고 본문은 「펼치기」 로 접혀 있다

#### Scenario: 없는 회의록
- **WHEN** 없는 id 로 조회한다
- **THEN** 404 `MEETING_NOT_FOUND` 를 받고 목록으로 돌려보내진다

### Requirement: 회의록 수정
<!-- 근거: D-02 / detail.html -->
`PUT /api/meetings/{id}` 는 제목 · 회의 시각 · 참석자 · 본문을 고칠 수 있어야 하며 올린 사람과 팀의 owner 만 할 수 있다(SHALL). 그 밖의 member 는 403 `FORBIDDEN` 이다. 본문을 고쳐도 받아쓰기와 세 항목 구분을 다시 돌리지 않고 이미 뽑힌 세 항목은 그대로 둔다.

#### Scenario: 올린 사람의 수정
- **WHEN** 올린 사람이 제목을 고친다
- **THEN** 200 을 받고 요약 · 결정사항 · 할 일은 그대로다

#### Scenario: 다른 member 의 수정
- **WHEN** 올리지 않은 member 가 수정을 요청한다
- **THEN** 403 `FORBIDDEN` 을 받는다

### Requirement: 회의록 삭제
<!-- 근거: D-08 / detail.html -->
`DELETE /api/meetings/{id}` 는 올린 사람과 팀의 owner 만 할 수 있고 204 를 돌려줘야 한다(SHALL). 딸린 할 일과 댓글도 함께 지운다. 화면은 삭제 전에 「딸린 할 일도 함께 사라집니다」 확인을 보인다.

#### Scenario: 딸린 항목도 삭제
- **WHEN** 할 일 3건과 댓글 2건이 있는 회의록을 owner 가 삭제한다
- **THEN** 204 를 받고 할 일과 댓글도 조회되지 않는다

#### Scenario: 삭제 확인
- **WHEN** 삭제 버튼을 누른다
- **THEN** 확인 상자가 먼저 보이고 취소하면 아무것도 지워지지 않는다
