// 회의록 목록 + 새 회의록 (스토리보드 C-01 ~ C-11)
(function () {
  const { api, esc, fmtAt, toLocalInput, fromLocalInput, toast } = App;
  const $ = (id) => document.getElementById(id);

  const MAX_BYTES = 4400000;               // 서버와 같은 상한 (4.4MB)
  const COLORS = ["blue", "green", "orange", "purple", "red"];   // 카드 띠 색은 목록 순서대로 돌려 쓴다

  // 클래스는 theme.js 의 이름으로만 입힌다
  $("searchBox").className = UI.panel + " p-4 mb-4";
  $("q").className = "flex-1 " + UI.input;
  $("from").className = UI.input;
  $("to").className = UI.input;
  $("newBtn").className = UI.btnPrimary + " w-full whitespace-nowrap";
  $("newPanel").className = "hidden " + UI.panel + " " + STRIPE.blue + " p-5 mb-4";
  ["nTitle", "nAt", "nWho"].forEach((id) => { $(id).className = UI.input; });
  $("nBody").className = UI.textarea + " mt-3";
  $("dropSub").className = UI.meta + " mt-1";
  $("progText").className = "mt-1.5 text-[11px] font-bold " + LABEL.blue;
  $("prog").className = UI.progress;
  $("cancelBtn").className = UI.btnGhost;
  $("saveBtn").className = UI.btnPrimary;
  $("panelHelp").className = UI.meta + " mt-2.5";
  $("count").className = UI.meta;
  $("empty").className = "hidden " + UI.panel + " px-5 py-12 text-center";
  $("emptySub").className = UI.sub + " mt-1";

  const DROP_HINT = "mp3 · wav · 4.4MB 이하. 또는 아래에 메모를 붙여넣기";
  let ctx = null, busy = false, uploading = false, filterTimer = null;

  // ── 목록 ──
  function card(m, i) {
    const color = COLORS[i % COLORS.length];
    return `
      <a href="detail.html?id=${m.id}" class="block ${UI.card} ${STRIPE[color]} p-4 hover:border-ink dark:hover:border-dim transition">
        <div class="flex items-start gap-2">
          <h3 class="text-[14px] font-extrabold leading-snug flex-1">${esc(m.title)}</h3>
          <span class="${UI.chip} ${LABEL[color]} shrink-0">${m.todo_done_count}/${m.todo_total_count}</span>
        </div>
        <p class="mt-1 ${UI.meta}">${fmtAt(m.met_at)}${m.attendees ? " · " + esc(m.attendees) : ""}</p>
        <p class="mt-2 ${UI.sub} leading-relaxed line-clamp-2">${esc(m.summary)}</p>
        <div class="mt-2.5 flex gap-1.5">
          <span class="${UI.chip}">결정 ${m.decision_count}</span>
          <span class="${UI.chip}">할 일 ${m.todo_total_count}</span>
        </div>
      </a>`;
  }

  async function load() {
    const params = new URLSearchParams();
    if ($("q").value.trim()) params.set("q", $("q").value.trim());
    if ($("from").value) params.set("from", $("from").value);
    if ($("to").value) params.set("to", $("to").value);
    const qs = params.toString();
    let rows;
    try {
      rows = await api.get(`/api/teams/${ctx.team.id}/meetings${qs ? "?" + qs : ""}`);
    } catch (e) {
      toast("red", "목록을 불러오지 못함", e.message);
      return;
    }
    const searching = qs !== "";
    $("list").innerHTML = rows.map(card).join("");
    $("list").classList.toggle("hidden", rows.length === 0);
    $("count").textContent = rows.length ? rows.length + "건" : "";
    $("empty").classList.toggle("hidden", rows.length > 0);
    $("emptyTitle").textContent = searching ? "검색 결과 없음" : "아직 회의록이 없음";
    $("emptySub").textContent = searching ? "검색어를 지우면 전체 목록으로 돌아감" : "새 회의록 버튼으로 첫 회의를 올려 보기";
  }

  function scheduleLoad() {
    clearTimeout(filterTimer);
    filterTimer = setTimeout(load, 300);
  }

  // ── 새 회의록 패널 ──
  function showNotice(boxId, kind, title, body) {
    $(boxId).innerHTML = window.notice(kind, esc(title), body ? esc(body) : "");
    $(boxId).classList.remove("hidden");
  }

  function resetPanel() {
    $("newPanel").classList.add("hidden");
    ["dropErr", "saveErr", "progWrap"].forEach((id) => $(id).classList.add("hidden"));
    ["nTitle", "nAt", "nWho", "nBody", "file"].forEach((id) => { $(id).value = ""; });
    $("prog").value = 0;
    $("dropTitle").textContent = "녹취 파일을 끌어다 놓기";
    $("dropSub").textContent = DROP_HINT;
    $("saveBtn").disabled = false;
    $("saveBtn").textContent = "정리하기";
    busy = false;
    uploading = false;
  }

  function openPanel() {
    resetPanel();
    $("newPanel").classList.remove("hidden");
    $("panelHelp").textContent = "제목 · 회의 시각 · 본문이 필수. 저장하면 입력칸은 비워지고 같은 회의록이 두 번 저장되지 않음";
    $("nAt").value = toLocalInput(new Date().toISOString());
    $("nTitle").focus();
  }

  const MB = (bytes) => (bytes / 1000000).toFixed(1) + "MB";   // 상한(4,400,000 바이트)과 같은 십진수 기준

  async function pickFile(file) {
    if (!file || uploading) return;
    $("dropErr").classList.add("hidden");
    $("dropTitle").textContent = file.name;
    if (file.size > MAX_BYTES) {          // 올리기 전에 막아 쓸데없이 보내지 않게
      $("dropSub").textContent = MB(file.size);
      showNotice("dropErr", "red", "4.4MB 를 넘는 파일", "올린 파일은 " + MB(file.size));
      return;
    }
    uploading = true;
    $("progWrap").classList.remove("hidden");
    $("prog").removeAttribute("value");   // 값이 없으면 진행 막대가 계속 도는 표시가 된다
    $("progText").textContent = "올리는 중";
    $("dropSub").textContent = MB(file.size) + " · 올리는 중";
    try {
      const res = await api.upload("/api/upload", file, (ratio) => {
        $("prog").value = Math.round(ratio * 100);
        $("progText").textContent = ratio < 1 ? "올리는 중  " + Math.round(ratio * 100) + "%" : "받아쓰는 중...";
        if (ratio >= 1) $("prog").removeAttribute("value");
      });
      $("nBody").value = res.body;
      $("dropSub").textContent = MB(file.size) + " · 받아쓰기 완료";
      $("progWrap").classList.add("hidden");
      $("panelHelp").textContent = "본문이 채워짐. 정리하기를 눌러야 세 항목 구분이 돌아감";
    } catch (e) {
      $("progWrap").classList.add("hidden");
      $("dropSub").textContent = "";
      const title = { 415: "mp3 또는 wav 만 올릴 수 있음", 413: "4.4MB 를 넘는 파일", 502: "받아쓰기에 실패함" }[e.status]
        || "올리지 못함";
      showNotice("dropErr", "red", title, e.message);
    } finally {
      uploading = false;
      $("file").value = "";
    }
  }

  async function save() {
    if (busy) return;                      // 저장 중에는 버튼을 잠가 두 번 저장되지 않게
    $("saveErr").classList.add("hidden");
    const title = $("nTitle").value.trim(), at = $("nAt").value, body = $("nBody").value.trim();
    if (!title || !at || !body) {
      showNotice("saveErr", "red", "제목 · 회의 시각 · 본문이 필요함", "");
      return;
    }
    busy = true;
    $("saveBtn").disabled = true;
    $("saveBtn").textContent = "정리 중...";
    try {
      await api.post(`/api/teams/${ctx.team.id}/meetings`, {
        title, met_at: fromLocalInput(at), attendees: $("nWho").value.trim(), body
      });
      resetPanel();
      toast("green", "저장 완료", "목록 맨 위에 추가됨");
      await load();
    } catch (e) {
      busy = false;
      $("saveBtn").disabled = false;
      $("saveBtn").textContent = "정리하기";
      showNotice("saveErr", "red", "저장하지 못함", e.message);
    }
  }

  function bind() {
    $("newBtn").onclick = openPanel;
    $("cancelBtn").onclick = resetPanel;
    $("saveBtn").onclick = save;
    ["q", "from", "to"].forEach((id) => $(id).addEventListener("input", scheduleLoad));
    const zone = $("dropZone");
    zone.onclick = () => $("file").click();
    $("file").onchange = (e) => pickFile(e.target.files[0]);
    zone.ondragover = (e) => { e.preventDefault(); zone.classList.add("border-blue-dot"); };
    zone.ondragleave = () => zone.classList.remove("border-blue-dot");
    zone.ondrop = (e) => {
      e.preventDefault();
      zone.classList.remove("border-blue-dot");
      pickFile(e.dataTransfer.files[0]);
    };
  }

  (async function init() {
    ctx = await App.boot({ active: "meetings" });
    if (!ctx) return;
    $("dropSub").textContent = DROP_HINT;
    bind();
    await load();
  })();
})();
