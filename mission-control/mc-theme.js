// Mission Control theme loader (Jon 2026-10-15). Injected into every MC page by server.js next to the Exobot widget.
// Default look is unchanged; "Joint Ops Center" (theme-joc.css) is opt-in per browser:
//   ?theme=joc  -> on (remembered)   ?theme=default -> off   or click the toggle bottom-left.
(function () {
  var KEY = 'mcTheme';
  try {
    var q = new URLSearchParams(location.search).get('theme');
    if (q === 'joc' || q === 'default') localStorage.setItem(KEY, q);
  } catch (e) {}
  var on = false; try { on = localStorage.getItem(KEY) === 'joc'; } catch (e) {}
  if (on) {
    var l = document.createElement('link'); l.rel = 'stylesheet'; l.href = '/theme-joc.css'; l.id = 'mc-theme-css';
    (document.head || document.documentElement).appendChild(l);
  }
  function addToggle() {
    if (document.getElementById('mc-theme-toggle')) return;
    var b = document.createElement('button'); b.id = 'mc-theme-toggle';
    b.textContent = on ? '◐ STANDARD VIEW' : '◐ OPS CENTER VIEW';
    b.title = 'Switch Mission Control look (remembered in this browser)';
    b.style.cssText = on ? '' : 'position:fixed;left:12px;bottom:12px;z-index:2147483001;font:11px Menlo,monospace;letter-spacing:.12em;background:rgba(10,22,40,.85);color:#a0aec0;border:1px solid rgba(255,255,255,.15);padding:5px 9px;cursor:pointer;border-radius:4px;opacity:.6';
    b.onclick = function () { try { localStorage.setItem(KEY, on ? 'default' : 'joc'); } catch (e) {} location.reload(); };
    document.body.appendChild(b);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', addToggle); else addToggle();
})();
