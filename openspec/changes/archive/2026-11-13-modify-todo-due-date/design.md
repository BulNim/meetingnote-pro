# Design

## Context

- 지금 할 일 기한은 `todos.due_text`(글자)뿐이다. Gemini 가 세 항목을 구분할 때 받아쓴 기한 글자를 그대로 넘기고(`backend/gemini.py` 의 `TodoItem.due`), 저장은 `backend/routers/meetings.py` 의 `create_meeting` 과 `backend/routers/todos.py` 의 `create_todo` · `edit_todo` 가 한다.
- 정렬은 `backend/serial.py` 의 `sort_todos`(status 다음 due_text 글자 순)이고, 기한 지남은 화면(`frontend/todos.html`)이 글자 「어제 · 지난 주 · 지난 달」로만 판정한다.
- DB 는 시작 때 `Base.metadata.create_all` 만 돈다. 이미 있는 표에 칼럼을 더하지 않으므로, add-mvp-core 로 만든 로컬 SQLite 와 배포 Neon 에는 `due_date` 칼럼이 없다.
- 시각은 UTC 로 저장한다(`met_at` · `created_at`). 사용자는 한국어 사용자이고(정의서 8-1 Assumptions) 한국은 서머타임이 없다.

## Goals / Non-Goals

**Goals:**
- 같은 기한 글자 · 같은 기준일이면 언제나 같은 날짜 (Gemini 에 맡기지 않음)
- 기존 API 필드는 그대로 두고 `due_date` 만 더해 화면 · 시험이 깨지지 않게
- 이미 쌓인 데이터도 서버 시작 한 번으로 채워짐

**Non-Goals:**
- 자연어 날짜 인식 라이브러리 도입 - 표현 범위를 표로 고정하고 그 밖은 null
- 서버가 「기한 지남」을 판정해 내려 주기 - 판정은 지금처럼 화면이 한다 (보는 사람의 오늘 기준)

## Decisions

### 1. 환산은 서버의 순수 함수 하나 - `backend/duedate.py`

```
resolve(text: str, base: date) -> date | None
```

- 입력 정리: 앞뒤 공백 제거 → 끝의 「까지 · 안에 · 안 · 내 · 중 · 쯤」을 반복해서 떼기 → 안쪽 공백 제거 (「다음 주 금요일까지」 → 「다음주금요일」)
- 규칙을 위에서부터 맞춰 보고 처음 맞는 것을 쓴다. 맞는 게 없으면 None

| 정리된 글자 | 날짜 (B = 기준일, 한 주는 월요일 시작) |
|---|---|
| 오늘 · 금일 | B |
| 내일 | B+1 |
| 모레 | B+2 |
| 어제 | B-1 |
| N일뒤 · N일후 | B+N |
| N주뒤 · N주후 | B+7N |
| 다음주 · 차주 | B+7 |
| 지난주 | B-7 |
| 이번주X요일 · X요일 | B 가 속한 주의 X요일 (지났어도 그 주) |
| 다음주X요일 · 차주X요일 | B 다음 주의 X요일 |
| 지난주X요일 | B 지난 주의 X요일 |
| 이번달말 · 월말 | B 달의 마지막 날 |
| 다음달말 | 다음 달 마지막 날 |
| 이번달N일 · N일 | B 달의 N일 |
| 다음달N일 | 다음 달 N일 |
| M월N일 | B 해의 M월 N일. B 보다 앞이면 다음 해 |
| M/D | M월N일과 같음 |
| YYYY-MM-DD · YYYY.MM.DD | 그 날짜 |
| 지난달 · 다음달 · 이번주 · 이번주안 · 미정 · 빈 값 · 그 밖 | None |

- 요일은 월 · 화 · 수 · 목 · 금 · 토 · 일 한 글자 또는 「요일」 붙인 형태 둘 다 받는다 (「금」 · 「금요일」)
- 없는 날짜(2월 30일)는 None. 다음 달 N일에서 N 이 그 달에 없으면 None
- 「이번 주」 · 「지난 달」처럼 날 하나로 정해지지 않는 말은 None 으로 둔다 - 사용자 지시 「못 정하면 비워 두고」. 「다음 주까지」만 지시대로 B+7
- 대안: dateparser 같은 라이브러리 - 한국어 상대 표현 지원이 들쭉날쭉하고 결과를 표로 약속할 수 없어 쓰지 않는다. Gemini 에게 날짜까지 뽑게 하는 것도 실행마다 달라질 수 있어 쓰지 않는다

### 2. 기준일

```
base_date(todo) = KST 날짜(meeting.met_at)   # 회의록에서 뽑힌 할 일
                = KST 날짜(todo.created_at)  # 직접 등록 (meeting_id 가 null)
```

- KST 는 `timezone(timedelta(hours=9))` 고정. Windows 에서 `zoneinfo` 는 tzdata 패키지가 따로 필요하고, 한국은 서머타임이 없으므로 고정 오프셋이 충분하다
- 회의록 저장(`create_meeting`)은 met_at 이 먼저 정해지므로 할 일을 만들 때 바로 환산한다
- 직접 등록은 등록 시각이 기준이므로 `created_at` 을 정한 뒤 환산한다

### 3. 다시 환산하는 때

| 일 | 처리 |
|---|---|
| `PUT /api/todos/{id}` 에 `due_text` 가 옴 | 그 할 일의 기준일로 다시 환산 |
| `PUT /api/meetings/{id}` 에 `met_at` 이 와서 값이 바뀜 | 그 회의록에서 뽑힌 할 일 전부를 새 기준일로 다시 환산 (due_text 는 그대로) |
| 상태 · 담당자만 바뀜 | 그대로 |

### 4. DB 칼럼 추가와 채우기 - `backend/db.py`

- `models.Todo` 에 `due_date: Mapped[date | None]` (`Date`, nullable)
- `create_all()` 뒤에 `upgrade()` 를 돈다
  1. `sqlalchemy.inspect(engine).get_columns("todos")` 에 `due_date` 가 없으면 `ALTER TABLE todos ADD COLUMN due_date DATE` (SQLite · Postgres 둘 다 같은 문장)
  2. `due_date IS NULL AND due_text <> ''` 인 할 일을 읽어 `resolve(due_text, base_date(todo))` 로 채운다. None 이면 그대로 둔다
- 두 번째 시작부터는 칼럼이 있으니 1 은 건너뛰고, 2 는 채울 게 없거나(정할 수 없는 글자뿐) 결과가 같아 값이 바뀌지 않는다
- 대안: Alembic 도입 - 칼럼 하나에 도구를 들이는 것보다 시작 때 확인이 단순하다. 다음 칼럼 변경이 잦아지면 그때 도입을 다시 본다

### 5. 응답과 정렬 - `backend/serial.py`

- `todo_out` 에 `"due_date": t.due_date.isoformat() if t.due_date else None`
- `sort_todos` 의 열쇠를 `(status 순서, due_date 없음 여부, due_date, id)` 로. 같은 날짜면 id 순

### 6. 화면 - 기한 배지와 기한 지남

- 공통 함수는 `frontend/api.js` 에 둔다 (세 화면이 같이 씀)
  - `dueLabel(todo)` → due_date 가 있으면 `"11-20 (금)"`, 없으면 due_text, 둘 다 없으면 「미정」
  - `isOverdue(todo)` → `todo.due_date && todo.status !== "DONE" && todo.due_date < 오늘(현지 YYYY-MM-DD)`
- `todos.html` · `detail.html` · `profile.html` 의 기한 배지: 날짜를 앞에, 원래 글자를 같은 배지 안 보조 글자(`text-ink-3`)로. 배지 클래스는 지금 것 그대로 쓰고 새 색 · 새 조합을 만들지 않는다
- 기한 지남 붉은 띠(`STRIPE.red`)는 `isOverdue` 로만 정한다. 기존 낱말 판정은 지운다
- 기한을 고치는 입력은 지금처럼 글자로 받는다 (PUT due_text) - 저장 응답의 due_date 로 배지를 다시 그린다

## Risks / Trade-offs

- [기준일이 한국 날짜, 오늘은 보는 사람 날짜] → 한국 밖에서 보면 하루 어긋날 수 있다. 사용자 전제가 한국어 사용자라 받아들인다
- [표에 없는 표현은 null] → 「이번 주 안」 「곧」 같은 기한은 날짜가 없어 기한 지남 판정에서 빠진다. 글자는 남으므로 사람이 볼 수 있다. 자주 나오는 표현이 보이면 표에 더한다
- [요일만 적힌 기한이 이미 지난 요일] → 「월요일」을 목요일 회의에서 말하면 같은 주 월요일(과거)로 잡혀 바로 기한 지남이 된다. 다음 주 월요일로 볼지 애매해 「그 주」로 고정했다 → 자주 틀리면 「기준일 이후 가장 가까운 X요일」로 바꾸는 것을 다시 본다
- [시작 때 마이그레이션] → Vercel 은 콜드 스타트마다 확인 쿼리가 한 번 더 돈다. 칼럼 확인 한 번 · 빈 칸 조회 한 번이라 비용이 작다
- [정렬 순서 변경] → 기존 화면은 서버 순서를 그대로 쓰므로 카드 순서가 바뀐다. 의도한 변화다

## Migration Plan

1. 배포 전: 로컬 SQLite 사본으로 서버를 띄워 칼럼 추가와 채우기를 확인
2. 배포: 코드만 올리면 첫 요청 때 Neon 에 칼럼이 추가되고 채워진다
3. 되돌리기: 이전 코드로 되돌려도 `due_date` 칼럼은 쓰지 않을 뿐 남아 있어 동작에 문제가 없다
