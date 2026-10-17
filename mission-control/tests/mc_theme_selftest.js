// exo3 eval for mc-theme.js (Jon 2026-10-15 "Joint Ops Center" look): opt-in only, persists, default unchanged.
const vm = require('vm'), fs = require('fs'), path = require('path'), assert = require('assert');
const src = fs.readFileSync(path.join(__dirname, '..', 'mc-theme.js'), 'utf8');
function run(search, stored) {
  const store = stored ? { mcTheme: stored } : {}; const head = []; const body = [];
  const doc = { readyState: 'complete', head: { appendChild: n => head.push(n) }, documentElement: {}, body: { appendChild: n => body.push(n) },
    getElementById: () => null, createElement: t => ({ tag: t, style: {} }), addEventListener() {} };
  vm.runInNewContext(src, { URLSearchParams, location: { search, reload() {} }, document: doc,
    localStorage: { getItem: k => store[k] || null, setItem: (k, v) => { store[k] = v; } } });
  return { head, body, store };
}
let n = 0; const ok = (c, m) => { assert.ok(c, 'FAIL: ' + m); n++; };
let r = run('', null); ok(r.head.length === 0 && r.body.length === 1, 'default: no theme css, toggle shown');
r = run('?theme=joc', null); ok(r.head[0] && r.head[0].href === '/theme-joc.css' && r.store.mcTheme === 'joc', '?theme=joc loads + remembers');
r = run('', 'joc'); ok(r.head.length === 1, 'remembered choice applies on next page');
r = run('?theme=hud', null); ok(r.head[0] && r.head[0].href === '/theme-hud.css' && r.store.mcTheme === 'hud', '?theme=hud loads rugged HMD + remembers');
r = run('', 'bogus'); ok(r.head.length === 0, 'unknown stored theme falls back to default');
r = run('?theme=default', 'joc'); ok(r.head.length === 0 && r.store.mcTheme === 'default', '?theme=default turns it off');
console.log(`mc-theme selftest: ${n}/${n} pass`);
