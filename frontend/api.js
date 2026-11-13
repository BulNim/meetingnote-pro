// MeetingNote Pro - API 호출 공통
// 토큰 헤더 · 401 TOKEN_EXPIRED 처리 · {code, msg} 해석 · 화면 진입 검사 · 시각 표시
(function () {
  const TOKEN = "token";

  class ApiError extends Error {
    constructor(status, code, msg) {
      super(msg || code);
      this.status = status;
      this.code = code;
      this.msg = msg || "";
    }
  }

  const getToken = () => localStorage.getItem(TOKEN);
  const setToken = (t) => localStorage.setItem(TOKEN, t);
  const clearToken = () => localStorage.removeItem(TOKEN);

  // 24h 지난 토큰 - 토큰을 지우고 로그인 화면으로 (B-03)
  function expired() {
    clearToken();
    sessionStorage.setItem("expired", "1");
    location.href = "/login.html";
  }

  async function parse(res) {
    if (res.status === 204) return null;
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (_) { data = null; }
    if (!res.ok) {
      const code = (data && data.code) || "NOT_FOUND";
      const msg = (data && data.msg) || res.statusText;
      if (res.status === 401 && code === "TOKEN_EXPIRED" && getToken()) expired();
      throw new ApiError(res.status, code, msg);
    }
    return data;
  }

  async function request(method, path, body) {
    const headers = {};
    const t = getToken();
    if (t) headers["Authorization"] = "Bearer " + t;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    let res;
    try {
      res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch (e) {
      throw new ApiError(0, "NETWORK", "서버에 연결할 수 없음");
    }
    return parse(res);
  }

  // 녹취 업로드 - 올리는 동안은 실제 진행률, 받아쓰는 동안은 95% 까지 천천히 (onProgress(pct, phase))
  function upload(file, onProgress) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      const fd = new FormData();
      fd.append("file", file);
      let creep = null, pct = 0;
      const report = (p, phase) => { pct = p; if (onProgress) onProgress(Math.round(p), phase); };
      xhr.open("POST", "/api/upload");
      const t = getToken();
      if (t) xhr.setRequestHeader("Authorization", "Bearer " + t);
      xhr.upload.onprogress = (e) => { if (e.lengthComputable) report((e.loaded / e.total) * 30, "upload"); };
      xhr.upload.onload = () => {
        report(30, "transcribe");
        creep = setInterval(() => report(pct + (95 - pct) * 0.04, "transcribe"), 400);
      };
      xhr.onload = async () => {
        clearInterval(creep);
        const res = new Response(xhr.responseText, { status: xhr.status });
        try { const data = await parse(res); report(100, "done"); resolve(data); }
        catch (e) { reject(e); }
      };
      xhr.onerror = () => { clearInterval(creep); reject(new ApiError(0, "NETWORK", "서버에 연결할 수 없음")); };
      xhr.send(fd);
    });
  }

  window.ApiError = ApiError;
  window.API = {
    get: (p) => request("GET", p),
    post: (p, b) => request("POST", p, b === undefined ? {} : b),
    put: (p, b) => request("PUT", p, b === undefined ? {} : b),
    del: (p) => request("DELETE", p),
    upload,
    getToken, setToken, clearToken,
  };

  // 화면 진입 검사 - 토큰 없으면 로그인, needTeam 이면 팀 없을 때 팀 설정 화면으로
  // 반환: { user: {id,name,email,role}, team: {id,name,invite_code,role,member_count} | null }
  window.boot = async function ({ needTeam = true } = {}) {
    if (!getToken()) { location.href = "/login.html"; return new Promise(() => {}); }
    const [user, teams] = await Promise.all([API.get("/api/auth/me"), API.get("/api/teams")]);
    const team = teams[0] || null;
    if (needTeam && !team) { location.href = "/team.html"; return new Promise(() => {}); }
    return { user, team };
  };

  window.logout = async function () {
    try { await API.post("/api/auth/logout"); } catch (_) { /* 서버 상태와 상관없이 지움 */ }
    clearToken();
    location.href = "/login.html";
  };

  // HTML 이스케이프 - 서버 값은 항상 이걸 거쳐 innerHTML 에 넣는다
  window.esc = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

  const pad = (n) => String(n).padStart(2, "0");

  // 서버 시각(UTC ISO) -> 현지 "2026-09-24 14:00"
  window.fmtTime = function (iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  // 활동 · 댓글용 - "방금" · "오늘 14:12" · "어제 11:02" · "9월 12일"
  window.relTime = function (iso) {
    if (!iso) return "";
    const d = new Date(iso), now = new Date();
    if (now - d < 60 * 1000) return "방금";
    const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((day(now) - day(d)) / 86400000);
    const hm = `${pad(d.getHours())}:${pad(d.getMinutes())}`;
    if (diff === 0) return "오늘 " + hm;
    if (diff === 1) return "어제 " + hm;
    if (d.getFullYear() === now.getFullYear()) return `${d.getMonth() + 1}월 ${d.getDate()}일`;
    return `${d.getFullYear()}년 ${d.getMonth() + 1}월 ${d.getDate()}일`;
  };

  // datetime-local 값(현지) <-> UTC ISO
  window.localToIso = (v) => (v ? new Date(v).toISOString() : "");
  window.isoToLocalInput = function (iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  };

  // ── 할 일 기한 (modify-todo-due-date) ──
  // due_date(YYYY-MM-DD) 는 서버가 회의 날짜 기준으로 환산한 날짜. 못 정하면 null 이고 원래 글자 due_text 만 있다
  const WEEK = "일월화수목금토";
  const todayStr = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`; };
  // "11-20 (금)" - 날짜가 없으면 빈 문자열
  window.dueDateText = function (t) {
    if (!t || !t.due_date) return "";
    const [y, m, d] = t.due_date.split("-").map(Number);
    return `${pad(m)}-${pad(d)} (${WEEK[new Date(y, m - 1, d).getDay()]})`;
  };
  // 기한 지남 - 날짜가 오늘보다 앞이고 완료가 아님. 날짜가 없으면 판정하지 않음
  window.isOverdue = (t) => !!(t && t.due_date && t.status !== "DONE" && t.due_date < todayStr());
  // 기한 배지 안쪽 HTML - 날짜 + 원래 글자, 날짜가 없으면 글자만 (둘 다 없으면 「미정」)
  window.dueHtml = function (t) {
    const dt = window.dueDateText(t);
    if (!dt) return window.esc(t.due_text || "미정");
    return window.esc(dt) + (t.due_text ? `<span class="font-normal text-ink-3 dark:text-dim"> · ${window.esc(t.due_text)}</span>` : "");
  };

  // 팔레트 순환 - 회의록 카드 띠 (목록 순서대로)
  window.CYCLE = ["blue", "green", "orange", "purple", "red"];
  // 활동 kind -> 띠 색
  window.KIND_COLOR = { meeting_add: "blue", todo_assign: "orange", todo_done: "green", comment_add: "purple", member_join: "purple" };
})();
