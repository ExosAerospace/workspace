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
  var pending = load(PEND, []);     // [{jobId, q, ts}]
  // A pending job is only "in flight" for so long. If the server forgets it
  // (restart, lost job) the result endpoint 404s forever — without these caps a
  // '…working' bubble would stick permanently. GRACE tolerates transient errors;
  // TTL is the hard ceiling after which we give up and clear the bubble.
  var PEND_GRACE = 90 * 1000, PEND_TTL = 10 * 60 * 1000;
  function nowMs() { return Date.now(); }
  function prunePending() {
    var n = nowMs(), changed = false;
    pending = pending.filter(function (p) {
      if (!p.ts || (n - p.ts) > PEND_TTL) { changed = true; return false; }
      return true;
    });
    if (changed) save(PEND, pending);
  }
  prunePending();  // drop any stale/legacy '…working' jobs left over from a prior session
  var attachments = [];             // in-memory only: [{name, data(dataURL), size}] for the next send

  var css = '#exobotFab{position:fixed;bottom:22px;right:22px;width:54px;height:54px;border-radius:50%;'
    + 'background:linear-gradient(135deg,#2563eb,#1e40af);color:#fff;font-size:24px;display:flex;'
    + 'align-items:center;justify-content:center;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.4);z-index:1002}'
    + '#exobotFab:hover{transform:scale(1.06)}'
    + '#ecBadge{position:absolute;top:-2px;right:-2px;min-width:16px;height:16px;border-radius:8px;background:#ef4444;'
    + 'color:#fff;font-size:10px;line-height:16px;text-align:center;padding:0 4px;display:none}'
    + '#exobotChat{position:fixed;bottom:22px;right:22px;width:380px;max-width:94vw;height:520px;max-height:80vh;'
    + 'background:var(--panel,#0f1e38);border:1px solid var(--border,#2a3f63);border-radius:14px;'
    + 'box-shadow:0 10px 40px rgba(0,0,0,.5);z-index:1003;display:none;flex-direction:column;overflow:hidden}'
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
    + 'color:var(--text,#e8edf5);padding:9px 11px;font-size:13px;font-family:inherit;outline:none;min-height:96px;max-height:160px}'
    + '.ec-foot textarea:focus{border-color:#60a5fa}'
    + '#ecSendBtn{background:#2563eb;color:#fff;border:none;border-radius:9px;width:42px;font-size:16px;cursor:pointer}'
    + '#ecSendBtn:disabled{opacity:.5;cursor:default}'
    + '.ec-attach{background:#16233d;color:var(--text2,#c8d6e5);border:1px solid var(--border,#2a3f63);border-radius:9px;width:40px;font-size:16px;cursor:pointer}'
    + '.ec-attach:hover{color:#fff;border-color:#60a5fa}'
    + '.ec-att{display:none;flex-wrap:wrap;gap:6px;padding:8px 10px 0}'
    + '.ec-att.show{display:flex}'
    + '.ec-chip{display:flex;align-items:center;gap:6px;background:#16233d;border:1px solid var(--border,#2a3f63);border-radius:8px;padding:3px 8px;font-size:11px;color:#c8d6e5;max-width:200px}'
    + '.ec-chip span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}'
    + '.ec-chip b{cursor:pointer;color:#ef4444;font-weight:700;font-size:12px}'
    + '#exobotChat.ec-drag{outline:2px dashed #60a5fa;outline-offset:-6px}'
    + '.ec-help{background:none;border:none;color:var(--text2,#8aa0bd);font-size:14px;font-weight:700;cursor:pointer;line-height:1}'
    + '.ec-help:hover{color:#fff}'
    + '#ecHelpPop{position:absolute;top:46px;right:10px;width:300px;max-width:90%;background:#0f1e38;'
    + 'border:1px solid var(--border,#2a3f63);border-radius:10px;padding:12px 14px;box-shadow:0 10px 28px rgba(0,0,0,.5);z-index:90;display:none}'
    + '#ecHelpPop.show{display:block}'
    + '#ecHelpPop h4{font-size:11px;color:#60a5fa;margin:0 0 8px;text-transform:uppercase;letter-spacing:.04em}'
    + '#ecHelpPop .row{padding:3px 0;font-size:12px;line-height:1.45;color:#c8d6e5}'
    + '#ecHelpPop code{background:#162a4a;color:#ffb27a;padding:1px 5px;border-radius:4px;font-size:11px;white-space:nowrap}'
    + '#ecHelpPop .muted{color:#7a8aa0;font-size:10.5px;margin-top:8px;border-top:1px solid rgba(255,255,255,.06);padding-top:7px}'
    // When a task detail drawer (660px, right-anchored) is open, slide the launcher/chat
    // left of it on wide screens so both stay visible and the drawer's own buttons aren't covered.
    + '@media(min-width:1120px){#exobotFab.mc-task-open{right:700px}#exobotChat.mc-task-open{right:700px}}';

  function boot() {
    if (document.getElementById('exobotFab')) return; // never double-inject
    var st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);
    var wrap = document.createElement('div');
    wrap.innerHTML =
      '<div id="exobotFab" title="Ask Exobot">💬<span id="ecBadge"></span></div>'
      + '<div id="exobotChat">'
      + '<div class="ec-head"><span>🤖 Ask Exobot <span class="ec-sub">private · follows you across pages · ask several at once</span></span>'
      + '<span><button class="ec-help" id="ecHelp" title="What can I ask?">?</button>'
      + '<button class="ec-x" id="ecClear" title="Clear conversation">🗑</button>'
      + '<button class="ec-x" id="ecClose">✕</button></span></div>'
      + '<div id="ecHelpPop">'
      + '<h4>What you can ask</h4>'
      + '<div class="row"><b>Ask anything</b> — or tell me to act: <code>add a task</code>, <code>run DD on [company]</code>, <code>find the [doc]</code>, <code>draft an email to…</code></div>'
      + '<div class="row"><b>Follows you across pages</b> — ask here, navigate away, the reply lands back in this chat.</div>'
      + '<div class="row"><b>Ask several at once</b> — a new question runs in parallel while another is still working.</div>'
      + '<div class="row"><b>Attach documents</b> — click <code>📎</code>, paste, or drag &amp; drop a file (PDF, Word, Excel, image…) and ask about it.</div>'
      + '<div class="muted">Private to you. History is kept on this device — 🗑 clears it.</div>'
      + '</div>'
      + '<div class="ec-body" id="ecBody"></div>'
      + '<div class="ec-att" id="ecAtt"></div>'
      + '<div class="ec-foot">'
      + '<input type="file" id="ecFile" multiple style="display:none">'
      + '<button id="ecAttachBtn" class="ec-attach" title="Attach documents (or paste / drag &amp; drop)">📎</button>'
      + '<textarea id="ecInput" rows="5" placeholder="Ask Exobot…  (Enter to send · 📎 or paste/drop a document)"></textarea>'
      + '<button id="ecSendBtn">➤</button></div></div>';
    document.body.appendChild(wrap);
    document.getElementById('exobotFab').addEventListener('click', function () { toggle(true); });
    document.getElementById('ecClose').addEventListener('click', function () { toggle(false); });
    document.getElementById('ecHelp').addEventListener('click', function (e) {
      e.stopPropagation(); document.getElementById('ecHelpPop').classList.toggle('show');
    });
    document.addEventListener('click', function (e) {
      var pop = document.getElementById('ecHelpPop');
      if (pop && pop.classList.contains('show') && !pop.contains(e.target)
          && e.target.id !== 'ecHelp') pop.classList.remove('show');
    });
    document.getElementById('ecClear').addEventListener('click', clearConv);
    document.getElementById('ecSendBtn').addEventListener('click', send);
    document.getElementById('ecInput').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });
    // Attach documents: 📎 button, paste (files/screenshots), and drag & drop onto the panel.
    document.getElementById('ecAttachBtn').addEventListener('click', function () { document.getElementById('ecFile').click(); });
    document.getElementById('ecFile').addEventListener('change', function (e) { addFiles(e.target.files); e.target.value = ''; });
    document.getElementById('ecInput').addEventListener('paste', function (e) {
      var items = (e.clipboardData || {}).items || [], files = [];
      for (var i = 0; i < items.length; i++) { if (items[i].kind === 'file') { var f = items[i].getAsFile(); if (f) files.push(f); } }
      if (files.length) { e.preventDefault(); addFiles(files); }   // let plain text paste through normally
    });
    var chat = document.getElementById('exobotChat');
    chat.addEventListener('dragover', function (e) { e.preventDefault(); chat.classList.add('ec-drag'); });
    chat.addEventListener('dragleave', function (e) { if (!chat.contains(e.relatedTarget)) chat.classList.remove('ec-drag'); });
    chat.addEventListener('drop', function (e) {
      e.preventDefault(); chat.classList.remove('ec-drag');
      if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
    });
    render();
    watchTaskPanel();
    if (load(OPENK, false)) toggle(true, true);
    setInterval(poll, 3000); poll();
    // Browsers throttle/pause setInterval in background or inactive tabs, so a reply
    // that finished server-side can sit unfetched until the user interacts — making an
    // already-ready answer appear only when you type your next question. Poll the instant
    // the tab regains visibility/focus so completed answers surface immediately on return.
    document.addEventListener('visibilitychange', function () { if (!document.hidden) poll(); });
    window.addEventListener('focus', poll);
  }

  // Keep the launcher/chat clickable and visible when the task detail drawer is open.
  // The drawer (#panelOverlay toggles .open) sits at z-index 998/999; the launcher now
  // rides above it and shifts left of the drawer on wide screens (see .mc-task-open CSS).
  function watchTaskPanel() {
    var ov = document.getElementById('panelOverlay'); // only exists on the tasks board
    if (!ov) return;
    function sync() {
      var open = ov.classList.contains('open');
      var fab = document.getElementById('exobotFab');
      var chat = document.getElementById('exobotChat');
      if (fab) fab.classList.toggle('mc-task-open', open);
      if (chat) chat.classList.toggle('mc-task-open', open);
    }
    new MutationObserver(sync).observe(ov, { attributes: true, attributeFilter: ['class'] });
    sync();
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
    } else { p.classList.remove('open'); fab.style.display = ''; save(OPENK, false);
      var hp = document.getElementById('ecHelpPop'); if (hp) hp.classList.remove('show'); }
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
  function addFiles(list) {
    Array.prototype.slice.call(list || []).forEach(function (f) {
      if (attachments.length >= 10) { pushHist({ who: 'bot', text: 'You can attach up to 10 documents at a time.' }); render(); return; }
      if (f.size > 25 * 1024 * 1024) { pushHist({ who: 'bot', text: '"' + (f.name || 'file') + '" is too large (max 25 MB).' }); render(); return; }
      var rd = new FileReader();
      rd.onload = function () { attachments.push({ name: f.name || 'document', data: rd.result, size: f.size }); renderAtt(); };
      rd.readAsDataURL(f);
    });
    if (!isOpen()) toggle(true);
  }
  function renderAtt() {
    var el = document.getElementById('ecAtt'); if (!el) return;
    el.innerHTML = '';
    attachments.forEach(function (a, i) {
      var c = document.createElement('div'); c.className = 'ec-chip';
      var s = document.createElement('span'); s.textContent = '📄 ' + a.name;
      var x = document.createElement('b'); x.textContent = '✕'; x.title = 'Remove';
      x.addEventListener('click', function () { attachments.splice(i, 1); renderAtt(); });
      c.appendChild(s); c.appendChild(x); el.appendChild(c);
    });
    el.classList.toggle('show', attachments.length > 0);
  }
  function send() {
    var inp = document.getElementById('ecInput'); var msg = (inp.value || '').trim();
    if (!msg && !attachments.length) return;
    inp.value = '';
    var atts = attachments.slice(); attachments = []; renderAtt();
    var label = msg + (atts.length ? (msg ? '\n' : '') + atts.map(function (a) { return '📄 ' + a.name; }).join('\n') : '');
    pushHist({ who: 'me', text: label }); render();
    var btn = document.getElementById('ecSendBtn'); btn.disabled = true;
    fetch('/api/chat', { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: msg, attachments: atts.map(function (a) { return { name: a.name, data: a.data }; }) }) })
      .then(function (r) {
        btn.disabled = false;
        if (r.status === 401) { pushHist({ who: 'bot', text: 'Session expired — reload and log in.' }); render(); return; }
        return r.json().then(function (j) {
          if (r.status === 429) { pushHist({ who: 'bot', text: (j && j.error) || 'Too many questions running at once — let one finish.' }); render(); return; }
          if (j && j.jobId) { pending.push({ jobId: j.jobId, q: msg || (atts.length ? '📄 ' + atts[0].name : ''), ts: nowMs() }); save(PEND, pending); render(); poll(); }
          else { pushHist({ who: 'bot', text: (j && (j.reply || j.error)) || 'No reply.' }); render(); }
        });
      })
      .catch(function (e) { btn.disabled = false; pushHist({ who: 'bot', text: 'Error: ' + e.message }); render(); });
    var inp2 = document.getElementById('ecInput'); if (inp2) inp2.focus();
  }
  function poll() {
    prunePending();
    if (!pending.length) return;
    pending.slice().forEach(function (p) {
      function drop(text) {
        pending = pending.filter(function (x) { return x.jobId !== p.jobId; }); save(PEND, pending);
        if (text) { pushHist({ who: 'bot', text: text }); if (!isOpen()) { unread++; badge(unread); } }
        render();
      }
      fetch('/api/chat/result?id=' + encodeURIComponent(p.jobId), { credentials: 'same-origin' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .then(function (j) {
          if (j && j.status === 'pending') return;              // still working — keep waiting
          if (j) { drop(j.reply || j.error || 'No reply.'); return; }   // terminal answer/error
          // Unknown/expired job (server 404 or error body). Tolerate a brief blip,
          // but once past GRACE the job is gone for good — clear it so it can't hang.
          if (nowMs() - (p.ts || 0) > PEND_GRACE) drop('That request timed out and was cleared — please re-send if you still need it.');
        }).catch(function () {
          if (nowMs() - (p.ts || 0) > PEND_TTL) drop('');        // network trouble past the hard cap — silently clear
        });
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
