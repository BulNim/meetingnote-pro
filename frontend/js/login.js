// 로그인 / 회원가입 화면 (스토리보드 B-01 ~ B-11)
(function () {
  const { api, esc, store, flash } = App;
  const $ = (id) => document.getElementById(id);

  document.getElementById("themeSlot").innerHTML = window.THEME_BTN;
  window.initTheme();

  // 클래스는 theme.js 의 이름으로만 입힌다
  ["email", "pw", "uname", "invite"].forEach((id) => { $(id).className = UI.input; });
  $("invite").classList.add("font-mono", "tracking-widest");
  ["errEmail", "errPw", "errName", "errInvite"].forEach((id) => { $(id).dataset.cls = UI.errText; });
  $("inviteHelp").className = UI.help;
  $("inviteHelp").textContent = "비워 두면 가입 후 팀을 새로 만듦";
  $("submit").className = "w-full " + UI.btnPrimary;

  let mode = "login";          // login | signup
  let busy = false;

  function clearMessages() {
    ["errEmail", "errPw", "errName", "errInvite", "boxErr", "boxOk", "boxExpired"].forEach((id) => {
      $(id).classList.add("hidden");
      $(id).textContent = "";
    });
    ["email", "pw", "uname", "invite"].forEach((id) => $(id).classList.remove("border-red-dot"));
  }

  function fieldError(id, input, msg) {
    const el = $(id);
    el.className = UI.errText;
    el.textContent = msg;
    el.classList.remove("hidden");
    if (input) input.classList.add("border-red-dot");
  }

  function box(which, msg) {
    const el = $(which === "err" ? "boxErr" : "boxOk");
    el.innerHTML = window.notice(which === "err" ? "red" : "green", esc(msg), "");
    el.classList.remove("hidden");
  }

  function setBusy(on) {
    busy = on;
    $("submit").disabled = on;
    $("submit").textContent = on ? "처리 중..." : (mode === "login" ? "로그인" : "가입하기");
  }

  function setMode(next) {
    mode = next;
    clearMessages();
    const signup = mode === "signup";
    $("title").textContent = signup ? "회원가입" : "로그인";
    $("sub").textContent = signup ? "이메일과 비밀번호만 있으면 시작" : "회의록과 할 일을 팀이 함께 관리";
    $("nameWrap").classList.toggle("hidden", !signup);
    $("inviteWrap").classList.toggle("hidden", !signup);
    $("pw").autocomplete = signup ? "new-password" : "current-password";
    $("submit").textContent = signup ? "가입하기" : "로그인";
    $("switch").innerHTML = signup
      ? `이미 계정이 있으신가요? <a href="#" id="toggle" class="${UI.link}">로그인</a>`
      : `계정이 없으신가요? <a href="#" id="toggle" class="${UI.link}">회원가입</a>`;
    $("toggle").onclick = (e) => { e.preventDefault(); setMode(signup ? "login" : "signup"); };
  }

  // 이메일 형식과 비밀번호 길이는 화면에서 먼저 거른다 (제출 전에는 오류를 띄우지 않음)
  function validate() {
    const email = $("email").value.trim();
    const bad = !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    if (bad) { fieldError("errEmail", $("email"), "이메일 형식이 올바르지 않음"); return false; }
    if (mode === "signup" && $("pw").value.length < 8) {
      fieldError("errPw", $("pw"), "비밀번호는 8자 이상");
      return false;
    }
    if (mode === "login" && !$("pw").value) { fieldError("errPw", $("pw"), "비밀번호를 입력해야 함"); return false; }
    if (mode === "signup" && !$("uname").value.trim()) { fieldError("errName", $("uname"), "이름을 입력해야 함"); return false; }
    return true;
  }

  async function afterLogin() {
    const me = await api.get("/api/auth/me");
    location.href = me.team_id ? "meetings.html" : "team.html";
  }

  const SERVER_MSG = {
    EMAIL_INVALID: ["errEmail", "email"],
    EMAIL_DUPLICATED: ["errEmail", "email"],
    PASSWORD_TOO_WEAK: ["errPw", "pw"]
  };

  async function submit(e) {
    e.preventDefault();
    if (busy) return;                       // 버튼을 잠가 두 번 눌리지 않게
    clearMessages();
    if (!validate()) return;
    setBusy(true);
    try {
      if (mode === "login") {
        const res = await api.post("/api/auth/login", { email: $("email").value, password: $("pw").value });
        store.set(App.TOKEN_KEY, res.token);
        box("ok", "성공. 이동 중...");
        await afterLogin();
        return;
      }
      const res = await api.post("/api/auth/signup", {
        email: $("email").value, password: $("pw").value, name: $("uname").value
      });
      store.set(App.TOKEN_KEY, res.token);
      const code = $("invite").value.trim();
      if (code) {
        try {
          await api.post("/api/teams/join", { invite_code: code });
        } catch (err) {
          // 가입은 되고 팀 합류만 실패 - 계정은 그대로 두고 팀 화면으로 보낸다 (B-11)
          fieldError("errInvite", $("invite"),
            err.code === "INVITE_NOT_FOUND" ? "초대코드를 찾을 수 없음" : (err.message || "합류하지 못함"));
          box("ok", "가입은 끝났음. 팀 화면으로 이동 중...");
          setTimeout(() => { location.href = "team.html"; }, 1800);
          return;
        }
      }
      box("ok", "성공. 이동 중...");
      await afterLogin();
    } catch (err) {
      setBusy(false);
      const target = SERVER_MSG[err.code];
      if (target) fieldError(target[0], $(target[1]), err.message);
      else box("err", err.message || "요청에 실패함");
    }
  }

  $("form").addEventListener("submit", submit);
  setMode("login");

  // 세션이 만료되어 넘어온 경우 안내 (B-03)
  if (flash.get(App.EXPIRED_KEY)) {
    flash.del(App.EXPIRED_KEY);
    $("boxExpired").innerHTML = window.notice("red", "세션 만료", "24시간이 지나 다시 로그인 필요");
    $("boxExpired").classList.remove("hidden");
  }
})();
