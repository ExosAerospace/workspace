// Mission Control theme loader (Jon 2026-10-15; "Rugged HMD" added 2026-10-16). Injected into every MC page by server.js next to the Exobot widget.
// Default look is unchanged; themes are opt-in per browser:
//   ?theme=hud -> Rugged HMD (theme-hud.css)   ?theme=joc -> Joint Ops Center (theme-joc.css)   ?theme=default -> off
//   or click the toggle bottom-left (cycles STANDARD -> RUGGED HMD -> OPS CENTER). Choice is remembered.
(function () {
  var KEY = 'mcTheme';
  var THEMES = { hud: { css: '/theme-hud.css', label: 'RUGGED HMD' }, joc: { css: '/theme-joc.css', label: 'OPS CENTER' } };
  var ORDER = ['default', 'hud', 'joc'];
  try {
    var q = new URLSearchParams(location.search).get('theme');
    if (q === 'default' || THEMES[q]) localStorage.setItem(KEY, q);
  } catch (e) {}
  var cur = 'default'; try { cur = localStorage.getItem(KEY) || 'default'; } catch (e) {}
  if (!THEMES[cur]) cur = 'default';
  if (cur !== 'default') {
    var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = THEMES[cur].css; l.id = 'mc-theme-css';
    (document.head || document.documentElement).appendChild(l);
  }
  var next = ORDER[(ORDER.indexOf(cur) + 1) % ORDER.length];
  function addToggle() {
    if (document.getElementById('mc-theme-toggle')) return;
    var b = document.createElement('button'); b.id = 'mc-theme-toggle';
    b.textContent = '◐ ' + (next === 'default' ? 'STANDARD VIEW' : THEMES[next].label + ' VIEW');
    b.title = 'Switch Mission Control look (remembered in this browser)';
    b.style.cssText = cur !== 'default' ? '' : 'position:fixed;left:12px;bottom:12px;z-index:2147483001;font:11px Menlo,monospace;letter-spacing:.12em;background:rgba(10,22,40,.85);color:#a0aec0;border:1px solid rgba(255,255,255,.15);padding:5px 9px;cursor:pointer;border-radius:4px;opacity:.6';
    b.onclick = function () { try { localStorage.setItem(KEY, next); } catch (e) {} location.reload(); };
    document.body.appendChild(b);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', addToggle); else addToggle();
})();
