// 모든 화면이 같이 쓰는 스크립트 - API 호출 한 곳, 토큰, 머리글, 알림, 날짜 표기
// 색과 클래스는 theme.js 의 이름(UI · STRIPE · LABEL)만 쓴다
(function () {
  const TOKEN_KEY = "token";
  const EXPIRED_KEY = "mn_expired";

  // 저장소를 못 쓰는 환경(사생활 보호 창 등)에서도 화면이 죽지 않게 감싼다
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* 무시 */ } },
    del(k) { try { localStorage.removeItem(k); } catch (e) { /* 무시 */ } }
  };
  const flash = {
    get(k) { try { return sessionStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { sessionStorage.setItem(k, v); } catch (e) { /* 무시 */ } },
    del(k) { try { sessionStorage.removeItem(k); } catch (e) { /* 무시 */ } }
  };

  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  class ApiError extends Error {
    constructor(status, code, msg) {
      super(msg || code || (status === 413 ? "파일이 너무 큼" : "요청 실패"));   // 플랫폼의 413 은 JSON 이 아니다
      this.status = status;
      this.code = code;
    }
  }

  function goLogin(expired) {
    store.del(TOKEN_KEY);
    if (expired) flash.set(EXPIRED_KEY, "1");
    location.href = "login.html";
  }

  async function request(method, path, opts) {
    opts = opts || {};
    const headers = {};
    const token = store.get(TOKEN_KEY);
    if (token) headers["Authorization"] = "Bearer " + token;
    let body;
    if (opts.form) {
      body = opts.form;                    // multipart 는 브라우저가 경계 문자열을 붙인다
    } else if (opts.json !== undefined) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(opts.json);
    }
    let res;
    try {
      res = await fetch(path, { method, headers, body });
    } catch (e) {
      throw new ApiError(0, "NETWORK", "서버에 연결하지 못함");
    }
    if (res.status === 204) return null;
    let data = null;
    try { data = await res.json(); } catch (e) { data = null; }
    if (!res.ok) {
      const code = data && data.code;
      const isAuthCall = path.startsWith("/api/auth/login") || path.startsWith("/api/auth/signup");
      // 만료되었거나 토큰이 없으면 토큰을 지우고 로그인 화면으로 보낸다
      if (res.status === 401 && !isAuthCall && code !== "INVALID_CREDENTIALS") {
        goLogin(code === "TOKEN_EXPIRED");
      }
      throw new ApiError(res.status, code, data && data.msg);
    }
    return data;
  }

  const api = {
    get: (p) => request("GET", p),
    post: (p, json) => request("POST", p, { json: json === undefined ? {} : json }),
    put: (p, json) => request("PUT", p, { json: json === undefined ? {} : json }),
    del: (p) => request("DELETE", p),
    // 업로드는 진행률을 알려 주려고 XMLHttpRequest 를 쓴다 (fetch 는 보내는 쪽 진행률을 못 줌)
    upload: (p, file, onProgress) => new Promise((resolve, reject) => {
      const form = new FormData();
      form.append("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", p);
      const token = store.get(TOKEN_KEY);
      if (token) xhr.setRequestHeader("Authorization", "Bearer " + token);
      xhr.upload.onprogress = (e) => { if (onProgress && e.lengthComputable) onProgress(e.loaded / e.total); };
      xhr.onerror = () => reject(new ApiError(0, "NETWORK", "서버에 연결하지 못함"));
      xhr.onload = () => {
        let data = null;
        try { data = JSON.parse(xhr.responseText); } catch (e) { data = null; }
        if (xhr.status >= 200 && xhr.status < 300) return resolve(data);
        const code = data && data.code;
        if (xhr.status === 401) goLogin(code === "TOKEN_EXPIRED");
        reject(new ApiError(xhr.status, code, data && data.msg));
      };
      xhr.send(form);
    })
  };

  // ── 날짜 표기: 서버는 UTC, 화면은 현지 시간 ──
  const pad = (n) => String(n).padStart(2, "0");
  function fmtAt(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }
  function fmtWhen(iso) {
    if (!iso) return "";
    const d = new Date(iso), now = new Date();
    const day = (x) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
    const diff = Math.round((day(now) - day(d)) / 86400000);
    const hm = pad(d.getHours()) + ":" + pad(d.getMinutes());
    if (diff === 0) return "오늘 " + hm;
    if (diff === 1) return "어제 " + hm;
    if (d.getFullYear() === now.getFullYear()) return (d.getMonth() + 1) + "월 " + d.getDate() + "일";
    return fmtAt(iso).slice(0, 10);
  }
  function toLocalInput(iso) {
    const d = new Date(iso);
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) + "T" + pad(d.getHours()) + ":" + pad(d.getMinutes());
  }
  function fromLocalInput(value) {
    return new Date(value).toISOString();
  }

  // ── 알림: theme.js 의 notice 를 화면 아래에 잠깐 띄운다 ──
  let toastTimer = null;
  function toast(kind, title, body) {
    let box = document.getElementById("toast");
    if (!box) {
      box = document.createElement("div");
      box.id = "toast";
      box.className = "fixed bottom-4 left-4 right-4 sm:left-auto sm:w-80 z-50";
      box.setAttribute("role", "status");
      document.body.appendChild(box);
    }
    box.innerHTML = window.notice(kind, esc(title), body ? esc(body) : "");
    box.classList.remove("hidden");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => box.classList.add("hidden"), 4000);
  }

  // ── 머리글: 내비게이션 + 팀 이름 + 테마 버튼 ──
  const NAV = [
    ["meetings", "회의록", "meetings.html"],
    ["todos", "할 일", "todos.html"],
    ["team", "팀", "team.html"],
    ["profile", "내 정보", "profile.html"]
  ];
  function mountHeader(active, teamName) {
    const links = NAV.map(([key, label, href]) => key === active
      ? `<span class="${UI.navOn}">${label}</span>`
      : `<a href="${href}" class="${UI.nav}">${label}</a>`).join("");
    document.getElementById("header").innerHTML = `
      <header class="sticky top-0 z-30 bg-white dark:bg-canvas border-b border-line dark:border-edge">
        <div class="max-w-6xl mx-auto px-4 h-14 flex items-center gap-3">
          <a href="meetings.html" class="flex items-center gap-2 shrink-0">
            <div class="w-7 h-7 rounded-lg bg-ink dark:bg-fg grid place-items-center text-white dark:text-canvas font-extrabold text-sm">M</div>
            <span class="font-extrabold tracking-tight">MeetingNote</span>
          </a>
          <nav class="flex items-center gap-1 text-[13px] font-bold ml-2 min-w-0 overflow-x-auto">${links}</nav>
          <div class="ml-auto flex items-center gap-2 shrink-0">
            ${teamName ? `<span class="hidden sm:inline ${UI.meta}">${esc(teamName)}</span>` : ""}
            <div id="themeSlot">${window.THEME_BTN}</div>
          </div>
        </div>
      </header>`;
  }

  // 화면 시작: 로그인 확인 -> 소속 팀 확인 -> 머리글. 이동이 필요하면 null 을 돌려준다
  async function boot(opts) {
    opts = opts || {};
    if (!store.get(TOKEN_KEY)) { goLogin(false); return null; }
    window.initTheme(opts.onTheme);
    let me;
    try { me = await api.get("/api/auth/me"); } catch (e) { return null; }
    let team = null;
    if (me.team_id) {
      const teams = await api.get("/api/teams");
      team = teams[0] || null;
    }
    if (opts.needTeam !== false && !team) { location.href = "team.html"; return null; }
    mountHeader(opts.active, team && team.name);
    window.initTheme(opts.onTheme);   // 머리글이 만들어진 뒤 테마 버튼을 연결
    return { me, team };
  }

  window.App = {
    esc, api, ApiError, store, flash, fmtAt, fmtWhen, toLocalInput, fromLocalInput,
    toast, boot, goLogin, EXPIRED_KEY, TOKEN_KEY
  };
})();
