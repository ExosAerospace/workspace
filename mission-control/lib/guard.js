// ── MC GUARD: anti-scraping / anti-exfiltration (Jon approved 2026-09-26) ─────────────────
// Building-alarm model for Mission Control:
//   1. TRIPWIRES — bait paths no real workflow touches (hidden links, fake export endpoints,
//      fake files). Any hit by a non-exempt identity = instant lockout. ENFORCED from day one.
//   2. BEHAVIOR SCORING — per-identity rolling risk score (rate, distinct records, downloads,
//      denied calls, automation user-agents, odd hours, new IPs). Runs WATCH-ONLY until Jon
//      approves tuned thresholds (state.scoring_mode === 'enforce').
//   3. GRADUATED RESPONSE — low: log; medium: DM Jon + throttle (enforce mode); high/tripwire:
//      lockout = MC user deactivated + all sessions killed + Cloudflare Access revoked + blocklist.
//      Only Jon unlocks (scripts/mc_guard.py unlock <key>, or POST /api/admin/guard/unlock).
//   4. TRACEABLE COPIES — every served document carries a per-download trace id (PDF trailer
//      comment / Office zip comment) recorded with the sha256 in the trace ledger.
//   5. EVIDENCE — append-only, hash-chained JSONL (logs/mc-guard/evidence.jsonl).
// GUARDRAILS: Jon and local automation (loopback, no Cloudflare headers) are NEVER locked —
// alert only. Nothing here may block the event loop (no sync child processes; async https).
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const https = require('https');
const { spawn } = require('child_process');

const ROOT = path.join(__dirname, '..');                 // mission-control/
const WS = path.join(ROOT, '..');                        // workspace
const LOG_DIR = process.env.MC_GUARD_LOG_DIR || path.join(WS, 'logs', 'mc-guard');   // env overrides = test harness only
const STATE_FILE = process.env.MC_GUARD_STATE || path.join(ROOT, 'data', 'guard-state.json');
const EVIDENCE = path.join(LOG_DIR, 'evidence.jsonl');
const HOURLY = path.join(LOG_DIR, 'hourly.jsonl');
const TRACE_LEDGER = path.join(LOG_DIR, 'trace-ledger.jsonl');
const SECRET_FILE = path.join(ROOT, 'data', '.guard-secret');
try { fs.mkdirSync(LOG_DIR, { recursive: true }); } catch (e) {}

const JON_EMAILS = new Set(['jquinn@exosaero.com', 'jquinnexo@pm.me']);
const JON_DISCORD = 'user:1501632195163590739';
const CF_ACC = '6b178cbe1c76dfd717c07460d5c0f653';
const CF_APP = 'e4fef0a6-7c43-42d0-91ca-ff9e22fa70ea';
const CF_POLICY = '3bf75a2c-33f7-4901-bfac-ae153fb47d9b';

// ── Tripwire bait. None of these are real routes; nothing in MC links to them except the
// hidden (display:none, aria-hidden, nofollow) anchors injected into pages for scrapers. ──
const TRIPWIRE_EXACT = new Set([
  '/api/export/all', '/api/admin/export-all', '/api/crm/export', '/api/contacts/export-all',
  '/api/v1/dump', '/api/backup/full', '/api/internal/users-dump', '/api/deals/export-all',
  '/.env', '/.git/config', '/.git/HEAD', '/config.json.bak', '/server.js', '/users.json', '/sessions.json',
  '/uploads/Exos_Investor_Master_List_FULL_EXPORT.xlsx', '/uploads/MC_CRM_Full_Export_ALL_CONTACTS.csv',
]);
const HIDDEN_LINKS = '<div style="display:none" aria-hidden="true">'
  + '<a href="/api/export/all" rel="nofollow" tabindex="-1">Export all</a>'
  + '<a href="/uploads/Exos_Investor_Master_List_FULL_EXPORT.xlsx" rel="nofollow" tabindex="-1">Investor master list</a>'
  + '<a href="/api/contacts/export-all" rel="nofollow" tabindex="-1">Contacts export</a></div>';
const ROBOTS = 'User-agent: *\nDisallow: /api/export/all\nDisallow: /api/v1/dump\nDisallow: /uploads/Exos_Investor_Master_List_FULL_EXPORT.xlsx\nDisallow: /\n';

const AUTOMATION_UA = /(curl|wget|python-requests|python-urllib|aiohttp|httpx|httpie|go-http-client|okhttp|java\/|libwww|scrapy|headless|puppeteer|playwright|selenium|phantomjs|node-fetch|axios|undici|postman|insomnia|powershell|httrack|sitesucker)/i;
const DOWNLOAD_RE = /^\/(uploads|viewpdf|backup)\/|^\/api\/dataroom-doc/;

// Initial thresholds (WATCH-ONLY until tuned + approved). Scores add; tiers below.
const T = {
  rpm: [120, 300], records_hr: [300, 1000], downloads_hr: [25, 75], mb_hr: 200,
  denied_10m: [20, 60], medium: 40, high: 80,
};

// ── state ──
function defaultState() {
  return { scoring_mode: 'watch', watch_started: new Date().toISOString(), locked: {}, alerts: {} };
}
let state = defaultState(), stateMtime = 0, lastStateCheck = 0;
function loadState(force) {
  const now = Date.now();
  if (!force && now - lastStateCheck < 3000) return;
  lastStateCheck = now;
  try {
    const st = fs.statSync(STATE_FILE);
    if (st.mtimeMs !== stateMtime) { state = Object.assign(defaultState(), JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'))); stateMtime = st.mtimeMs; }
  } catch (e) { saveState(); }
}
function saveState() {
  try { fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2)); stateMtime = fs.statSync(STATE_FILE).mtimeMs; } catch (e) {}
}
function secret() {
  try { return fs.readFileSync(SECRET_FILE, 'utf8').trim(); }
  catch (e) { const s = crypto.randomBytes(32).toString('hex'); try { fs.writeFileSync(SECRET_FILE, s, { mode: 0o600 }); } catch (e2) {} return s; }
}
const SECRET = secret();

// ── evidence log: append-only + hash-chained (tamper-evident) ──
let lastHash = null;
function evidence(entry) {
  try {
    if (lastHash === null) {
      lastHash = 'GENESIS';
      try { const lines = fs.readFileSync(EVIDENCE, 'utf8').trim().split('\n'); const last = lines[lines.length - 1]; if (last) lastHash = JSON.parse(last).hash; } catch (e) {}
    }
    const rec = Object.assign({ ts: new Date().toISOString() }, entry, { prev: lastHash });
    rec.hash = crypto.createHash('sha256').update(JSON.stringify(rec)).digest('hex');
    fs.appendFileSync(EVIDENCE, JSON.stringify(rec) + '\n');
    lastHash = rec.hash;
  } catch (e) {}
}

// ── alerts to Jon (async, never blocks) ──
function dmJon(text) {
  if (process.env.MC_GUARD_NO_DM) { try { fs.appendFileSync(path.join(LOG_DIR, 'dm-test.log'), text + '\n---\n'); } catch (e) {} return; }
  try {
    const p = spawn('/usr/bin/python3', [path.join(WS, 'scripts', 'deliver.py'), '--target', JON_DISCORD, '--source', 'mc-guard', '-m', text],
      { cwd: WS, detached: true, stdio: 'ignore' });
    p.on('error', () => {}); p.unref();
  } catch (e) {}
}

// ── identity ──
function identify(req, session) {
  const h = req.headers;
  const cfEmail = (h['cf-access-authenticated-user-email'] || '').toString().toLowerCase();
  const viaCf = !!(h['cf-ray'] || h['cf-connecting-ip']);
  const raw = (req.socket && req.socket.remoteAddress) || '';
  const ip = (h['cf-connecting-ip'] || (h['x-forwarded-for'] || '').split(',')[0] || raw).toString().trim();
  const loopback = /^(::1|127\.|::ffff:127\.)/.test(raw);
  const email = ((session && session.email) || '').toLowerCase();
  const key = session ? 'user:' + session.userId : (cfEmail ? 'cf:' + cfEmail : 'ip:' + ip);
  const automation = loopback && !viaCf;           // on-box launchd pollers / Exo jobs
  // Identity = the MC login when there is one. The Cloudflare email only counts when there's no MC
  // session: teammates on the shared A11 ride Jon's cached Cloudflare login, so a CF email of Jon's
  // must never exempt (or blocklist) whoever is actually signed in to MC.
  const isJon = session ? JON_EMAILS.has(email) : JON_EMAILS.has(cfEmail);
  return { key, email, cfEmail, ip, userId: session && session.userId, name: session && session.name,
    role: session && session.role, ua: (h['user-agent'] || '').toString().slice(0, 200),
    country: (h['cf-ipcountry'] || '').toString(), exempt: automation || isJon, automation, isJon };
}

// ── rolling metrics per identity (minute buckets, 60 min) ──
const tracks = new Map();   // key -> { mins: Map(minute -> {req,denied,dl,bytes}), recs: Map(hour->Set), ips:Set, ua, peak, last }
function track(id) {
  let t = tracks.get(id.key);
  if (!t) { t = { mins: new Map(), recs: new Map(), dlFiles: new Map(), ips: new Set(), uaAuto: false, peak: 0, lastAlertTier: 0, lastAlertAt: 0, id }; tracks.set(id.key, t); }
  t.id = id; return t;
}
function minuteBucket(t, m) { let b = t.mins.get(m); if (!b) { b = { req: 0, denied: 0, dl: 0, bytes: 0 }; t.mins.set(m, b); } return b; }
function recordIds(url) {
  const out = [];
  const [p, q] = url.split('?');
  for (const seg of p.split('/')) if (/^\d{2,}$/.test(seg) || /^[0-9a-f-]{12,}$/i.test(seg) || /^[A-Z]{1,4}-\d{2,}$/.test(seg)) out.push(p.replace(seg, ':' + seg));
  if (q) { const sp = new URLSearchParams(q); for (const k of ['id', 'task', 'task_id', 'contact', 'deal', 'doc', 'file', 'key', 'opp', 'person']) { const v = sp.get(k); if (v) out.push(p + '?' + k + '=' + v); } }
  return out;
}
function score(t, now) {
  const m = Math.floor(now / 60000);
  let rpm = 0, denied10 = 0, dlHr = 0, bytesHr = 0;
  for (const [k, b] of t.mins) {
    if (k < m - 60) { t.mins.delete(k); continue; }
    if (k === m || k === m - 1) rpm = Math.max(rpm, b.req);
    if (k > m - 10) denied10 += b.denied;
    dlHr += b.dl; bytesHr += b.bytes;
  }
  const h = Math.floor(now / 3600000);
  for (const k of t.recs.keys()) if (k < h - 1) t.recs.delete(k);
  const recsHr = (t.recs.get(h) || new Set()).size;
  const reasons = []; let s = 0;
  const add = (pts, why) => { s += pts; reasons.push(why); };
  if (rpm > T.rpm[1]) add(60, `rate ${rpm}/min`); else if (rpm > T.rpm[0]) add(30, `rate ${rpm}/min`);
  if (recsHr > T.records_hr[1]) add(50, `${recsHr} distinct records/hr`); else if (recsHr > T.records_hr[0]) add(25, `${recsHr} distinct records/hr`);
  if (dlHr > T.downloads_hr[1]) add(50, `${dlHr} downloads/hr`); else if (dlHr > T.downloads_hr[0]) add(25, `${dlHr} downloads/hr`);
  if (bytesHr > T.mb_hr * 1e6) add(20, `${Math.round(bytesHr / 1e6)} MB/hr`);
  if (denied10 > T.denied_10m[1]) add(40, `${denied10} denied/10min`); else if (denied10 > T.denied_10m[0]) add(20, `${denied10} denied/10min`);
  if (t.uaAuto) add(40, 'automated client user-agent');
  const hrCT = Number(new Intl.DateTimeFormat('en-US', { timeZone: 'America/Chicago', hour: 'numeric', hourCycle: 'h23' }).format(now));
  if (hrCT >= 0 && hrCT < 5 && rpm > 10) add(10, 'active 00:00–05:00 CT');
  if (t.id.country && t.id.country !== 'US') add(20, `country ${t.id.country}`);
  if (t.newIp) add(10, 'new IP for this identity');
  return { score: s, reasons, rpm, recsHr, dlHr, mbHr: Math.round(bytesHr / 1e6), denied10 };
}

// ── hourly aggregates for tuning + weekly report (flushed every 5 min) ──
const agg = new Map();  // hour|key -> row
function aggRow(id, now) {
  const hour = new Date(Math.floor(now / 3600000) * 3600000).toISOString();
  const k = hour + '|' + id.key;
  let r = agg.get(k);
  if (!r) { r = { hour, key: id.key, email: id.email || id.cfEmail || '', role: id.role || '', automation: id.automation, req: 0, denied: 0, downloads: 0, bytes: 0, records: new Set(), peak_score: 0, peak_rpm: 0, ua_auto: false, ips: new Set() }; agg.set(k, r); }
  return r;
}
function flushAgg(all) {
  const curHour = new Date(Math.floor(Date.now() / 3600000) * 3600000).toISOString();
  const lines = [];
  for (const [k, r] of agg) {
    if (!all && r.hour === curHour) continue;
    lines.push(JSON.stringify(Object.assign({}, r, { records: r.records.size, ips: [...r.ips].slice(0, 10) })));
    agg.delete(k);
  }
  if (lines.length) try { fs.appendFileSync(HOURLY, lines.join('\n') + '\n'); } catch (e) {}
}
setInterval(() => flushAgg(false), 5 * 60000).unref();
process.on('exit', () => flushAgg(true));

// ── Known IPs per identity (new-IP signal), persisted lightly ──
const KNOWN_IPS_FILE = path.join(LOG_DIR, 'known-ips.json');
let knownIps = {}; try { knownIps = JSON.parse(fs.readFileSync(KNOWN_IPS_FILE, 'utf8')); } catch (e) {}
let knownDirty = false;
setInterval(() => { if (knownDirty) { knownDirty = false; try { fs.writeFileSync(KNOWN_IPS_FILE, JSON.stringify(knownIps)); } catch (e) {} } }, 60000).unref();

// ── Cloudflare revoke / restore (async https) ──
function cfToken() { try { return JSON.parse(fs.readFileSync(path.join(process.env.HOME || '/Users/exomac', '.openclaw', 'secrets.json'), 'utf8')).cloudflare_zt_token || ''; } catch (e) { return ''; } }
function cfApi(method, p, body) {
  return new Promise((resolve) => {
    const tok = cfToken(); if (!tok) return resolve({ ok: false, error: 'no token' });
    const data = body ? JSON.stringify(body) : null;
    const r = https.request({ host: 'api.cloudflare.com', path: '/client/v4' + p, method, timeout: 15000,
      headers: Object.assign({ Authorization: 'Bearer ' + tok, 'Content-Type': 'application/json' }, data ? { 'Content-Length': Buffer.byteLength(data) } : {}) }, (res) => {
      let b = ''; res.on('data', c => b += c); res.on('end', () => { try { const j = JSON.parse(b); resolve({ ok: !!j.success, result: j.result, error: j.errors }); } catch (e) { resolve({ ok: false, error: b.slice(0, 200) }); } });
    });
    r.on('error', e => resolve({ ok: false, error: e.message })); r.on('timeout', () => { r.destroy(); resolve({ ok: false, error: 'timeout' }); });
    if (data) r.write(data); r.end();
  });
}
async function cfRevoke(emails) {
  if (process.env.MC_GUARD_NO_CF) return { revoked: [], removed_from_policy: [], errors: ['test: CF skipped'] };
  const out = { revoked: [], removed_from_policy: [], errors: [] };
  const pol = await cfApi('GET', `/accounts/${CF_ACC}/access/apps/${CF_APP}/policies/${CF_POLICY}`);
  if (pol.ok && pol.result) {
    const inc = pol.result.include || [];
    const keep = inc.filter(i => !(i.email && emails.includes((i.email.email || '').toLowerCase())));
    if (keep.length !== inc.length) {
      const put = await cfApi('PUT', `/accounts/${CF_ACC}/access/apps/${CF_APP}/policies/${CF_POLICY}`,
        { name: pol.result.name, decision: pol.result.decision, include: keep, exclude: pol.result.exclude || [], require: pol.result.require || [] });
      if (put.ok) out.removed_from_policy = inc.filter(i => !keep.includes(i)).map(i => i.email.email); else out.errors.push('policy PUT: ' + JSON.stringify(put.error).slice(0, 150));
    }
  } else out.errors.push('policy GET: ' + JSON.stringify(pol.error).slice(0, 150));
  for (const e of emails) {
    const r = await cfApi('POST', `/accounts/${CF_ACC}/access/organizations/revoke_user`, { email: e });
    if (r.ok) out.revoked.push(e); else out.errors.push('revoke ' + e + ': ' + JSON.stringify(r.error).slice(0, 150));
  }
  return out;
}

// ── lockout ──
let deps = null;   // { sessions, saveSessions, loadUsers, saveUsers }
function lockout(id, reason, evidenceData) {
  loadState(true);
  if (state.locked[id.key]) return;
  const users = deps.loadUsers();
  const u = id.userId ? users.find(x => x.id === id.userId) : null;
  if (u) { u.active = false; u.guard_locked = { at: new Date().toISOString(), reason }; deps.saveUsers(users); }
  for (const [tok, s] of deps.sessions.entries()) if (id.userId && s.userId === id.userId) deps.sessions.delete(tok);
  deps.saveSessions();
  const emails = [...new Set([id.email, id.cfEmail].filter(e => e && !JON_EMAILS.has(e)))];
  state.locked[id.key] = { at: new Date().toISOString(), reason, userId: id.userId || null, name: id.name || null, emails, ip: id.ip, cf: 'pending' };
  saveState();
  evidence({ event: 'LOCKOUT', key: id.key, reason, identity: id, evidence: evidenceData });
  const who = id.name ? `${id.name} (${id.email})` : (id.cfEmail || id.ip);
  const ev = evidenceData ? '\n' + evidenceData.slice(0, 1400) : '';
  cfRevoke(emails).then(r => {
    loadState(true);
    if (state.locked[id.key]) { state.locked[id.key].cf = r; saveState(); }
    evidence({ event: 'CF_REVOKE', key: id.key, result: r });
    dmJon(`🚨 **MC GUARD — LOCKOUT: ${who}**\nReason: ${reason}\nFrom: ${id.ip}${id.country ? ' (' + id.country + ')' : ''} · UA: ${id.ua.slice(0, 80)}\nDone: MC account deactivated, all sessions killed, Cloudflare ${r.revoked.length ? 'access revoked' : 'revoke FAILED (' + r.errors.join('; ').slice(0, 120) + ') — MC blocklist still holds'}.${ev}\nTo restore: tell me "unlock ${id.key}" (only you can).`);
  });
}

// ── public API ──
function init(d) { deps = d; loadState(true); if (!fs.existsSync(STATE_FILE)) saveState(); adminToken(); }

// Returns true if the request was handled (blocked). Call at the top of the request handler.
function check(req, res, session) {
  try {
    loadState();
    const now = Date.now();
    const url = req.url || '';
    const p = url.split('?')[0];
    const id = identify(req, session);

    if (p === '/robots.txt') { res.writeHead(200, { 'Content-Type': 'text/plain' }); res.end(ROBOTS); return true; }

    // Blocklist: locked identities (by MC user, CF email, or IP-key) get nothing.
    const lockedHit = state.locked[id.key] || (id.cfEmail && state.locked['cf:' + id.cfEmail])
      || Object.values(state.locked).find(l => l.emails && ((id.email && l.emails.includes(id.email)) || (id.cfEmail && l.emails.includes(id.cfEmail))));
    if (lockedHit && !id.exempt) {
      res.writeHead(403, { 'Content-Type': 'text/html' });
      res.end('<html><body style="font-family:system-ui;background:#111;color:#ddd;padding:40px"><h2>Access suspended</h2><p>This account\'s access to Exos Mission Control has been suspended. Contact John Quinn.</p></body></html>');
      return true;
    }

    // Tripwires.
    if (TRIPWIRE_EXACT.has(p)) {
      const ev = `Tripwire: ${req.method} ${url.slice(0, 200)}`;
      if (id.exempt) {
        evidence({ event: 'TRIPWIRE_EXEMPT', key: id.key, url: url.slice(0, 300), identity: id });
        if (!id.automation) dmJon(`⚠️ MC GUARD: tripwire hit by an exempt identity (${id.email || id.cfEmail || id.ip}) — ${req.method} ${p}. Alert only, no lockout.`);
      } else {
        lockout(id, 'Tripwire hit', ev + `\nUser-agent: ${id.ua}`);
      }
      res.writeHead(404); res.end('Not Found');
      return true;
    }

    if (id.automation) return false;   // on-box jobs: not scored

    // Metrics.
    const t = track(id);
    const b = minuteBucket(t, Math.floor(now / 60000));
    b.req++;
    if (AUTOMATION_UA.test(id.ua)) t.uaAuto = true;
    if (id.ip && !(knownIps[id.key] || []).includes(id.ip)) {
      const had = (knownIps[id.key] || []).length > 0;
      knownIps[id.key] = [...(knownIps[id.key] || []), id.ip].slice(-20); knownDirty = true;
      t.newIp = had;
    }
    const hk = Math.floor(now / 3600000);
    let rs = t.recs.get(hk); if (!rs) { rs = new Set(); t.recs.set(hk, rs); }
    const row = aggRow(id, now);
    for (const r of recordIds(url)) { rs.add(r); row.records.add(r); }
    const isDl = DOWNLOAD_RE.test(p);
    if (isDl) { b.dl++; row.downloads++; }
    row.req++; row.ips.add(id.ip); if (t.uaAuto) row.ua_auto = true;

    res.on('finish', () => {
      try {
        const code = res.statusCode;
        if (code === 401 || code === 403 || (code === 404 && p.startsWith('/api/'))) { b.denied++; row.denied++; }
        const len = Number(res.getHeader('content-length')) || res._guardBytes || 0;
        if (isDl && len) { b.bytes += len; row.bytes += len; }
      } catch (e) {}
    });

    const sc = score(t, now);
    row.peak_score = Math.max(row.peak_score, sc.score); row.peak_rpm = Math.max(row.peak_rpm, sc.rpm);
    const tier = sc.score >= T.high ? 3 : sc.score >= T.medium ? 2 : sc.score > 0 ? 1 : 0;
    const enforce = state.scoring_mode === 'enforce';
    // Enforce mode: HIGH always locks out (independent of the alert de-dupe below).
    if (tier === 3 && enforce && !id.exempt) {
      evidence({ event: 'SCORE_HIGH', mode: 'enforce', key: id.key, identity: id, score: sc });
      lockout(id, `Behavior score ${sc.score}`, `Signals: ${sc.reasons.join(', ')}`);
      res.writeHead(403, { 'Content-Type': 'text/plain' }); res.end('Access suspended');
      return true;
    }
    if (tier >= 2 && (tier > t.lastAlertTier || now - t.lastAlertAt > 3600000)) {
      t.lastAlertTier = tier; t.lastAlertAt = now;
      evidence({ event: tier === 3 ? 'SCORE_HIGH' : 'SCORE_MEDIUM', mode: state.scoring_mode, key: id.key, identity: id, score: sc });
      const who = id.name ? `${id.name} (${id.email})` : (id.cfEmail || id.ip);
      if (enforce || tier === 3) {
        // Watch mode: only HIGH is surfaced (as "would have acted"); MEDIUM stays in the logs.
        if (!id.isJon) dmJon(`${enforce ? '⚠️' : '👁️'} MC GUARD ${enforce ? '' : '[watch-only, no action taken] '}— ${tier === 3 ? 'HIGH' : 'MEDIUM'} risk score ${sc.score} for ${who}: ${sc.reasons.join(', ')}.`);
      }
    }
    // Enforce-mode throttle for medium+: cap at the medium request rate.
    if (enforce && !id.exempt && tier >= 2 && sc.rpm > T.rpm[0]) {
      res.writeHead(429, { 'Content-Type': 'application/json', 'Retry-After': '30' }); res.end('{"error":"Slow down"}');
      return true;
    }
    t.lastScore = sc;
  } catch (e) { /* guard must never break MC */ }
  return false;
}

// Hidden bait anchors for HTML pages.
function injectBait(html) {
  const bi = html.lastIndexOf('</body>');
  return bi !== -1 ? html.slice(0, bi) + HIDDEN_LINKS + html.slice(bi) : html + HIDDEN_LINKS;
}

// ── traceable copies ──
function traceBuffer(buf, ext, session, req, fileName) {
  try {
    const id = identify(req, session);
    const trace = crypto.createHmac('sha256', SECRET).update(`${id.key}|${Date.now()}|${fileName}|${crypto.randomBytes(4).toString('hex')}`).digest('hex').slice(0, 16);
    const tag = `EXOS-TRACE ${trace}`;
    let out = buf;
    if (ext === '.pdf') out = Buffer.concat([buf, Buffer.from(`\n%${tag}\n`)]);
    else if (['.docx', '.xlsx', '.pptx', '.zip'].includes(ext)) {
      // Set the ZIP archive comment in the End-Of-Central-Directory record (valid per spec).
      const i = buf.lastIndexOf(Buffer.from([0x50, 0x4b, 0x05, 0x06]));
      if (i !== -1 && i + 22 === buf.length && buf.readUInt16LE(i + 20) === 0) {
        const c = Buffer.from(tag); const eocd = Buffer.from(buf.subarray(i, i + 22)); eocd.writeUInt16LE(c.length, 20);
        out = Buffer.concat([buf.subarray(0, i), eocd, c]);
      }
    }
    const rec = { ts: new Date().toISOString(), trace, marked: out !== buf, key: id.key, email: id.email || id.cfEmail, ip: id.ip, file: fileName, sha256: crypto.createHash('sha256').update(out).digest('hex'), bytes: out.length };
    fs.appendFile(TRACE_LEDGER, JSON.stringify(rec) + '\n', () => {});
    return out;
  } catch (e) { return buf; }
}

// Admin/Jon-only unlock (also used by scripts/mc_guard.py via the state file).
async function unlock(key, byEmail) {
  loadState(true);
  const l = state.locked[key]; if (!l) return { ok: false, error: 'not locked' };
  const users = deps.loadUsers();
  if (l.userId) { const u = users.find(x => x.id === l.userId); if (u) { u.active = true; delete u.guard_locked; deps.saveUsers(users); } }
  const restored = [];
  const removed = (l.cf && l.cf.removed_from_policy) || [];
  if (removed.length) {
    const pol = await cfApi('GET', `/accounts/${CF_ACC}/access/apps/${CF_APP}/policies/${CF_POLICY}`);
    if (pol.ok) {
      const inc = pol.result.include || [];
      for (const e of removed) if (!inc.some(i => i.email && i.email.email.toLowerCase() === e)) { inc.push({ email: { email: e } }); restored.push(e); }
      await cfApi('PUT', `/accounts/${CF_ACC}/access/apps/${CF_APP}/policies/${CF_POLICY}`, { name: pol.result.name, decision: pol.result.decision, include: inc, exclude: pol.result.exclude || [], require: pol.result.require || [] });
    }
  }
  delete state.locked[key]; saveState();
  tracks.delete(key);
  evidence({ event: 'UNLOCK', key, by: byEmail, cf_restored: restored });
  return { ok: true, cf_restored: restored };
}
// On-box admin (Exo acting on Jon's explicit instruction via scripts/mc_guard.py): loopback only,
// no Cloudflare headers, and the 0600 token file. External traffic can never satisfy this.
const ADMIN_TOKEN_FILE = path.join(ROOT, 'data', '.guard-admin-token');
function adminToken() {
  try { return fs.readFileSync(ADMIN_TOKEN_FILE, 'utf8').trim(); }
  catch (e) { const t = crypto.randomBytes(24).toString('hex'); try { fs.writeFileSync(ADMIN_TOKEN_FILE, t, { mode: 0o600 }); } catch (e2) {} return t; }
}
function isOnBoxAdmin(req) {
  const id = identify(req, null);
  const tok = (req.headers['x-guard-token'] || '').toString();
  const want = adminToken();
  return id.automation && tok.length === want.length && crypto.timingSafeEqual(Buffer.from(tok), Buffer.from(want));
}
function status() { loadState(true); return { scoring_mode: state.scoring_mode, watch_started: state.watch_started, locked: state.locked, thresholds: T }; }

module.exports = { init, check, injectBait, traceBuffer, unlock, status, isOnBoxAdmin, JON_EMAILS, TRIPWIRE_EXACT };
