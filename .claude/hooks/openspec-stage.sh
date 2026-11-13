#!/usr/bin/env bash
# OpenSpec 워크플로 단계(explore · propose · apply · archive)와 change 진행도를 한 줄로 출력한다.
#
#  - UserPromptSubmit : 사용자가 /openspec-* 로 시작하면 단계를 기록하고, 단계 줄을 화면 로그에 남긴다
#  - PostToolUse(Skill): Claude 가 openspec-* 스킬을 부르면 단계를 기록만 한다 (출력 없음)
#
# 단계는 .claude/openspec-phase 에 적는다. 기록이 없으면 change 파일 상태로 짐작한다.
# 빠르게 돌도록 openspec CLI(node) 대신 파일만 읽는다.

root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
changes="$root/openspec/changes"
phase_file="$root/.claude/openspec-phase"
[ -d "$root/openspec" ] || exit 0

input=""
[ -t 0 ] || input=$(cat)

# 스킬 이름 -> 단계
phase_of_skill() {
  case "$1" in
    openspec-explore)        echo explore ;;
    openspec-propose)        echo propose ;;
    openspec-update-change)  echo propose ;;
    openspec-apply-change)   echo apply ;;
    openspec-sync-specs)     echo archive ;;
    openspec-archive-change) echo archive ;;
  esac
}

event=$(printf '%s' "$input" | grep -o '"hook_event_name" *: *"[A-Za-z]*"' | head -1 | sed 's/.*"\([A-Za-z]*\)"$/\1/')

if [ "$event" = "PostToolUse" ]; then
  skill=$(printf '%s' "$input" | grep -o '"skill" *: *"openspec-[a-z-]*"' | head -1 | sed 's/.*"\(openspec-[a-z-]*\)"$/\1/')
  p=$(phase_of_skill "$skill")
  [ -n "$p" ] && printf '%s\n' "$p" > "$phase_file"
  exit 0
fi

# 사용자가 /openspec-xxx 로 시작한 경우
skill=$(printf '%s' "$input" | grep -o '"prompt" *: *"/openspec-[a-z-]*' | head -1 | sed 's/.*"\/\(openspec-[a-z-]*\)$/\1/')
p=$(phase_of_skill "$skill")
[ -n "$p" ] && printf '%s\n' "$p" > "$phase_file"

# change 하나의 산출물 진행도
stage_of() {
  local d="$1"
  if [ ! -s "$d/proposal.md" ]; then echo "proposal 작성 전"; return; fi
  if ! ls "$d"/specs/*/spec.md >/dev/null 2>&1; then echo "specs 작성 전"; return; fi
  if [ ! -s "$d/design.md" ]; then echo "design 작성 전"; return; fi
  if [ ! -s "$d/tasks.md" ]; then echo "tasks 작성 전"; return; fi
  local total done
  total=$(grep -cE '^[[:space:]]*- \[[ xX]\]' "$d/tasks.md")
  done=$(grep -cE '^[[:space:]]*- \[[xX]\]' "$d/tasks.md")
  echo "tasks $done/$total"
}

items=(); guess=""
for d in "$changes"/*/; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  [ "$name" = "archive" ] && continue
  s=$(stage_of "${d%/}")
  items+=("$name ($s)")
  case "$s" in
    tasks\ *) t=${s#tasks }; [ "${t%/*}" = "${t#*/}" ] && [ "${t#*/}" != 0 ] && guess=archive || guess=apply ;;
    *) [ -z "$guess" ] && guess=propose ;;
  esac
done

phase=$(cat "$phase_file" 2>/dev/null | tr -d '\r\n ')
[ -z "$phase" ] && phase="${guess:-explore}"

# 진행 막대: 지금 단계만 [대괄호]
bar=""
for s in explore propose apply archive; do
  if [ "$s" = "$phase" ]; then seg="[${s^^}]"; else seg="$s"; fi
  bar="${bar:+$bar > }$seg"
done

if [ ${#items[@]} -eq 0 ]; then
  detail="change 없음"
else
  detail="${items[0]}"
  for ((i=1; i<${#items[@]}; i++)); do detail="$detail, ${items[$i]}"; done
fi

echo "📐 OpenSpec 단계: ${phase^^}  |  $bar  |  $detail"
