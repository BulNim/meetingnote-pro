// MeetingNote Pro 공통 API 래퍼 - 모든 화면이 같은 fetch · 토큰 · 오류 처리를 쓴다
// JWT 는 localStorage("token"), 소속 팀 id 는 localStorage("teamId")
window.API = (() => {
  const TOKEN = "token", TEAM = "teamId";

  const clear = () => { localStorage.removeItem(TOKEN); localStorage.removeItem(TEAM); };

  const goLogin = (expired) => { location.href = "login.html" + (expired ? "?expired=1" : ""); };

  // 401 TOKEN_EXPIRED 는 어느 화면에서든 토큰을 지우고 로그인 화면으로 보낸다 (스토리보드 B-03)
  async function call(method, path, body, form) {
    const headers = {};
    const token = localStorage.getItem(TOKEN);
    if (token) headers["Authorization"] = "Bearer " + token;
    let payload;
    if (form) payload = form;
    else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
    let res;
    try {
      res = await fetch(path, { method, headers, body: payload });
    } catch (e) {
      return { ok: false, status: 0, data: { code: "NETWORK", msg: "서버에 연결할 수 없습니다" } };
    }
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
    if (res.status === 401 && data && data.code === "TOKEN_EXPIRED" && !location.pathname.endsWith("login.html")) {
      clear(); goLogin(true);
      // 이동하는 동안 호출한 쪽 코드가 이어지면 다른 화면으로 덮어쓰므로 여기서 멈춘다
      return new Promise(() => {});
    }
    return { ok: res.ok, status: res.status, data };
  }

  return {
    get: (p) => call("GET", p),
    post: (p, b) => call("POST", p, b === undefined ? {} : b),
    put: (p, b) => call("PUT", p, b === undefined ? {} : b),
    del: (p) => call("DELETE", p),
    upload: (file) => { const f = new FormData(); f.append("file", file); return call("POST", "/api/upload", undefined, f); },
    token: () => localStorage.getItem(TOKEN),
    setToken: (t) => localStorage.setItem(TOKEN, t),
    // 소속 팀 {id, name, role} 은 로그인 직후 GET /api/teams 로 확인해 저장해 두고(login.html), 다른 화면은 저장값을 쓴다
    cachedTeam() { try { return JSON.parse(localStorage.getItem(TEAM)); } catch (e) { return null; } },
    setTeam(team) { localStorage.setItem(TEAM, JSON.stringify({ id: team.id, name: team.name, role: team.role })); },
    // 사용자 id 는 JWT 의 sub 에 있다. 서버를 다시 부르지 않고 토큰에서 읽는다
    userId() {
      try {
        const body = localStorage.getItem(TOKEN).split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
        return +JSON.parse(atob(body)).sub;
      } catch (e) { return null; }
    },
    clear,
    // 로그인이 필요한 화면의 첫 줄에서 부른다. 토큰이 없으면 로그인 화면으로 보낸다
    requireLogin() { if (!localStorage.getItem(TOKEN)) { goLogin(false); return false; } return true; },
    // 소속 팀을 서버에서 다시 확인해 저장한다. 팀이 없으면 null
    async resolveTeam() {
      const r = await call("GET", "/api/teams");
      if (r.ok && r.data.length) { this.setTeam(r.data[0]); return r.data[0]; }
      localStorage.removeItem(TEAM);
      return null;
    },
    // 저장된 팀을 쓰고, 없을 때만 서버에 묻는다. 그래도 없으면 팀 설정 화면으로 보낸다
    async requireTeam() {
      const team = this.cachedTeam() || await this.resolveTeam();
      if (!team) location.href = "team.html";
      return team;
    },
    // 저장은 UTC ISO 8601, 화면 표시는 현지 시간 (정의서 9절 시각 기준)
    local(iso) {
      if (!iso) return "";
      const d = new Date(iso), p = (n) => String(n).padStart(2, "0");
      return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
    },
    esc: (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]))
  };
})();
