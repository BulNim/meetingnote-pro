// 할 일 칸반 (스토리보드 E-01 ~ E-12)
(function () {
  const { api, esc, toast } = App;
  const $ = (id) => document.getElementById(id);

  const COLS = [
    { key: "OPEN", label: "대기", color: "orange" },
    { key: "DOING", label: "진행", color: "blue" },
    { key: "DONE", label: "완료", color: "green" }
  ];
  // 기한은 자유 글자라 이번 회차는 publish 방식 그대로 눌러서 돌려 가며 고른다 (결정기록 D-003)
  const WHEN = ["미정", "오늘", "이번 주 안", "다음 주 금요일", "어제", "지난 주"];
  const LATE_WORDS = ["어제", "지난 주", "지난 달"];
  const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

  // 클래스는 theme.js 의 이름으로만 입힌다
  $("bar").className = UI.panel + " p-4 mb-4";
  $("fWho").className = UI.selectInline;
  $("sum").className = UI.meta + " ml-auto";
  $("empty").className = "hidden " + UI.panel + " px-5 py-12 text-center";
  $("emptySub").className = UI.sub + " mt-1";
  $("help").className = UI.meta + " mt-3";

  let ctx = null, members = [], mine = true, filter = "";
  let rows = [], dragId = null, overCol = null;

  function isLate(t) {
    if (t.status === "DONE") return false;
    if (DATE_RE.test(t.due_text)) {
      const d = new Date(), today = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0");
      return t.due_text < today;
    }
    return LATE_WORDS.includes(t.due_text);
  }

  const isOwner = () => ctx.me.role === "owner";

  function visibleRows() {
    if (mine || !filter) return rows;
    if (filter === "none") return rows.filter((t) => t.assignee_id === null);
    return rows.filter((t) => t.assignee_id === +filter);
  }

  // ── 그리기 ──
  function cardHtml(t) {
    const late = isLate(t);
    return `
    <article data-id="${t.id}" class="card touch-none select-none cursor-grab active:cursor-grabbing ${UI.card} ${late ? STRIPE.red : ""} p-3 hover:border-ink dark:hover:border-dim transition ${dragId === t.id ? "opacity-40" : ""}">
      <p class="text-[13px] font-bold leading-snug">${esc(t.what)}</p>
      <p class="mt-1 ${UI.meta}">${esc(t.meeting_title)}</p>
      <div class="mt-2 flex items-center gap-1.5">
        <button type="button" data-act="assign" data-id="${t.id}" class="${UI.chipBtn}">${esc(t.assignee_name || "미정")}</button>
        <button type="button" data-act="due" data-id="${t.id}" class="${UI.chipBtn} ${late ? LABEL.red : ""}">${esc(t.due_text)}</button>
        <button type="button" data-act="del" data-id="${t.id}" class="${UI.chipBtn} ${LABEL.red} ml-auto" ${isOwner() ? "" : "disabled"} title="${isOwner() ? "" : "owner 만 삭제할 수 있음"}">삭제</button>
      </div>
    </article>`;
  }

  function render() {
    const list = visibleRows();
    $("board").innerHTML = COLS.map((c) => {
      const items = list.filter((t) => t.status === c.key);
      return `
      <section data-col="${c.key}" class="dropzone ${UI.panel} ${STRIPE[c.color]} p-4 min-h-[220px] transition">
        <div class="flex items-baseline gap-2 mb-3">
          <h2 class="text-sm font-extrabold ${LABEL[c.color]}">${c.label}</h2>
          <span class="${UI.meta}">${items.length}건</span>
          <span data-hint class="hidden ml-auto text-[10px] font-extrabold ${LABEL[c.color]}">여기에 놓기</span>
        </div>
        <div class="space-y-2.5">${items.map(cardHtml).join("") || `<p class="${UI.sub} py-2">없음</p>`}</div>
      </section>`;
    }).join("");
    $("board").classList.toggle("hidden", list.length === 0);
    $("empty").classList.toggle("hidden", list.length > 0);
    const done = list.filter((t) => t.status === "DONE").length;
    $("sum").textContent = list.length ? `${done} / ${list.length} 완료` : "";
    $("tabMine").className = mine ? UI.tabOn : UI.tab;
    $("tabAll").className = mine ? UI.tab : UI.tabOn;
    $("fWho").classList.toggle("hidden", mine);
    $("emptyTitle").textContent = mine ? "배정된 할 일이 없음" : (filter ? "이 담당자의 할 일이 없음" : "할 일이 없음");
    bindCards();
  }

  // 끌고 있을 때는 다시 그리지 않고 놓을 칸 표시만 바꾼다
  function markDropTarget(col) {
    overCol = col;
    document.querySelectorAll(".dropzone").forEach((z) => {
      const c = COLS.find((x) => x.key === z.dataset.col);
      const hot = z.dataset.col === col;
      DROP[c.color].split(" ").forEach((cls) => z.classList.toggle(cls, hot));
      z.querySelector("[data-hint]").classList.toggle("hidden", !hot);
    });
  }

  // ── 서버와 맞추기 ──
  async function load() {
    try {
      rows = mine
        ? await api.get("/api/me/todos")
        : await api.get(`/api/teams/${ctx.team.id}/todos`);
    } catch (e) {
      toast("red", "할 일을 불러오지 못함", e.message);
      return;
    }
    render();
  }

  async function patch(t, body, okTitle, okBody) {
    try {
      const row = await api.put(`/api/todos/${t.id}`, body);
      Object.assign(t, row);
      toast("green", okTitle, okBody || "");
      return true;
    } catch (e) {
      toast("red", "저장하지 못함", e.message);
      return false;
    }
  }

  // 놓는 순간 한 번만 호출. 실패하면 카드가 원래 칸으로 돌아간다
  async function moveTo(t, col) {
    const before = t.status;
    t.status = col;
    render();
    const ok = await patch(t, { status: col }, "상태를 옮김", COLS.find((c) => c.key === col).label + " 칸으로 옮겼습니다");
    if (!ok) t.status = before;
    render();
  }

  async function cycleDue(t) {
    const next = WHEN[(WHEN.indexOf(t.due_text) + 1) % WHEN.length];
    await patch(t, { due_text: next }, "기한을 바꿈", next);
    render();
  }

  // 담당자 칩을 누르면 카드 안에서 선택 상자가 열린다. 미정도 한 값
  function openAssignPicker(t, anchor) {
    const sel = document.createElement("select");
    sel.className = UI.select;
    sel.setAttribute("aria-label", "담당자");
    sel.innerHTML = [`<option value="">미정</option>`]
      .concat(members.map((m) => `<option value="${m.id}" ${m.id === t.assignee_id ? "selected" : ""}>${esc(m.name)}</option>`)).join("");
    anchor.replaceWith(sel);
    sel.focus();
    sel.onchange = async () => {
      await patch(t, { assignee_id: sel.value === "" ? null : +sel.value }, "담당자를 바꿈",
        sel.value === "" ? "담당자 미정" : sel.options[sel.selectedIndex].text + "에게 배정");
      if (mine) await load(); else render();
    };
    sel.onblur = () => render();
  }

  async function removeTodo(t) {
    if (!window.confirm("이 할 일을 삭제할까요?")) return;
    try {
      await api.del(`/api/todos/${t.id}`);
      rows = rows.filter((x) => x.id !== t.id);
      toast("green", "할 일을 삭제함", "");
    } catch (e) {
      toast("red", "삭제하지 못함", e.message);
    }
    render();
  }

  // ── 카드 조작: 끌어 옮기기(포인터 이벤트) / 눌러서 칸 고르기 / 칩 ──
  let ghost = null, startX = 0, startY = 0, moved = false;

  function colUnder(x, y) {
    const el = document.elementFromPoint(x, y);
    const z = el && el.closest(".dropzone");
    return z ? z.dataset.col : null;
  }

  function openPicker(t) {
    closePicker();
    const card = document.querySelector(`.card[data-id="${t.id}"]`);
    if (!card) return;
    const box = document.createElement("div");
    box.id = "picker";
    box.className = "mt-2 flex gap-1.5 border-t border-line dark:border-edge pt-2";
    COLS.forEach((c) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = c.label;
      b.className = (t.status === c.key ? UI.btnGhost + " opacity-40 " : UI.btnGhost + " " + LABEL[c.color] + " ") + "flex-1";
      b.disabled = t.status === c.key;
      b.addEventListener("pointerdown", (ev) => ev.stopPropagation());
      b.addEventListener("click", (ev) => { ev.stopPropagation(); moveTo(t, c.key); });
      box.appendChild(b);
    });
    card.appendChild(box);
  }
  function closePicker() { const p = document.getElementById("picker"); if (p) p.remove(); }
  document.addEventListener("pointerdown", (e) => { if (!e.target.closest(".card")) closePicker(); });

  function bindCards() {
    document.querySelectorAll("[data-act]").forEach((el) => {
      el.addEventListener("pointerdown", (e) => e.stopPropagation());
      el.addEventListener("click", (e) => {
        e.stopPropagation();
        const t = rows.find((x) => x.id === +el.dataset.id);
        if (!t) return;
        if (el.dataset.act === "assign") openAssignPicker(t, el);
        else if (el.dataset.act === "due") cycleDue(t);
        else if (el.dataset.act === "del") removeTodo(t);
      });
    });
    document.querySelectorAll(".card").forEach((el) => {
      el.addEventListener("pointerdown", (e) => {
        if (e.target.closest("[data-act]") || e.target.closest("#picker")) return;
        if (e.button !== undefined && e.button !== 0) return;
        dragId = +el.dataset.id;
        startX = e.clientX; startY = e.clientY; moved = false;
        el.setPointerCapture(e.pointerId);
      });
      el.addEventListener("pointermove", (e) => {
        if (dragId === null) return;
        if (!moved) {
          if (Math.abs(e.clientX - startX) < 6 && Math.abs(e.clientY - startY) < 6) return;
          moved = true;
          closePicker();
          const r = el.getBoundingClientRect();
          ghost = el.cloneNode(true);
          ghost.classList.add("fixed", "pointer-events-none", "z-50", "opacity-80", "shadow-lg");
          ghost.style.width = r.width + "px";
          document.body.appendChild(ghost);
          el.classList.add("opacity-40");
        }
        e.preventDefault();
        ghost.style.left = (e.clientX - 40) + "px";
        ghost.style.top = (e.clientY - 18) + "px";
        const c = colUnder(e.clientX, e.clientY);
        if (c !== overCol) markDropTarget(c);
      });
      const finish = (e) => {
        if (dragId === null) return;
        if (ghost) { ghost.remove(); ghost = null; }
        const id = dragId;
        const col = moved ? colUnder(e.clientX, e.clientY) : null;
        const wasTap = !moved;
        const t = rows.find((x) => x.id === id);
        dragId = null; moved = false;
        markDropTarget(null);
        if (t && col && t.status !== col) { moveTo(t, col); return; }
        render();
        // 끌지 않고 눌렀으면 옮길 칸을 고르는 버튼이 뜬다 (좁은 화면에서 유일한 길)
        if (wasTap && t) openPicker(t);
      };
      el.addEventListener("pointerup", finish);
      el.addEventListener("pointercancel", finish);
    });
  }

  function fillFilter() {
    $("fWho").innerHTML = [`<option value="">담당자 전체</option>`, `<option value="none">미정</option>`]
      .concat(members.map((m) => `<option value="${m.id}">${esc(m.name)}</option>`)).join("");
  }

  (async function init() {
    ctx = await App.boot({ active: "todos", onTheme: () => render() });
    if (!ctx) return;
    members = await api.get(`/api/teams/${ctx.team.id}/members`);
    fillFilter();
    $("tabMine").onclick = () => { mine = true; filter = ""; $("fWho").value = ""; load(); };
    $("tabAll").onclick = () => { mine = false; load(); };
    $("fWho").onchange = () => { filter = $("fWho").value; render();   /* 화면에서 거름. 서버를 다시 부르지 않음 */ };
    await load();
  })();
})();
