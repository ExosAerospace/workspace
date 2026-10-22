'use strict';
// Selftest for MC Guard graduated response (lib/guard.js TEMP tier). Offline: temp state/log dir,
// no Discord DMs, no Cloudflare calls, fake clock. Run: node mission-control/tests/guard_templock_selftest.js
const fs = require('fs'), os = require('os'), path = require('path'), assert = require('assert');
const { execFileSync } = require('child_process');
const EventEmitter = require('events');

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mcguard-'));
const STATE = path.join(tmp, 'guard-state.json');
fs.writeFileSync(STATE, JSON.stringify({ scoring_mode: 'enforce', watch_started: '2026-09-27T00:00:00Z', locked: {}, alerts: {} }));
Object.assign(process.env, { MC_GUARD_STATE: STATE, MC_GUARD_LOG_DIR: tmp, MC_GUARD_NO_DM: '1', MC_GUARD_NO_CF: '1' });
delete process.env.ENTITY;
const guard = require('../lib/guard');

let clock = Date.parse('2026-10-22T17:00:00Z');   // noon CT: no odd-hours points
guard._setNow(() => clock);
const users = [
  { id: 'u1', email: 'alice@example.com', name: 'Alice', role: 'member', active: true },
  { id: 'u2', email: 'bob@example.com', name: 'Bob', role: 'member', active: true },
  { id: 'u3', email: 'carol@example.com', name: 'Carol', role: 'admin', active: true },
];
const sessions = new Map();
guard.init({ sessions, saveSessions() {}, loadUsers: () => JSON.parse(JSON.stringify(users)), saveUsers(u) { users.splice(0, users.length, ...u); } });

const sess = (u) => ({ userId: u.id, email: u.email, name: u.name, role: u.role });
function req(session, url) {
  return { url: url || '/api/tasks', method: 'GET', socket: { remoteAddress: '10.0.0.5' },
    headers: { 'cf-ray': 'x', 'cf-connecting-ip': '203.0.113.9', 'cf-ipcountry': 'US', 'user-agent': 'Mozilla/5.0' } };
}
function res() {
  const r = new EventEmitter(); r.statusCode = 200; r.body = '';
  r.writeHead = (c) => { r.statusCode = c; }; r.end = (b) => { r.body = String(b || ''); r.emit('finish'); }; r.getHeader = () => 0;
  return r;
}
function hit(session, url) { const q = req(session, url), s = res(); const blocked = guard.check(q, s, session); return { blocked, code: blocked ? s.statusCode : 200, body: s.body }; }
function burst(session, n) { let last; for (let i = 0; i < n; i++) { last = hit(session); if (last.blocked) return { i: i + 1, ...last }; } return { i: n, ...last }; }
const events = () => fs.readFileSync(path.join(tmp, 'evidence.jsonl'), 'utf8').trim().split('\n').map(l => JSON.parse(l).event);
const st = () => JSON.parse(fs.readFileSync(STATE, 'utf8'));

let n = 0; const queue = []; const t = (name, fn) => queue.push([name, fn]);
const alice = users[0], bob = users[1];

t('constants: suspicious band sits between medium and high', () => {
  assert(guard.T.medium < guard.TEMP.score && guard.TEMP.score < guard.T.high);
  assert.deepStrictEqual([guard.TEMP.first_min, guard.TEMP.second_min, guard.TEMP.permanent_on, guard.TEMP.window_hr], [15, 60, 3, 24]);
});
t('normal activity (score below threshold) -> nothing', () => {
  const r = burst(sess(alice), 120);
  assert(!r.blocked, 'blocked at request ' + r.i);
  assert(!st().temp_locked || !Object.keys(st().temp_locked).length);
});
t('suspicious (rate >300/min = 60) -> temp lock 15 min, 423, sessions killed', () => {
  clock += 5 * 60000;
  sessions.set('tokA', { userId: 'u1' }); sessions.set('tokB', { userId: 'u2' });
  const r = burst(sess(alice), 400);
  assert(r.blocked && r.code === 423, `expected 423, got ${r.code} at ${r.i}`);
  assert(/paused for 15 minutes because of unusual activity\. Contact your administrator\./.test(r.body), r.body);
  const tl = st().temp_locked['user:u1'];
  assert(tl && tl.minutes === 15 && tl.n === 1);
  assert(!sessions.has('tokA') && sessions.has('tokB'), 'only alice sessions killed');
  assert(users[0].active === true, 'temp lock must NOT deactivate the MC user');
  assert(!Object.keys(st().locked).length, 'no permanent lock');
  assert(events().includes('TEMP_LOCKOUT'));
  const dm = fs.readFileSync(path.join(tmp, 'dm-test.log'), 'utf8');
  assert(/temp lock 15 min/.test(dm) && dm.trim().split('\n')[0] === dm.trim().split('\n---')[0], 'one-line DM');
});
t('during temp lock: any request 423 (API json, page html) with remaining minutes', () => {
  clock += 5 * 60000;
  const a = hit(sess(alice), '/api/x'); assert.strictEqual(a.code, 423); assert(/paused for 10 minutes/.test(JSON.parse(a.body).error));
  const b = hit(sess(alice), '/tasks.html'); assert.strictEqual(b.code, 423); assert(/Access paused/.test(b.body));
  assert(!hit(sess(bob)).blocked, 'other users unaffected');
});
t('tripwire during temp lock still = permanent lockout', () => {
  // use a separate identity so alice's escalation path stays clean
  const dave = { id: 'u4', email: 'dave@example.com', name: 'Dave', role: 'member', active: true }; users.push(dave);
  burst(sess(dave), 400);
  assert(st().temp_locked['user:u4']);
  const r = hit(sess(dave), '/api/export/all');
  assert.strictEqual(r.code, 404);
  assert(st().locked['user:u4'] && st().locked['user:u4'].reason === 'Tripwire hit');
  assert(!st().temp_locked['user:u4'], 'permanent supersedes temp');
  assert(users.find(u => u.id === 'u4').active === false);
});
t('expiry -> access restored, TEMP_EXPIRED logged', () => {
  clock += 11 * 60000;
  const r = hit(sess(alice));
  assert(!r.blocked, 'still blocked: ' + r.code);
  assert(!st().temp_locked['user:u1']);
  assert(events().includes('TEMP_EXPIRED'));
});
t('2nd within 24h -> 60 min', () => {
  clock += 2 * 60000;
  const r = burst(sess(alice), 400);
  assert.strictEqual(r.code, 423); assert(/paused for 60 minutes/.test(r.body));
  assert.strictEqual(st().temp_locked['user:u1'].n, 2);
  clock += 59 * 60000; assert.strictEqual(hit(sess(alice)).code, 423);
  clock += 2 * 60000; assert(!hit(sess(alice)).blocked);
});
t('3rd within 24h -> permanent lockout() path (user deactivated, blocklisted)', () => {
  clock += 2 * 60000;
  const r = burst(sess(alice), 400);
  assert.strictEqual(r.code, 403);
  const s = st();
  assert(s.locked['user:u1'] && /temp lock #3/.test(s.locked['user:u1'].reason), JSON.stringify(s.locked['user:u1']));
  assert(!s.temp_locked['user:u1']);
  assert(users[0].active === false && users[0].guard_locked);
  assert(events().includes('TEMP_ESCALATE') && events().includes('LOCKOUT'));
  assert.strictEqual(hit(sess(alice)).code, 403);
});
t('history older than 24h does not escalate', () => {
  burst(sess(bob), 400); assert.strictEqual(st().temp_locked['user:u2'].n, 1);
  clock += 25 * 3600000;
  assert(!hit(sess(bob)).blocked);
  burst(sess(bob), 400); assert.strictEqual(st().temp_locked['user:u2'].n, 1, 'old trigger pruned');
});
t('admin unlock of a temp lock clears it + history', async () => {
  const r = await guard.unlock('user:u2', 'jquinn@exosaero.com');
  assert(r.ok && r.kind === 'temp'); assert(!st().temp_locked['user:u2'] && !st().temp_history['user:u2']);
  assert(!hit(sess(bob)).blocked);
});
t('exempt (Jon) and on-box automation never temp-locked', () => {
  const jon = { userId: 'j', email: 'jquinn@exosaero.com', name: 'Jon', role: 'admin' };
  assert(!burst(jon, 400).blocked);
  const auto = { url: '/api/tasks', method: 'GET', socket: { remoteAddress: '127.0.0.1' }, headers: { 'user-agent': 'curl/8' } };
  for (let i = 0; i < 400; i++) assert(!guard.check(auto, res(), null));
  assert(!st().temp_locked['user:j']);
});
t('watch mode: suspicious score takes no action', () => {
  const s = st(); s.scoring_mode = 'watch'; fs.writeFileSync(STATE, JSON.stringify(s)); fs.utimesSync(STATE, new Date(), new Date(Date.now() + 5000));
  guard.status();   // force reload
  clock += 3 * 3600000;
  const eve = { id: 'u5', email: 'eve@example.com', name: 'Eve', role: 'member', active: true }; users.push(eve);
  assert(!burst(sess(eve), 400).blocked);
  assert(!st().temp_locked['user:u5']);
});
t('Exos (non-cell): a role=admin user is NOT a guard admin; Jon is', () => {
  assert(guard.JON_EMAILS.has('jquinn@exosaero.com'));
  assert(!guard.JON_EMAILS.has('carol@example.com'));
});
t('entity cell: cell admins may unlock; members may not; Jon still may', () => {
  const cellTmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mcguard-cell-'));
  const code = `
    const g = require(${JSON.stringify(path.join(__dirname, '..', 'lib', 'guard'))});
    const users = [{ id: 'a', email: 'boss@cell.example', role: 'admin', active: true }, { id: 'm', email: 'mem@cell.example', role: 'member', active: true }];
    g.init({ sessions: new Map(), saveSessions() {}, loadUsers: () => users, saveUsers() {} });
    const out = { admin: g.JON_EMAILS.has('boss@cell.example'), member: g.JON_EMAILS.has('mem@cell.example'), jon: g.JON_EMAILS.has('jquinn@exosaero.com'), can: g.canUnlock({ email: 'BOSS@cell.example' }) };
    console.log(JSON.stringify(out));`;
  const env = Object.assign({}, process.env, { ENTITY: 'sslc', MC_GUARD_STATE: path.join(cellTmp, 's.json'), MC_GUARD_LOG_DIR: cellTmp });
  const out = JSON.parse(execFileSync(process.execPath, ['-e', code], { env }).toString().trim());
  assert.deepStrictEqual(out, { admin: true, member: false, jon: true, can: true });
});

(async () => {
  for (const [name, fn] of queue) {
    try { await fn(); } catch (e) { console.error('FAIL', n + 1, name, '\n', e && e.stack || e); process.exit(1); }
    n++; console.log('ok', n, name);
  }
  console.log(`GUARD TEMPLOCK SELFTEST PASS (${n} checks)`);
  fs.rmSync(tmp, { recursive: true, force: true });
  process.exit(0);
})();
