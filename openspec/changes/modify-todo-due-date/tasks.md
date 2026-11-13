# Tasks

## 1. 백엔드 구현

- [ ] 1.1 `backend/duedate.py` 에 `resolve(text, base)` 와 `kst_date(dt)` · `base_date(todo, meeting)` 를 design 1 · 2 의 표대로 만들고, `python -c` 로 「다음 주 금요일」(기준 2026-11-12) → 2026-11-20 이 나오는지 확인
- [ ] 1.2 `backend/models.py` 의 `Todo` 에 `due_date`(Date, nullable)를 더하고, 새 임시 DB 에서 `create_all` 뒤 칼럼이 생기는지 확인
- [ ] 1.3 `backend/db.py` 에 `upgrade()` (칼럼 없으면 `ALTER TABLE todos ADD COLUMN due_date DATE`, 빈 due_date 채우기)를 넣고 `create_all()` 뒤에 부른다. 현재 로컬 `meetingnote.db` 사본으로 서버를 띄워 칼럼이 추가되고 기존 할 일 9건의 due_date 가 채워지는지 확인
- [ ] 1.4 `backend/serial.py`: `todo_out` 에 `due_date`, `sort_todos` 를 status 다음 due_date(null 은 뒤) 순으로. `/docs` 에서 팀 할 일 응답에 due_date 가 보이는지 확인
- [ ] 1.5 `backend/routers/meetings.py`: 회의록 저장 때 met_at 기준으로 할 일 due_date 환산, 수정 때 met_at 이 바뀌면 딸린 할 일 다시 환산. `/docs` 로 저장 · 회의 시각 수정 뒤 due_date 를 확인
- [ ] 1.6 `backend/routers/todos.py`: 직접 등록은 등록일 기준 환산, PUT 에 due_text 가 오면 다시 환산. `/docs` 로 「다음 주까지」 등록 뒤 due_date 확인

## 2. 백엔드 테스트

- [ ] 2.1 `tests/test_duedate.py`: design 1 의 표 전 행(오늘 · 내일 · 모레 · 어제 · N일 뒤 · N주 뒤 · 다음 주 · 지난 주 · 요일 3종 · 월말 2종 · N일 2종 · M월N일(해 넘김 포함) · M/D · YYYY-MM-DD · 「까지 · 안에」 꼬리 · 공백 변형)과 null 이 되는 경우(이번 주 안 · 미정 · 빈 값 · 2월 30일 · 다음 달 31일이 없는 달)를 시험하고 통과 확인
- [ ] 2.2 `tests/test_todo.py` 보강: 응답에 due_date, 직접 등록 기준일(등록일), due_text 수정 뒤 다시 환산, 빈 due_text 면 due_date null, due_date 정렬(null 은 뒤)이 통과하는지 확인
- [ ] 2.3 `tests/test_meeting.py` 보강: 저장 때 회의 날짜 기준 환산(UTC 23:30 → 한국 다음 날 기준), met_at 수정 때 다시 환산, 제목만 수정하면 그대로가 통과하는지 확인
- [ ] 2.4 `tests/test_upgrade.py`: due_date 칼럼 없이 만든 SQLite 에 할 일을 넣고 `create_all()` 을 부르면 칼럼이 생기고 채워지며, 두 번 불러도 값이 그대로인지 확인
- [ ] 2.5 `pytest -q` 전체를 돌려 기존 40개와 새 시험이 모두 통과하는지 확인하고 통과 · 실패 · skip 수를 보고

## 3. 프런트엔드

- [ ] 3.1 `frontend/api.js` 에 `dueLabel(todo)` · `isOverdue(todo)` 를 더하고, 브라우저 콘솔에서 due_date 2026-11-20 → 「11-20 (금)」, 어제 날짜 · 미완료 → true 가 나오는지 확인
- [ ] 3.2 `frontend/todos.html`: 기한 배지를 날짜 + 원래 글자로, 기한 지남 붉은 띠를 `isOverdue` 로 바꾸고 낱말 판정을 지운다. 브라우저에서 날짜 지난 대기 카드만 붉은 띠인지, 날짜 없는 카드는 글자만 보이는지 확인
- [ ] 3.3 `frontend/detail.html` · `profile.html`: 할 일 기한 표시를 `dueLabel` 로 바꾸고, 기한 글자를 고치면 응답의 due_date 로 다시 그려지는지 브라우저에서 확인
- [ ] 3.4 세 화면에 새 색 값 · 인라인 style · `!important` 가 생기지 않았는지 grep 으로 확인

## 4. 통합 확인

- [ ] 4.1 시연 DB 로 서버를 띄워 기존 할 일 9건의 기한이 날짜로 보이고(「이번 주」 같은 글자는 글자만), 칸반이 기한 순으로 정렬되는지 브라우저로 확인
- [ ] 4.2 360px · 다크 모드에서 기한 배지가 줄바꿈 · 넘침 없이 보이는지 확인

## 5. 사람 수락

- [ ] 5.1 (사람) 칸반 · 상세에서 기한이 회의 날짜 기준 날짜로 보이고, 지난 기한만 붉은 띠이며, 원래 글자도 함께 보이는지 눈으로 확인

## Workflow follow-up

- 사람 수락이 끝나면 `openspec-archive-change` 로 modify-todo-due-date 를 아카이브해 todo · meeting main spec 에 합친다
