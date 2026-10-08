// 회의록 상세 (스토리보드 D-01 ~ D-13)
(function () {
  const { api, esc, fmtAt, fmtWhen, toLocalInput, fromLocalInput, toast } = App;
  const $ = (id) => document.getElementById(id);

  const STATUS = {
    OPEN: { label: "대기", color: "orange" },
    DOING: { label: "진행", color: "blue" },
    DONE: { label: "완료", color: "green" }
  };

  // 클래스는 theme.js 의 이름으로만 입힌다
  $("head").className = UI.panel;
  $("editPanel").className = "hidden " + UI.panel + " " + STRIPE.blue;
  $("delConfirm").className = "hidden " + UI.panel + " " + STRIPE.red;
  $("boxSummary").className = UI.panel + " " + STRIPE.blue + " p-5";
  $("boxDecisions").className = UI.panel + " " + STRIPE.green + " p-5";
  $("boxTodos").className = UI.panel + " " + STRIPE.orange + " p-5";
  $("boxBody").className = UI.panel + " p-5";
  $("boxComments").className = UI.panel + " " + STRIPE.purple + " p-5";
  $("head").classList.add("p-5");
  $("editPanel").classList.add("p-5");
  $("delConfirm").classList.add("p-5");
  $("hSummary").classList.add(...LABEL.blue.split(" "));
  $("hDecisions").classList.add(...LABEL.green.split(" "));
  $("hTodos").classList.add(...LABEL.orange.split(" "));
  $("hComments").classList.add(...LABEL.purple.split(" "));
  ["tSummary", "tDecisions", "tTodos", "cCount", "cLimit"].forEach((id) => { $(id).className = UI.meta + ($(id).id === "cLimit" ? " ml-auto" : ""); });
  $("metaLine").className = UI.meta + " mt-1";
  $("summary").classList.add(...UI.sub.split(" "));
  $("body").classList.add(...UI.sub.split(" "));
  $("bodyState").className = UI.meta + " font-bold";
  $("delSub").className = UI.sub + " mt-1";
  $("delTitle").classList.add(...LABEL.red.split(" "));
  $("editHelp").className = UI.meta + " mt-2.5";
  $("cEmpty").className = "hidden mb-3 " + UI.sub;
  ["eTitle", "eAt", "eWho", "cInput"].forEach((id) => { $(id).classList.add(...UI.input.split(" ")); });
  $("eBody").className = UI.textarea;
  ["editBtn", "editCancel", "delNo"].forEach((id) => { $(id).className = UI.btnGhost; });
  $("delBtn").className = UI.btnGhost + " " + LABEL.red;
  $("delYes").className = UI.btnDanger;
  ["editSave", "cBtn"].forEach((id) => { $(id).className = UI.btnPrimary; });

  const id = new URLSearchParams(location.search).get("id");
  let ctx = null, meeting = null, members = [], comments = [], saving = false;

  function showMissing() {
    $("content").classList.add("hidden");
    $("missing").innerHTML = window.notice("red", "404 없는 회의록", "목록으로 보냄");
    $("missing").classList.remove("hidden");
    setTimeout(() => { location.href = "meetings.html"; }, 1800);
  }

  // ── 그리기 ──
  function renderHead() {
    $("title").textContent = meeting.title;
    $("metaLine").textContent = fmtAt(meeting.met_at) + (meeting.attendees ? "  ·  " + meeting.attendees : "");
    $("actions").classList.toggle("hidden", !meeting.can_edit);
    $("actions").classList.toggle("flex", meeting.can_edit);
  }

  function renderSummary() {
    $("summary").textContent = meeting.summary || "요약이 없음";
  }

  function renderDecisions() {
    const lines = meeting.decisions.split("\n").map((s) => s.trim()).filter(Boolean);
    $("decisions").innerHTML = lines.length
      ? lines.map((t, i) => `<li class="flex gap-2"><span class="${LABEL.green} font-bold shrink-0">${i + 1}</span><span>${esc(t)}</span></li>`).join("")
      : `<li class="${UI.meta}">합의가 끝난 항목 없음  -  논의만 하고 정하지 않은 것은 넣지 않음</li>`;
  }

  function assigneeSelect(todo) {
    const opts = [`<option value="">미정</option>`]
      .concat(members.map((m) => `<option value="${m.id}" ${m.id === todo.assignee_id ? "selected" : ""}>${esc(m.name)}</option>`));
    return `<select data-todo="${todo.id}" class="assign ${UI.select}" aria-label="담당자">${opts.join("")}</select>`;
  }

  function renderTodos() {
    const rows = meeting.todos;
    $("todos").innerHTML = rows.length ? rows.map((t) => {
      const st = STATUS[t.status];
      return `
      <li class="${UI.card} p-3">
        <p class="text-[13px] font-bold leading-snug">${esc(t.what)}</p>
        <div class="mt-2">${assigneeSelect(t)}</div>
        <div class="mt-2 flex items-center gap-1.5">
          <span class="${UI.chip}">${esc(t.due_text)}</span>
          <span class="${UI.chip} ${LABEL[st.color]} ml-auto">${st.label}</span>
        </div>
      </li>`;
    }).join("") : `<li class="${UI.meta}">담당자와 기한이 드러난 항목 없음</li>`;
    document.querySelectorAll("select.assign").forEach((sel) => {
      sel.onchange = () => assign(+sel.dataset.todo, sel.value === "" ? null : +sel.value);
    });
  }

  function renderComments() {
    $("comments").innerHTML = comments.map((c) => `
      <li class="${UI.card} px-3.5 py-2.5">
        <p class="text-[13px]"><span class="font-bold">${esc(c.user_name)}</span>  ${esc(c.content)}</p>
        <p class="${UI.meta} mt-0.5">${fmtWhen(c.created_at)}
          ${c.can_delete ? `<button type="button" data-del-c="${c.id}" class="${UI.chipBtn} ${LABEL.red} ml-2">삭제</button>` : ""}</p>
      </li>`).join("");
    $("comments").classList.toggle("hidden", comments.length === 0);
    $("cEmpty").classList.toggle("hidden", comments.length > 0);
    $("cCount").textContent = comments.length ? comments.length + "건" : "";
    document.querySelectorAll("[data-del-c]").forEach((b) => { b.onclick = () => removeComment(+b.dataset.delC); });
  }

  function renderAll() {
    renderHead(); renderSummary(); renderDecisions(); renderTodos();
    $("body").textContent = meeting.body;
  }

  // ── 동작 ──
  async function assign(todoId, assigneeId) {
    try {
      const row = await api.put(`/api/todos/${todoId}`, { assignee_id: assigneeId });
      const t = meeting.todos.find((x) => x.id === todoId);
      if (t) { t.assignee_id = row.assignee_id; t.assignee_name = row.assignee_name; }
      toast("green", "담당자를 바꿈", row.assignee_name ? row.assignee_name + "에게 배정" : "담당자 미정");
    } catch (e) {
      toast("red", "담당자를 바꾸지 못함", e.message);
    }
    renderTodos();
  }

  async function addComment() {
    const text = $("cInput").value.trim();
    $("cErr").classList.add("hidden");
    if (!text) return;
    $("cBtn").disabled = true;
    try {
      await api.post(`/api/meetings/${id}/comments`, { content: text });
      $("cInput").value = "";
      comments = await api.get(`/api/meetings/${id}/comments`);
      renderComments();
      toast("green", "댓글 등록", "활동 기록에도 남음");
    } catch (e) {
      $("cErr").innerHTML = window.notice("red", "댓글을 등록하지 못함", esc(e.message));
      $("cErr").classList.remove("hidden");
    } finally {
      $("cBtn").disabled = false;
    }
  }

  async function removeComment(commentId) {
    try {
      await api.del(`/api/comments/${commentId}`);
      comments = comments.filter((c) => c.id !== commentId);
      renderComments();
    } catch (e) {
      toast("red", "댓글을 지우지 못함", e.message);
    }
  }

  function openEdit() {
    $("eTitle").value = meeting.title;
    $("eAt").value = toLocalInput(meeting.met_at);
    $("eWho").value = meeting.attendees;
    $("eBody").value = meeting.body;
    $("editErr").classList.add("hidden");
    $("editHelp").textContent = "본문을 고쳐도 받아쓰기와 요약 · 결정사항 · 할 일은 다시 만들지 않음";
    $("editPanel").classList.remove("hidden");
    $("delConfirm").classList.add("hidden");
  }

  async function saveEdit() {
    if (saving) return;
    const title = $("eTitle").value.trim(), body = $("eBody").value.trim();
    if (!title || !$("eAt").value || !body) {
      $("editErr").innerHTML = window.notice("red", "제목 · 회의 시각 · 본문이 필요함", "");
      $("editErr").classList.remove("hidden");
      return;
    }
    saving = true;
    $("editSave").disabled = true;
    try {
      meeting = await api.put(`/api/meetings/${id}`, {
        title, met_at: fromLocalInput($("eAt").value), attendees: $("eWho").value.trim(), body
      });
      $("editPanel").classList.add("hidden");
      renderAll();
      toast("green", "수정함", "");
    } catch (e) {
      $("editErr").innerHTML = window.notice("red", "수정하지 못함", esc(e.message));
      $("editErr").classList.remove("hidden");
    } finally {
      saving = false;
      $("editSave").disabled = false;
    }
  }

  async function remove() {
    $("delYes").disabled = true;
    try {
      await api.del(`/api/meetings/${id}`);
      location.href = "meetings.html";
    } catch (e) {
      $("delYes").disabled = false;
      toast("red", "삭제하지 못함", e.message);
    }
  }

  function bind() {
    $("editBtn").onclick = openEdit;
    $("editCancel").onclick = () => $("editPanel").classList.add("hidden");
    $("editSave").onclick = saveEdit;
    $("delBtn").onclick = () => {
      $("delSub").textContent = `딸린 할 일 ${meeting.todos.length}건도 함께 사라짐. 되돌릴 수 없음`;
      $("delConfirm").classList.remove("hidden");
      $("editPanel").classList.add("hidden");
    };
    $("delNo").onclick = () => $("delConfirm").classList.add("hidden");
    $("delYes").onclick = remove;
    $("bodyToggle").onclick = () => {
      const hidden = $("body").classList.toggle("hidden");
      $("bodyState").textContent = hidden ? "펼치기" : "접기";
    };
    $("cBtn").onclick = addComment;
    $("cInput").addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); addComment(); } });
  }

  (async function init() {
    ctx = await App.boot({ active: "meetings" });
    if (!ctx) return;
    if (!id) { showMissing(); return; }
    try {
      [meeting, members, comments] = await Promise.all([
        api.get(`/api/meetings/${id}`),
        api.get(`/api/teams/${ctx.team.id}/members`),
        api.get(`/api/meetings/${id}/comments`)
      ]);
    } catch (e) {
      if (e.code === "MEETING_NOT_FOUND" || e.status === 404) { showMissing(); return; }
      toast("red", "불러오지 못함", e.message);
      return;
    }
    bind();
    renderAll();
    renderComments();
  })();
})();
