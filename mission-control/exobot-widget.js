/* Exobot global chat widget — persistent across page navigation.
 * Loaded on every Mission Control page (auto-injected by server.js before </body>).
 * History + in-flight questions live in localStorage, and answers are fetched by
 * polling an async job id — so you can ask on one page, navigate away, and the
 * reply still lands in the same conversation on whatever page you're on. */
(function () {
  if (window.__mcExobot) return; window.__mcExobot = true;
  var HIST = 'mc_exobot_hist_v2', PEND = 'mc_exobot_pending_v2', OPENK = 'mc_exobot_open_v2';
  function load(k, d) { try { return JSON.parse(localStorage.getItem(k)) || d; } catch (e) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  var hist = load(HIST, []);        // [{who:'me'|'bot', text}]
  var pending = load(PEND, []);     // [{jobId, q}]

  var css = '#exobotFab{position:fixed;bottom:22px;right:22px;width:54px;height:54px;border-radius:50%;'
    + 'background:linear-gradient(135deg,#2563eb,#1e40af);color:#fff;font-size:24px;display:flex;'
    + 'align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.4);z-index:80}'
    + '#exobotFab:hover{transform:scale(1.06)}'
    + '#ecBadge{position:absolute;top:-2px;right:-2px;min-width:16px;height:16px;border-radius:8px;background:#ef4444;'
    + 'color:#fff;font-size:10px;line-height:16px;text-align:center;padding:0 4px;display:none}'
    + '#exobotChat{position:fixed;bottom:22px;right:22px;width:380px;max-width:94vw;height:520px;max-height:80vh;'
    + 'background:var(--panel,#0f1e38);border:1px solid var(--border,#2a3f63);border-radius:14px;'
    + 'box-shadow:0 10px 40px rgba(0,0,0,.5);z-index:81;display:none;flex-direction:column;overflow:hidden}'
    + '#exobotChat.open{display:flex}'
    + '.ec-head{display:flex;justify-content:space-between;align-items:center;padding:12px 14px;'
    + 'background:linear-gradient(135deg,#1e3a8a,#0f1e38);border-bottom:1px solid var(--border,#2a3f63);font-weight:600;font-size:14px;color:var(--text,#e8edf5)}'
    + '.ec-sub{color:var(--text2,#8aa0bd);font-weight:400;font-size:10px;display:block}'
    + '.ec-x{background:none;border:none;color:var(--text2,#8aa0bd);font-size:16px;cursor:pointer}'
    + '.ec-body{flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px}'
    + '.ec-msg{max-width:85%;padding:8px 11px;border-radius:11px;font-size:13px;line-height:1.4;white-space:pre-wrap;word-wrap:break-word}'
    + '.ec-me{align-self:flex-end;background:#2563eb;color:#fff;border-bottom-right-radius:3px}'
    + '.ec-bot{align-self:flex-start;background:#16233d;color:var(--text,#e8edf5);border:1px solid var(--border,#2a3f63);border-bottom-left-radius:3px}'
    + '.ec-thinking{color:var(--text2,#8aa0bd);font-style:italic}'
    + '.ec-foot{display:flex;gap:8px;padding:10px;border-top:1px solid var(--border,#2a3f63)}'
    + '.ec-foot textarea{flex:1;resize:none;background:#0a1830;border:1px solid var(--border,#2a3f63);border-radius:9px;'
    + 'color:var(--text,#e8edf5);padding:9px 11px;font-size:13px;font-family:inherit;outline:none;max-height:100px}'
    + '.ec-foot textarea:focus{border-color:#60a5fa}'
    + '#ecSendBtn{background:#2563eb;color:#fff;border:none;border-radius:9px;width:42px;font-size:16px;cursor:pointer}'
    + '#ecSendBtn:disabled{opacity:.5;cursor:default}';

  function boot() {
    if (document.getElementById('exobotFab')) return; // never double-inject
    var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    var wrap = document.createElement('div');
    wrap.innerHTML =
      '<div id="exobotFab" title="Ask Exobot">💬<span id="ecBadge"></span></div>'
      + '<div id="exobotChat">'
      + '<div class="ec-head"><span>🤖 Ask Exobot <span class="ec-sub">private · follows you across pages · ask several at once</span></span>'
      + '<span><button class="ec-x" id="ecClear" title="Clear conversation">🗑</button>'
      + '<button class="ec-x" id="ecClose">✕</button></span></div>'
      + '<div class="ec-body" id="ecBody"></div>'
      + '<div class="ec-foot">'
      + '<textarea id="ecInput" rows="1" placeholder="Ask Exobot…  (Enter to send, Shift+Enter for newline)"></textarea>'
      + '<button id="ecSendBtn">➤</button></div></div>';
    document.body.appendChild(wrap);
    document.getElementById('exobotFab').addEventListener('click', function () { toggle(true); });
    document.getElementById('ecClose').addEventListener('click', function () { toggle(false); });
    document.getElementById('ecClear').addEventListener('click', clearConv);
    document.getElementById('ecSendBtn').addEventListener('click', send);
    document.getElementById('ecInput').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    render();
    if (load(OPENK, false)) toggle(true, true);
    setInterval(poll, 3000); poll();
  }

  function badge(n) {
    var b = document.getElementById('ecBadge'); if (!b) return;
    if (n > 0) { b.textContent = n; b.style.display = ''; } else { b.style.display = 'none'; }
  }
  var unread = 0;
  function isOpen() { var p = document.getElementById('exobotChat'); return p && p.classList.contains('open'); }
  function toggle(open, silent) {
    var p = document.getElementById('exobotChat'), fab = document.getElementById('exobotFab');
    if (open) { p.classList.add('open'); fab.style.display = 'none'; unread = 0; badge(0);
      if (!silent) document.getElementById('ecInput').focus();
      if (!hist.length && !pending.length) greet();
      var b = document.getElementById('ecBody'); if (b) b.scrollTop = b.scrollHeight;
      save(OPENK, true);
    } else { p.classList.remove('open'); fab.style.display = ''; save(OPENK, false); }
  }
  function pushHist(m) { hist.push(m); if (hist.length > 120) hist = hist.slice(-120); save(HIST, hist); }
  function clearConv() { hist = []; pending = []; save(HIST, hist); save(PEND, pending); unread = 0; badge(0); render(); }
  function greet() {
    pushHist({ who: 'bot', text: "Hi — I'm Exobot. Ask me anything, or tell me to add a task, run DD, find a document, etc. This conversation follows you across pages, and you can fire several questions at once — a new one runs in parallel while another is still working." });
    render();
  }
  function bubble(who, text, thinking) {
    var d = document.createElement('div'); d.className = 'ec-msg ec-' + who + (thinking ? ' ec-thinking' : '');
    d.textContent = text; return d;
  }
  function render() {
    var b = document.getElementById('ecBody'); if (!b) return;
    b.innerHTML = '';
    hist.forEach(function (m) { b.appendChild(bubble(m.who, m.text)); });
    pending.forEach(function (p) { b.appendChild(bubble('bot', '…working: ' + (p.q || '').slice(0, 46), true)); });
    b.scrollTop = b.scrollHeight;
  }
  function send() {
    var inp = document.getElementById('ecInput'); var msg = (inp.value || '').trim(); if (!msg) return;
    inp.value = '';
    pushHist({ who: 'me', text: msg }); render();
    var btn = document.getElementById('ecSendBtn'); btn.disabled = true;
    fetch('/api/chat', { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: msg }) })
      .then(function (r) {
        btn.disabled = false;
        if (r.status === 401) { pushHist({ who: 'bot', text: 'Session expired — reload and log in.' }); render(); return; }
        return r.json().then(function (j) {
          if (r.status === 429) { pushHist({ who: 'bot', text: (j && j.error) || 'Too many questions running at once — let one finish.' }); render(); return; }
          if (j && j.jobId) { pending.push({ jobId: j.jobId, q: msg }); save(PEND, pending); render(); poll(); }
          else { pushHist({ who: 'bot', text: (j && (j.reply || j.error)) || 'No reply.' }); render(); }
        });
      })
      .catch(function (e) { btn.disabled = false; pushHist({ who: 'bot', text: 'Error: ' + e.message }); render(); });
    var inp2 = document.getElementById('ecInput'); if (inp2) inp2.focus();
  }
  function poll() {
    if (!pending.length) return;
    pending.slice().forEach(function (p) {
      fetch('/api/chat/result?id=' + encodeURIComponent(p.jobId), { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) {
          if (!j || j.status === 'pending') return;
          // done or error — resolve this job
          pending = pending.filter(function (x) { return x.jobId !== p.jobId; }); save(PEND, pending);
          pushHist({ who: 'bot', text: (j.reply || j.error || 'No reply.') });
          render();
          if (!isOpen()) { unread++; badge(unread); }
        }).catch(function () {});
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
