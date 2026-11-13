# Spec Delta

## Purpose

녹취 파일을 받아써 본문을 만들고, 저장할 때 요약 · 결정사항 · 할 일로 나눠 팀이 함께 보는 회의록으로 남기며, 목록 · 검색 · 상세 · 수정 · 삭제를 제공하는 회의록 기능과 meetings.html · detail.html 화면의 동작을 정의한다.

## ADDED Requirements

### Requirement: 회의록 목록
<!-- 근거: C-01 · meetings.html / 정의서 7-1 -->
시스템은 `GET /api/teams/{id}/meetings` 로 `id · title · met_at · attendees · summary · created_at · todo_done_count · todo_total_count · decision_count` 를 met_at 내림차순으로 MUST 돌려준다. 목록에는 body 와 todos 를 싣지 않는다. 다른 팀 목록은 403 `FORBIDDEN` 이다.

#### Scenario: 목록 조회
- **WHEN** 회의록 3건인 팀의 멤버가 목록을 조회하면
- **THEN** 3건이 최신 회의 순으로 오고, 각 항목에 body 필드가 없다

#### Scenario: 카드 띠 색
- **WHEN** 화면이 목록을 그리면
- **THEN** 카드 좌측 띠는 목록 순서대로 blue · green · orange · purple · red 를 돌려 쓴다

### Requirement: 빈 목록
<!-- 근거: C-02 · meetings.html -->
회의록이 없으면 시스템은 200 과 빈 배열을 MUST 돌려주고, 화면은 「아직 회의록이 없음」 / 「새 회의록 버튼으로 첫 회의를 올려 보기」를 보여 준다.

#### Scenario: 팀 합류 직후
- **WHEN** 회의록이 없는 팀의 목록을 열면
- **THEN** 빈 상태 안내가 보이고 「새 회의록」 버튼이 다음 행동이다

### Requirement: 검색과 기간
<!-- 근거: C-03 · C-04 · meetings.html / 정의서 7-2 -->
시스템은 `?q=` 로 제목과 참석자만 MUST 검색하고 본문은 검색하지 않는다. `?from=&to=`(ISO 날짜)로 met_at 기간을 거른다. 결과가 없으면 404 가 아니라 200 과 빈 배열이다.

#### Scenario: 제목 검색
- **WHEN** `q=배포` 로 검색하면
- **THEN** 제목에 「배포」가 든 「배포 환경 점검」 1건만 온다

#### Scenario: 본문만 일치
- **WHEN** 본문에만 있는 낱말로 검색하면
- **THEN** 200 과 빈 배열을 받고 화면은 「검색 결과 없음」 / 「검색어를 지우면 전체 목록으로 돌아감」을 보여 준다

### Requirement: 녹취 업로드와 받아쓰기
<!-- 근거: C-05 · C-06 · C-07 · meetings.html / 정의서 7-3 · 9 -->
시스템은 `POST /api/upload` 로 녹취 파일을 받아 Gemini 로 받아쓰고 200 `{body}` 를 MUST 돌려준다. 이 단계에서는 회의록을 저장하지 않는다. 화면은 끌어 놓기와 눌러서 선택을 모두 받고, 진행률을 보여 주며, 끝나면 본문 칸을 채운다.

#### Scenario: wav 받아쓰기
- **WHEN** `회의_녹음.wav`(4.2MB)를 새 회의록 팝업에 끌어 놓으면
- **THEN** 「업로드 완료, 받아쓰는 중」과 진행 막대가 보이고, 200 `{body}` 뒤 본문 칸이 채워지며 「받아쓰기 완료」가 뜬다. 회의록 수는 그대로다

### Requirement: 업로드 형식과 크기 제한
<!-- 근거: C-08 · meetings.html / 정의서 8-1 · add-mvp-core (지시) -->
시스템은 mp3 · wav 만 받으며 확장자가 아니라 파일 내용으로 판정한다(SHALL). 그 밖은 415 `UNSUPPORTED_MEDIA_TYPE` 이다. 파일 크기 상한은 로컬 20MB, 배포 4.5MB 이며 넘으면 400 `VALIDATION_ERROR` 를 MUST 돌려준다.

#### Scenario: mp4 거부
- **WHEN** `회의_녹화.mp4` 를 올리면
- **THEN** 415 `UNSUPPORTED_MEDIA_TYPE` 를 받고 「mp3 또는 wav 만 올릴 수 있음 - 415 UNSUPPORTED_MEDIA_TYPE」가 뜬다

#### Scenario: 확장자만 바꾼 파일
- **WHEN** 내용이 mp4 인 파일의 이름을 `a.wav` 로 바꿔 올리면
- **THEN** 415 `UNSUPPORTED_MEDIA_TYPE` 를 받는다

#### Scenario: 배포 환경 상한
- **WHEN** 배포 환경에 4.5MB 를 넘는 wav 를 올리면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

### Requirement: 받아쓰기 실패
<!-- 근거: C-09 · meetings.html / 정의서 7-2 · 9 -->
Gemini 응답 오류 · 키 없음이면 시스템은 502 `VALIDATION_ERROR` 를 MUST 돌려주고 msg 로 원인을 구분한다. 공급자 5xx 는 1회 재시도한 뒤 502 다. 화면은 본문 칸에 메모를 직접 붙여넣으면 저장할 수 있게 한다.

#### Scenario: 키 없음
- **WHEN** `GEMINI_API_KEY` 가 비어 있는 채로 업로드하면
- **THEN** 502 `VALIDATION_ERROR` 를 받고 「받아쓰기 실패 - 502. 본문 칸에 메모를 직접 붙여넣기」가 뜬다

#### Scenario: 본문을 붙여넣어 저장
- **WHEN** 받아쓰기 실패 뒤 본문 칸에 메모를 붙여넣으면
- **THEN** 「정리하기」가 켜지고 저장할 수 있다

### Requirement: 회의록 저장과 세 항목 구분
<!-- 근거: C-10 · C-11 · meetings.html / 정의서 7-3 -->
시스템은 `POST /api/teams/{id}/meetings` 로 제목 · 회의 시각 · 참석자 · 본문을 받아, 본문을 Gemini 로 요약(3~5줄) · 결정사항(합의 끝난 것만) · 할 일(담당자나 기한이 드러난 것만)로 나눠 저장하고 201 을 MUST 돌려준다. 제목 · 회의 시각 · 본문은 필수다. 본문은 지우지 않는다.

#### Scenario: 정리하기
- **WHEN** 필수 칸을 채우고 「정리하기」를 누르면
- **THEN** 버튼이 「정리 중...」으로 잠기고, 201 뒤 팝업이 닫히고 입력칸이 비며 새 카드가 목록 맨 위에 생기고 활동 meeting_add 가 남는다

#### Scenario: 필수 칸 누락
- **WHEN** 본문 없이 저장을 요청하면
- **THEN** 400 `VALIDATION_ERROR` 를 받는다

#### Scenario: 구분 실패
- **WHEN** Gemini 의 세 항목 구분 응답을 읽지 못하면
- **THEN** 저장하지 않고 502 `VALIDATION_ERROR` 를 받으며, 본문은 화면 칸에 남아 다시 저장할 수 있다

### Requirement: 할 일 담당자 대조
<!-- 근거: 정의서 7-3 · 6 -->
시스템은 뽑힌 할 일의 담당자 이름을 팀 멤버 이름과 공백 · 존칭(님)을 무시하고 MUST 대조해, 맞는 멤버가 없으면 담당자를 미정(null)으로 둔다. 할 일은 `내용 | 담당자 | 기한` 한 줄씩이며, 기한은 받아쓴 글자 그대로 due_text 에 둔다. 담당자가 붙은 할 일마다 활동 todo_assign 을 남긴다.

#### Scenario: 존칭 붙은 담당자
- **WHEN** 할 일 줄이 `목록 정리 | 이주임님 | 다음 주 금요일` 이고 멤버 `이주임` 이 있으면
- **THEN** 담당자는 이주임, due_text 는 「다음 주 금요일」이고 todo_assign 활동이 생긴다

#### Scenario: 멤버가 아닌 담당자
- **WHEN** 할 일 줄의 담당자가 팀에 없는 이름이면
- **THEN** 담당자는 미정으로 저장되고 이름을 지어내지 않는다

### Requirement: 회의록 상세
<!-- 근거: D-01 · D-05 · D-06 · D-07 · detail.html / 정의서 7-1 · 7-2 -->
시스템은 `GET /api/meetings/{id}` 로 목록 필드에 body · todos · can_edit 를 더해 MUST 돌려준다. can_edit 는 보는 사람이 작성자이거나 owner 일 때 true 다. 화면은 요약 · 결정사항 · 할 일 3단을 먼저 보여 주고 본문은 접어 둔다. 결정사항은 줄 단위로 번호를 붙인다.

#### Scenario: 상세 보기
- **WHEN** 회의록 카드를 누르면
- **THEN** detail.html 에서 요약 · 결정사항 · 할 일 3단이 보이고 본문은 「본문 펼치기」로 접혀 있다

#### Scenario: 결정사항 없음
- **WHEN** decisions 가 빈 회의록을 열면
- **THEN** 결정사항 칸에 「결정사항 없음」 / 「억지로 채우지 않음」이 보인다

#### Scenario: 할 일 없음
- **WHEN** 할 일이 0건인 회의록을 열면
- **THEN** 할 일 칸에 「할 일 없음」 / 「담당자와 기한이 드러난 항목 0건」이 보인다

### Requirement: 회의록 수정
<!-- 근거: D-02 · detail.html / 정의서 7-3 · 7-4 -->
시스템은 `PUT /api/meetings/{id}` 로 제목 · 회의 시각 · 참석자 · 본문을 고친다(SHALL). 작성자와 owner 만 할 수 있고 그 밖은 403 `FORBIDDEN` 이다. 본문을 고쳐도 받아쓰기와 세 항목 구분을 다시 돌리지 않는다(MUST).

#### Scenario: 본문 수정
- **WHEN** 작성자가 본문을 고쳐 저장하면
- **THEN** 200 을 받고 요약 · 결정사항 · 할 일은 그대로다

#### Scenario: 권한 없는 수정
- **WHEN** 작성자도 owner 도 아닌 member 가 수정을 요청하면
- **THEN** 403 `FORBIDDEN` 을 받고, 화면에서는 「수정」 · 「삭제」가 비활성이다

### Requirement: 회의록 삭제
<!-- 근거: D-08 · detail.html / 정의서 7-4 -->
시스템은 `DELETE /api/meetings/{id}` 로 회의록과 딸린 할 일 · 댓글을 함께 지우고 204 를 MUST 돌려준다. 작성자와 owner 만 할 수 있고 그 밖은 403 `FORBIDDEN` 이다. 화면은 삭제 전에 딸린 할 일 수를 알리고 확인받는다.

#### Scenario: 삭제 확인
- **WHEN** 「삭제」를 누르면
- **THEN** 팝업 「회의록을 삭제할까요?」 / 「「2차 스프린트 계획 회의」와 딸린 할 일 3건도 함께 삭제됨. 되돌릴 수 없음」이 뜨고, 확인하면 204 뒤 목록으로 간다

### Requirement: 없는 회의록
<!-- 근거: D-13 · detail.html -->
없거나 다른 팀의 회의록을 조회하면 시스템은 404 `MEETING_NOT_FOUND` 를 MUST 돌려주고, 화면은 팝업 「회의록을 찾을 수 없음」과 「목록으로」 버튼을 보여 준다.

#### Scenario: 지운 회의록 주소
- **WHEN** `detail.html?id=99` 를 열면
- **THEN** 404 `MEETING_NOT_FOUND` 를 받고 「목록으로」를 누르면 meetings.html 로 간다
