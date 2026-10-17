// exo3 eval for mc-theme.js (Jon 2026-10-15 "Joint Ops Center" look): opt-in only, persists, default unchanged.
const vm = require('vm'), fs = require('fs'), path = require('path'), assert = require('assert');
const src = fs.readFileSync(path.join(__dirname, '..', 'mc-theme.js'), 'utf8');
function run(search, stored) {
  const store = stored ? { mcTheme: stored } : {}; const head = []; const body = [];
  const doc = { readyState: 'complete', head: { appendChild: n => head.push(n) }, documentElement: {}, body: { appendChild: n => body.push(n) },
    getElementById: () => null, createElement: t => { const k = []; return { tag: t, style: {}, kids: k, setAttribute() {}, appendChild: n => k.push(n) }; }, addEventListener() {} };
  vm.runInNewContext(src, { URLSearchParams, location: { search, reload() {} }, document: doc,
    localStorage: { getItem: k => store[k] || null, setItem: (k, v) => { store[k] = v; } } });
  return { head, body, store };
}
let n = 0; const ok = (c, m) => { assert.ok(c, 'FAIL: ' + m); n++; };
let r = run('', null); ok(r.head.length === 0 && r.body.length === 2, 'default: no theme css, Display Mode button + menu shown');
const btn = r.body.find(n => n.id === 'mc-theme-toggle'), menu = r.body.find(n => n.id === 'mc-theme-menu');
ok(btn && /DISPLAY MODE/.test(btn.textContent) && menu && menu.kids.length === 3, 'menu offers Standard / Mech Cockpit / Ops Center');
r = run('?theme=joc', null); ok(r.head[0] && r.head[0].href.indexOf('/theme-joc.css?v=') === 0 && r.store.mcTheme === 'joc', '?theme=joc loads + remembers');
r = run('', 'joc'); ok(r.head.length === 1, 'remembered choice applies on next page');
r = run('?theme=mech', null); ok(r.head[0] && r.head[0].href.indexOf('/theme-mech.css?v=') === 0 && r.store.mcTheme === 'mech', '?theme=mech loads Mech Cockpit + remembers');
r = run('', 'hud'); ok(r.head[0] && r.head[0].href.indexOf('/theme-mech.css?v=') === 0, 'retired hud choice upgrades to mech');
r = run('', 'bogus'); ok(r.head.length === 0, 'unknown stored theme falls back to default');
r = run('?theme=default', 'joc'); ok(r.head.length === 0 && r.store.mcTheme === 'default', '?theme=default turns it off');
console.log(`mc-theme selftest: ${n}/${n} pass`);
