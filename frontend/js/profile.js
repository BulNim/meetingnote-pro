// 내 정보 (스토리보드 J-01 ~ J-07, 현재 비밀번호 칸은 구현에서 추가 - 결정기록 D-024)
(function () {
  const { api, esc, fmtWhen, store, toast } = App;
  const $ = (id) => document.getElementById(id);

  const STATUS = { OPEN: ["대기", "orange"], DOING: ["진행", "blue"], DONE: ["완료", "green"] };
  const KIND_COLOR = {
    meeting_add: "blue", todo_assign: "orange", todo_done: "green", comment_add: "purple", member_join: "purple"
  };

  // 클래스는 theme.js 의 이름으로만 입힌다
  ["account", "todoBox", "actBox"].forEach((id) => { $(id).className = UI.panel + " p-5"; });
  ["name", "pwCur", "pw1", "pw2"].forEach((id) => { $(id).className = UI.input; });
  $("mail").className = UI.meta;
  $("role").className = "hidden ml-auto " + UI.badge + " bg-page dark:bg-chip " + LABEL.purple;
  ["errName", "errCur", "errPw"].forEach((id) => { $(id).dataset.kind = "err"; });
  $("saveBtn").className = UI.btnPrimary;
  $("logoutBtn").className = UI.btnGhost;
  $("note").className = UI.meta + " mt-3";
  $("tCount").className = UI.meta;
  $("toBoard").className = "ml-auto text-[11px] " + UI.link;
  $("aLabel").className = UI.meta;
  $("aCount").className = UI.meta + " ml-auto";
  $("aEmptySub").className = UI.sub + " mt-1";
  $("tEmpty").className = "hidden " + UI.sub;

  let ctx = null, busy = false, me = null;

  function fieldError(id, input, msg) {
    const el = $(id);
    el.className = UI.errText;
    el.textContent = msg;
    el.classList.remove("hidden");
    if (input) input.classList.add("border-red-dot");
  }

  function reset() {
    ["errName", "errCur", "errPw", "msg"].forEach((id) => { $(id).classList.add("hidden"); $(id).textContent = ""; });
    ["name", "pwCur", "pw1", "pw2"].forEach((id) => $(id).classList.remove("border-red-dot"));
  }

  function renderMe() {
    $("who").textContent = me.name;
    $("mail").textContent = me.email;
    $("avatar").textContent = me.name.slice(0, 1);
    $("name").value = me.name;
    $("role").textContent = me.role || "";
    $("role").classList.toggle("hidden", !me.role);
    $("note").textContent = "이메일은 고칠 수 없음";
  }

  function renderTodos(list) {
    $("todos").innerHTML = list.map((t) => {
      const [label, color] = STATUS[t.status];
      return `
      <li class="${UI.card} ${STRIPE[color]} px-3.5 py-2.5">
        <p class="text-[13px] font-bold">${esc(t.what)}</p>
        <div class="mt-1 flex gap-1.5">
          <span class="${UI.chip}">${esc(t.due_text)}</span>
          <span class="${UI.chip} ${LABEL[color]}">${label}</span>
        </div>
      </li>`;
    }).join("");
    $("tCount").textContent = list.length + "건";
    $("tEmpty").textContent = "배정된 할 일 0건";
    $("tEmpty").classList.toggle("hidden", list.length > 0);
  }

  function renderActs(list) {
    $("acts").innerHTML = list.map((a) => `
      <li class="${UI.card} ${STRIPE[KIND_COLOR[a.kind]]} px-3.5 py-2.5">
        <p class="text-[13px]">${esc(a.text)}</p>
        <p class="${UI.meta} mt-0.5">${fmtWhen(a.created_at)}</p>
      </li>`).join("");
    $("aCount").textContent = list.length ? list.length + "건" : "";
    $("acts").classList.toggle("hidden", list.length === 0);
    $("aEmpty").classList.toggle("hidden", list.length > 0);
  }

  async function save() {
    if (busy) return;                       // 저장 중에는 버튼을 잠가 두 번 눌리지 않게
    reset();
    const name = $("name").value.trim();
    const cur = $("pwCur").value, p1 = $("pw1").value, p2 = $("pw2").value;
    const changingPw = p1 !== "" || p2 !== "";

    if (!name) { fieldError("errName", $("name"), "이름을 입력해야 함"); return; }
    if (changingPw) {
      // 두 칸이 다르면 서버로 보내지 않고 화면에서 먼저 거른다 (J-03)
      if (p1 !== p2) { fieldError("errPw", $("pw2"), "두 비밀번호가 다름"); return; }
      if (p1.length < 8) { fieldError("errPw", $("pw1"), "비밀번호는 8자 이상"); return; }
      if (!cur) { fieldError("errCur", $("pwCur"), "현재 비밀번호를 입력해야 함"); return; }
    }

    // 이름만 보내면 비밀번호는 그대로다 (J-02)
    const body = { name };
    if (changingPw) { body.current_password = cur; body.new_password = p1; }

    busy = true;
    $("saveBtn").disabled = true;
    $("saveBtn").textContent = "저장 중...";
    try {
      me = await api.put("/api/auth/me", body);
      renderMe();
      ["pwCur", "pw1", "pw2"].forEach((id) => { $(id).value = ""; });
      $("msg").innerHTML = window.notice("green", "저장함", "");
      $("msg").classList.remove("hidden");
    } catch (e) {
      if (e.code === "INVALID_CREDENTIALS") fieldError("errCur", $("pwCur"), "현재 비밀번호가 올바르지 않음");
      else if (e.code === "PASSWORD_TOO_WEAK") fieldError("errPw", $("pw1"), "비밀번호는 8자 이상");
      else toast("red", "저장하지 못함", e.message);
    } finally {
      busy = false;
      $("saveBtn").disabled = false;
      $("saveBtn").textContent = "저장";
    }
  }

  async function logout() {
    try { await api.post("/api/auth/logout"); } catch (e) { /* 서버는 토큰을 따로 두지 않으므로 실패해도 화면은 나간다 */ }
    App.goLogin(false);
  }

  (async function init() {
    ctx = await App.boot({ active: "profile", needTeam: false });
    if (!ctx) return;
    me = ctx.me;
    renderMe();
    $("saveBtn").onclick = save;
    $("logoutBtn").onclick = logout;
    try {
      const [todos, acts] = await Promise.all([api.get("/api/me/todos"), api.get("/api/me/activities")]);
      renderTodos(todos);
      renderActs(acts);
    } catch (e) {
      toast("red", "불러오지 못함", e.message);
    }
  })();
})();
