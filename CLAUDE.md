# OpenSpec 단계 표시

- 사용자가 메시지를 보낼 때마다 훅(`.claude/hooks/openspec-stage.sh`)이 `📐 OpenSpec 단계: EXPLORE | [EXPLORE] > propose > apply > archive | …` 한 줄을 화면 로그에 남긴다
- 단계는 **워크플로 단계** 넷이다: explore → propose → apply → archive. openspec-* 스킬을 부르면 PostToolUse(Skill) 훅이 `.claude/openspec-phase` 에 적는다 (explore · propose · update-change=propose · apply-change=apply · sync-specs · archive-change=archive)
- 줄 끝에는 change 마다 산출물 진행도(proposal · specs · design · tasks 작성 전, tasks 완료/전체)를 붙인다
- **모든 답변의 맨 윗줄에 그 단계 줄을 그대로 적는다.** 답변 중에 단계가 바뀌었으면(다른 openspec 스킬 호출, 산출물 작성, 작업 체크) 답변 끝에 바뀐 단계 줄을 한 번 더 적는다

# 작업 관리 규칙 (todo-guard)

<!-- todo-guard 운영 규칙 v8 · setup.sh 가 관리한다. 원본은 ~/.claude/skills/todo-guard/rules/claude-md-block.md -->

- 지시는 훅이 받는 순간 TODO.md 에 `#번호` 로 적는다. 여러 슬라이드 · 여러 항목을 한 메시지로 주면 항목마다 나눠 적고 목록을 보여 준다. 직접 등록하지 않고, TODO.md 를 읽거나 고치지 않는다
- **목록의 항목을 전부 한다.** 1~2개만 하고 끝내지 않는다. 남은 것이 있으면 턴이 끝나지 않는다
- 편집은 몰아서 해도 된다. 끝나면 **실제로 끝낸 번호만** 확인 명령 뒤에 적는다: `… && bash "$HOME/.claude/skills/todo-guard/scripts/todo.sh" done 3.1 3.2 5`
- 적힌 뒤 파일을 바꾼 횟수보다 많이 done 하거나, 항목에 적힌 파일 · 슬라이드를 바꾸지 않고 done 하면 거부된다
- **항목 글에 파일 이름도 슬라이드 번호도 없으면 무엇을 바꿨는지 대야 한다**: `todo.sh done 5 --file ktds_ch3.js`. 댄 파일은 그 항목이 적힌 뒤 바뀐 기록에 있어야 받는다. 전에는 이 자리가 비어 있어, 아무 파일이나 바꾸면 아무 항목이나 닫혔다
- 파일을 바꾸지 않고 끝나는 일(빌드 · 테스트 · 조사 · 답변)이나 스크립트 하나로 여러 항목을 고친 경우는 사유를 붙인다: `todo.sh done 5 --why "빌드 성공"`. 사유는 항목 옆에 남아 사용자가 본다. **사유는 120자 안으로 적는다** - 넘으면 잘려 나중에 읽을 수 없다
- 번호를 반복문으로 통째로 돌려 done 하지 않는다 (막힌다). 끝나지 않은 것은 done 하지 않는다. 사용자 판단이 필요하면 `todo.sh hold 14 "사유"`, 지시에 없던 일은 `todo.sh add "할 일"`
- 질문 · 의견에는 그냥 답한다. 파일을 바꾸지 않았으면 훅이 지운다. 「바꿔 · 넣어 · 고쳐」 같은 지시는 하겠다고만 하고 끝내도 지워지지 않는다
- TODO.md 맨 위 「항상 지킬 것」은 지킨다. 「앞으로 ~하지 마 · 항상 ~해」는 `bash "$HOME/.claude/skills/todo-guard/scripts/rule.sh" add "규칙"` 으로 등록한다
