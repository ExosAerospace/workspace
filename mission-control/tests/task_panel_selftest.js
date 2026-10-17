// exo3 eval for the MC task panel Updates tab (Jon 2026-10-17, #3808). Failure replays:
//  1. a transient /api/tasks/updates HTTP 500 wiped the Updates list, even on a silent background poll;
//  2. Enter + click posted the same note twice in one second -> duplicate Exo routing (3 identical acks).
// Extracts the live loadTimeline/postUpdate source from index.html and runs it in a stubbed sandbox.
// Run: node mission-control/tests/task_panel_selftest.js
const assert = require('assert'); const fs = require('fs'); const path = require('path'); const vm = require('vm');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const fn = name => {
  const i = html.indexOf(`async function ${name}(`); assert.ok(i >= 0, `${name} not found in index.html`);
  const j = html.indexOf('\n}\n', i); return html.slice(i, j + 2);
};
let n = 0; const ok = (c, m) => { assert.ok(c, 'FAIL: ' + m); n++; };

(async () => {
  // 1. Updates list survives a transient error
  const list = { innerHTML: '<div>EXISTING UPDATES</div>' };
  const timers = [];
  const ctx = {
    document: { getElementById: () => list }, currentPanelTaskId: '3808', escHtml: s => String(s),
    apiFetch: async () => { throw new Error('HTTP 500'); },
    setTimeout: (f, ms) => timers.push(ms), console,
  };
  vm.createContext(ctx); vm.runInContext(fn('loadTimeline'), ctx);
  await ctx.loadTimeline('3808', { silent: true });
  ok(list.innerHTML.includes('EXISTING UPDATES'), 'silent poll error keeps the Updates on screen');
  await ctx.loadTimeline('3808');
  ok(timers.length === 1, 'visible load retries instead of erroring at once');
  await ctx.loadTimeline('3808', { _tries: 2 });
  ok(/Retry/.test(list.innerHTML) && !/Failed to load/.test(list.innerHTML), 'after 2 retries: error with a Retry link');

  // 2. One post per request (double-submit guard)
  let posts = 0, release;
  const ta = { value: '@Exobot pull the NYK contacts', style: {}, dataset: {}, focus() {}, disabled: false };
  const ctx2 = {
    document: { getElementById: () => ta }, currentPanelTaskId: '3808', _exoWaitSince: 0,
    apiFetch: () => { posts++; return new Promise(r => { release = r; }); },
    toast() {}, loadTimeline() {}, switchTab() {}, startPanelLive() {}, Date, console,
  };
  vm.createContext(ctx2); vm.runInContext('let _posting = false;\n' + fn('postUpdate'), ctx2);
  const a = ctx2.postUpdate(); const b = ctx2.postUpdate();   // Enter + click in the same tick
  release(); await a; await b;
  ok(posts === 1, 'Enter + click posts the note once');
  ta.value = '@Exobot second, different ask';
  const c = ctx2.postUpdate(); release(); await c;
  ok(posts === 2, 'guard resets: the next note still posts');

  console.log(`task_panel selftest: ${n}/${n} pass`);
})().catch(e => { console.error(e.message); process.exit(1); });
