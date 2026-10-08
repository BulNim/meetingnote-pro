// 팀 설정 (스토리보드 F-01 ~ F-08)
(function () {
  const { api, esc, fmtWhen, toast } = App;
  const $ = (id) => document.getElementById(id);

  // 활동 종류별 띠 색 (팔레트 5색 안에서만)
  const KIND_COLOR = {
    meeting_add: "blue", todo_assign: "orange", todo_done: "green", comment_add: "purple", member_join: "purple"
  };

  // 클래스는 theme.js 의 이름으로만 입힌다
  $("onboard").className = "hidden " + UI.panel + " " + STRIPE.purple + " p-5";
  $("onboardSub").className = UI.sub + " mt-1";
  ["createBox", "joinBox"].forEach((id) => { $(id).className = UI.card + " p-4"; });
  $("newName").className = UI.input;
  $("joinCode").className = UI.input + " font-mono tracking-widest";
  $("createBtn").className = UI.btnPrimary + " mt-2.5 w-full";
  $("joinBtn").className = UI.btnGhost + " mt-2.5 w-full";
  $("info").className = UI.panel + " p-5";
  $("tName").className = UI.input + " font-bold";
  $("saveName").className = UI.btnPrimary + " mt-2";
  ["copyBtn", "newCodeBtn"].forEach((id) => { $(id).className = UI.btnGhost; });
  $("lockNote").className = "hidden " + UI.meta + " mt-3";
  $("memberBox").className = UI.panel + " p-5";
  $("actBox").className = UI.panel + " p-5";
  $("mLimit").className = UI.meta + " ml-auto";
  $("aLimit").className = UI.meta;
  $("aEmpty").className = "hidden " + UI.sub + " px-4 py-8 text-center";

  let ctx = null, team = null;

  function show(boxId, kind, title, body) {
    $(boxId).innerHTML = window.notice(kind, esc(title), body ? esc(body) : "");
    $(boxId).classList.remove("hidden");
  }

  // ── 소속 팀 없음: 만들기 / 합류 ──
  function showOnboard() {
    $("onboard").classList.remove("hidden");
    $("teamView").classList.add("hidden");
  }

  async function createTeam() {
    const name = $("newName").value.trim();
    $("onboardErr").classList.add("hidden");
    if (!name) { show("onboardErr", "red", "팀 이름을 입력해야 함", ""); return; }
    $("createBtn").disabled = true;
    try {
      await api.post("/api/teams", { name });
      location.reload();
    } catch (e) {
      $("createBtn").disabled = false;
      show("onboardErr", "red", "팀을 만들지 못함", e.message);
    }
  }

  async function joinTeam() {
    const code = $("joinCode").value.trim();
    $("onboardErr").classList.add("hidden");
    if (!code) { show("onboardErr", "red", "초대코드를 입력해야 함", ""); return; }
    $("joinBtn").disabled = true;
    try {
      await api.post("/api/teams/join", { invite_code: code });
      location.reload();
    } catch (e) {
      $("joinBtn").disabled = false;
      $("joinCode").classList.add("border-red-dot");
      const title = e.code === "INVITE_NOT_FOUND" ? "없는 초대코드"
        : e.code === "TEAM_FULL" ? "팀 정원이 찼음" : "합류하지 못함";
      // 합류가 실패해도 가입한 계정은 그대로 유지된다
      show("onboardErr", "red", title, e.message);
    }
  }

  // ── 팀 정보 ──
  function renderInfo(owner) {
    $("tName").value = team.name;
    $("code").textContent = team.invite_code;
    ["saveName", "newCodeBtn"].forEach((id) => { $(id).disabled = !owner; });
    $("tName").readOnly = !owner;
    $("tName").classList.toggle("opacity-60", !owner);
    // 읽기 전용이어도 복사는 막을 이유가 없지만 F-08 은 owner 전용 조작을 잠근다고만 적었다
    $("lockNote").textContent = owner ? "" : "owner 전용 조작 잠김 - 팀 이름 변경 · 초대코드 재발급은 owner 만 가능";
    $("lockNote").classList.toggle("hidden", owner);
  }

  function renderMembers(list) {
    $("members").innerHTML = list.map((m) => `
      <li class="${UI.card} p-3 flex items-center gap-3">
        <div class="w-9 h-9 rounded-xl bg-page dark:bg-chip border border-line dark:border-edge grid place-items-center text-[13px] font-extrabold">${esc(m.name.slice(0, 1))}</div>
        <div class="flex-1 min-w-0">
          <p class="text-[13px] font-bold">${esc(m.name)}</p>
          <p class="${UI.meta} truncate">${esc(m.email)}</p>
        </div>
        <div class="text-right shrink-0">
          <span class="${UI.chip} ${m.role === "owner" ? LABEL.purple : ""}">${m.role}</span>
          <p class="mt-1 text-[10px] text-ink-3 dark:text-dim">할 일 ${m.todo_count}</p>
        </div>
      </li>`).join("");
    $("mCap").textContent = list.length + " / 6";
  }

  function renderActs(list) {
    $("acts").innerHTML = list.map((a) => `
      <li class="${UI.card} ${STRIPE[KIND_COLOR[a.kind]]} px-3.5 py-2.5">
        <p class="text-[13px]"><span class="font-bold">${esc(a.actor_name)}</span>  ·  ${esc(a.text)}</p>
        <p class="${UI.meta} mt-0.5">${fmtWhen(a.created_at)}</p>
      </li>`).join("");
    $("acts").classList.toggle("hidden", list.length === 0);
    $("aEmpty").classList.toggle("hidden", list.length > 0);
    $("aEmpty").textContent = "아직 활동이 없음";
  }

  async function saveName() {
    const name = $("tName").value.trim();
    if (!name) { toast("red", "팀 이름을 입력해야 함", ""); return; }
    $("saveName").disabled = true;
    try {
      const row = await api.put(`/api/teams/${team.id}`, { name });
      team.name = row.name;
      toast("green", "팀 이름을 저장함", "");
    } catch (e) {
      // member 가 부르면 403 OWNER_ONLY
      toast("red", e.code === "OWNER_ONLY" ? "owner 만 수정 가능" : "저장하지 못함", e.message);
    } finally {
      $("saveName").disabled = ctx.me.role !== "owner";
    }
  }

  async function copyCode() {
    try {
      await navigator.clipboard.writeText(team.invite_code);
      toast("green", "복사했습니다", "받는 사람은 회원가입 화면의 초대코드 칸에 붙여넣음");
    } catch (e) {
      toast("orange", "복사하지 못함", "코드를 직접 선택해 복사");
    }
  }

  async function newCode() {
    $("newCodeBtn").disabled = true;
    try {
      const res = await api.put(`/api/teams/${team.id}/code`);
      team.invite_code = res.invite_code;
      $("code").textContent = res.invite_code;
      show("codeMsg", "orange", "초대코드를 다시 발급함", "앞의 코드는 더 쓸 수 없음. 이미 합류한 멤버는 그대로");
    } catch (e) {
      show("codeMsg", "red", e.code === "OWNER_ONLY" ? "owner 전용 조작" : "재발급하지 못함", e.message);
    } finally {
      $("newCodeBtn").disabled = ctx.me.role !== "owner";
    }
  }

  async function showTeam() {
    $("teamView").classList.remove("hidden");
    $("onboard").classList.add("hidden");
    renderInfo(ctx.me.role === "owner");
    const [members, acts] = await Promise.all([
      api.get(`/api/teams/${team.id}/members`),
      api.get(`/api/teams/${team.id}/activities`)
    ]);
    renderMembers(members);
    renderActs(acts);
  }

  (async function init() {
    ctx = await App.boot({ active: "team", needTeam: false });
    if (!ctx) return;
    $("createBtn").onclick = createTeam;
    $("joinBtn").onclick = joinTeam;
    $("saveName").onclick = saveName;
    $("copyBtn").onclick = copyCode;
    $("newCodeBtn").onclick = newCode;
    team = ctx.team;
    if (!team) { showOnboard(); return; }
    try {
      await showTeam();
    } catch (e) {
      toast("red", "팀 정보를 불러오지 못함", e.message);
    }
  })();
})();
