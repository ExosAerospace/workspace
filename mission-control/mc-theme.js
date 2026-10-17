// Mission Control theme loader (Jon 2026-10-15; "Mech Cockpit" 2026-10-16, replacing the short-lived Rugged HMD). Injected into every MC page by server.js next to the Exobot widget.
// Default look is unchanged; themes are opt-in per browser:
//   ?theme=mech -> Mech Cockpit (theme-mech.css)   ?theme=joc -> Joint Ops Center (theme-joc.css)   ?theme=default -> off
//   or the "DISPLAY MODE" button bottom-left (Jon 10/16: employees pick the look they prefer). Choice is remembered per browser.
(function () {
  var KEY = 'mcTheme';
  var V = '20261016-2232';  // bump on every theme CSS change: server sends .css without no-store, so browsers keep stale copies (Jon 10/16 still saw the old font)
  var THEMES = { mech: { css: '/theme-mech.css', label: 'MECH COCKPIT' }, joc: { css: '/theme-joc.css', label: 'OPS CENTER' } };
  var MENU = [['default', 'Standard', 'Classic Mission Control look'],
              ['mech', 'Mech Cockpit', 'Armored cockpit over Earth orbit'],
              ['joc', 'Ops Center', 'Charcoal + amber operations board']];
  var ALIAS = { hud: 'mech' };  // retired 10/16 -> its successor
  try {
    var q = new URLSearchParams(location.search).get('theme');
    if (ALIAS[q]) q = ALIAS[q];
    if (q === 'default' || THEMES[q]) localStorage.setItem(KEY, q);
  } catch (e) {}
  var cur = 'default'; try { cur = localStorage.getItem(KEY) || 'default'; } catch (e) {}
  if (ALIAS[cur]) cur = ALIAS[cur];
  if (!THEMES[cur]) cur = 'default';
  if (cur !== 'default') {
    var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = THEMES[cur].css + '?v=' + V; l.id = 'mc-theme-css';
    (document.head || document.documentElement).appendChild(l);
  }
  function pick(id) { try { localStorage.setItem(KEY, id); } catch (e) {} location.reload(); }
  function addToggle() {
    if (document.getElementById('mc-theme-toggle')) return;
    var b = document.createElement('button'); b.id = 'mc-theme-toggle'; b.type = 'button';
    b.textContent = '◐ DISPLAY MODE ▴';
    b.title = 'Choose how Mission Control looks for you (remembered in this browser)';
    b.style.cssText = cur !== 'default' ? '' : 'position:fixed;left:12px;bottom:12px;z-index:2147483001;font:600 11px Menlo,monospace;letter-spacing:.12em;background:#0a1628;color:#e8edf2;border:1px solid rgba(245,166,35,.6);padding:6px 10px;cursor:pointer;border-radius:4px;opacity:.9';
    var m = document.createElement('div'); m.id = 'mc-theme-menu';
    m.style.cssText = 'display:none;position:fixed;left:12px;bottom:44px;z-index:2147483002;min-width:250px;background:#0a1628;border:1px solid rgba(255,255,255,.18);border-radius:4px;box-shadow:0 8px 24px rgba(0,0,0,.6);padding:4px;font:13px -apple-system,system-ui,sans-serif;color:#e8edf2';
    MENU.forEach(function (it) {
      var r = document.createElement('div'); r.setAttribute('data-theme', it[0]);
      r.style.cssText = 'padding:8px 10px;cursor:pointer;border-radius:3px;' + (it[0] === cur ? 'background:rgba(245,166,35,.18);' : '');
      r.innerHTML = '<b>' + (it[0] === cur ? '✓ ' : '') + it[1] + '</b><div style="font-size:11px;color:#a0aec0;margin-top:2px">' + it[2] + '</div>';
      r.onmouseenter = function () { if (it[0] !== cur) r.style.background = 'rgba(255,255,255,.08)'; };
      r.onmouseleave = function () { if (it[0] !== cur) r.style.background = ''; };
      r.onclick = function () { if (it[0] !== cur) pick(it[0]); else m.style.display = 'none'; };
      m.appendChild(r);
    });
    b.onclick = function (e) { e.stopPropagation(); m.style.display = m.style.display === 'none' ? 'block' : 'none'; };
    document.addEventListener('click', function (e) { if (!m.contains(e.target)) m.style.display = 'none'; });
    document.body.appendChild(m); document.body.appendChild(b);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', addToggle); else addToggle();
})();
