const fs = require('fs');
const path = require('path');
const { execSync, execFileSync } = require('child_process');
const http = require('http');
const https = require('https');
const nodemailer = require('nodemailer');

const PORT = 8080;
const MD_FILE = path.join(__dirname, '../exos-mission-control.md');
const CRM_FILE = path.join(__dirname, 'crm-data.json');
const UPLOADS_DIR = path.join(__dirname, 'uploads');
const UPLOADS_META = path.join(__dirname, 'uploads', '_meta.json');
const MAX_UPLOAD_SIZE = 25 * 1024 * 1024; // 25 MB
const ALLOWED_EXTENSIONS = ['.pdf','.docx','.xlsx','.pptx','.doc','.xls','.ppt','.png','.jpg','.jpeg','.gif','.svg','.csv','.txt','.zip','.md'];

// ── DECISIONS INBOX: consolidated "Needs Jon" approval queue ──
const DECISIONS_FILE = path.join(__dirname, 'data', 'decisions.json');
const DOSSIERS_FILE = path.join(__dirname, 'data', 'dossiers.json');
function loadDossiersFile() { try { return JSON.parse(fs.readFileSync(DOSSIERS_FILE, 'utf-8')); } catch { return { dossiers: [] }; } }
function saveDossiersFile(o) { fs.writeFileSync(DOSSIERS_FILE, JSON.stringify(o, null, 2)); }
const DTOKEN_FILE = path.join(__dirname, 'data', '.decisions-token');
function loadDecisions() { try { return JSON.parse(fs.readFileSync(DECISIONS_FILE, 'utf-8')); } catch { return []; } }
function saveDecisions(arr) {
  fs.mkdirSync(path.dirname(DECISIONS_FILE), { recursive: true });
  // Anti-wipe guard: loadDecisions() returns [] on a corrupt/unreadable file, so a load→push→save
  // cycle could otherwise overwrite the whole store with a near-empty set (this actually happened
  // 2026-09-04). Refuse to catastrophically shrink: if the on-disk store is substantial (parseable
  // >25 items, or unparseable but >5KB) and the incoming set is <50% of it, back up and refuse.
  try {
    if (fs.existsSync(DECISIONS_FILE)) {
      const raw = fs.readFileSync(DECISIONS_FILE, 'utf-8');
      let cur = null; try { cur = JSON.parse(raw); } catch {}
      const curLen = Array.isArray(cur) ? cur.length : null;
      const bigOnDisk = curLen === null ? raw.length > 5000 : curLen > 25;
      if (bigOnDisk && (curLen === null || arr.length < curLen * 0.5)) {
        fs.copyFileSync(DECISIONS_FILE, DECISIONS_FILE + '.bak-shrinkguard-' + Date.now());
        throw new Error('saveDecisions refused: on-disk has ' +
          (curLen === null ? ('unparseable ~' + raw.length + 'B') : (curLen + ' items')) +
          ', incoming set has ' + arr.length + ' — backed up, NOT overwriting');
      }
    }
  } catch (e) { if (String(e.message).startsWith('saveDecisions refused')) throw e; }
  const tmp = DECISIONS_FILE + '.tmp-' + process.pid;
  fs.writeFileSync(tmp, JSON.stringify(arr, null, 2));
  fs.renameSync(tmp, DECISIONS_FILE);   // atomic replace
}

// ── Research & Intel feed ──
const RESEARCH_FILE = path.join(__dirname, 'data', 'research.json');
const RESEARCH_INGEST_FILE = path.join(__dirname, 'data', 'research-ingest.json');
function loadResearch() { try { return JSON.parse(fs.readFileSync(RESEARCH_FILE, 'utf-8')); } catch { return { briefs: [], count: 0 }; } }
function loadResearchIngest() { try { return JSON.parse(fs.readFileSync(RESEARCH_INGEST_FILE, 'utf-8')); } catch { return []; } }
function saveResearchIngest(arr) { fs.mkdirSync(path.dirname(RESEARCH_INGEST_FILE), { recursive: true }); fs.writeFileSync(RESEARCH_INGEST_FILE, JSON.stringify(arr, null, 2)); }

// Build a lookup of related items (opportunities + MC tasks) for value/deadline enrichment
function loadDecisionRefIndex() {
  const idx = {};
  for (const file of ['opportunities.json', 'tasks.json']) {
    try {
      const raw = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', file), 'utf-8'));
      const arr = Array.isArray(raw) ? raw : (raw.opportunities || raw.tasks || []);
      for (const it of arr) { if (it && it.id) idx[it.id] = it; }
    } catch {}
  }
  return idx;
}

// Parse a dollar value (supports K/M/B) from free text → absolute number
function parseDollarValue(text) {
  if (!text) return 0;
  let best = 0;
  const re = /\$\s*([\d,]+(?:\.\d+)?)\s*([KkMmBb])?/g; let m;
  while ((m = re.exec(text))) {
    let n = parseFloat(m[1].replace(/,/g, ''));
    const suf = (m[2] || '').toLowerCase();
    if (suf === 'k') n *= 1e3; else if (suf === 'm') n *= 1e6; else if (suf === 'b') n *= 1e9;
    if (n > best) best = n;
  }
  return best;
}

// Deadline urgency score from free text + an optional explicit due date (0 = none, higher = sooner)
function deadlineUrgency(text, dueDate) {
  let score = 0;
  const t = (text || '').toLowerCase();
  if (/overdue|past due|missed/.test(t)) score = Math.max(score, 100);
  if (/\btoday\b|\bnow\b|asap|immediately/.test(t)) score = Math.max(score, 95);
  if (/tomorrow/.test(t)) score = Math.max(score, 90);
  if (/this week|\bdue\b|deadline/.test(t)) score = Math.max(score, 70);
  if (/next week/.test(t)) score = Math.max(score, 50);
  // Explicit date (from decision text or linked item) → days-until urgency
  const dm = (text || '').match(/\b(20\d{2}-\d{2}-\d{2})\b/);
  const iso = dm ? dm[1] : (dueDate && /^\d{4}-\d{2}-\d{2}/.test(dueDate) ? dueDate.slice(0, 10) : null);
  if (iso) {
    const days = Math.floor((new Date(iso) - new Date()) / 86400000);
    let dScore;
    if (days < 0) dScore = 100;
    else if (days === 0) dScore = 95;
    else if (days <= 2) dScore = 88;
    else if (days <= 7) dScore = 72;
    else if (days <= 14) dScore = 55;
    else if (days <= 30) dScore = 40;
    else dScore = 25;
    score = Math.max(score, dScore);
  }
  return score;
}

// Parse a submittal deadline from free-text `due` → {iso, label, bucket}.
// Handles ISO dates, "July 9", "Sep 5, 2026", "9 July", ranges ("June 4 → July 9").
// When no year is given, infers the soonest upcoming year. todayUTC = Date.UTC of today.
function parseSubmittalDeadline(due, todayUTC) {
  const raw = (due || '').toString().trim();
  if (!raw) return { iso: null, label: 'No date set', bucket: 'tbd' };
  const low = raw.toLowerCase();
  const M = { jan:0,feb:1,mar:2,apr:3,may:4,jun:5,jul:6,aug:7,sep:8,sept:8,oct:9,nov:10,dec:11,
    january:0,february:1,march:2,april:3,june:5,july:6,august:7,september:8,october:9,november:10,december:11 };
  const Y = new Date(todayUTC).getUTCFullYear();
  const past = (t) => t < todayUTC - 7*86400000;
  const cands = [];
  let m;
  const re1 = /\b(20\d{2})-(\d{1,2})-(\d{1,2})\b/g;
  while ((m=re1.exec(raw))) cands.push(Date.UTC(+m[1],+m[2]-1,+m[3]));
  const re2 = /\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})(?!\d)(?:\s*,?\s*(20\d{2}))?/gi;
  while ((m=re2.exec(raw))) { const mo=M[m[1].toLowerCase()]; const d=+m[2]; let y=m[3]?+m[3]:Y; if(!m[3]&&past(Date.UTC(y,mo,d)))y++; if(mo!=null&&d>=1&&d<=31) cands.push(Date.UTC(y,mo,d)); }
  const re3 = /\b(\d{1,2})(?!\d)\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?(?:\s*,?\s*(20\d{2}))?/gi;
  while ((m=re3.exec(raw))) { const d=+m[1]; const mo=M[m[2].toLowerCase()]; let y=m[3]?+m[3]:Y; if(!m[3]&&past(Date.UTC(y,mo,d)))y++; if(mo!=null&&d>=1&&d<=31) cands.push(Date.UTC(y,mo,d)); }
  if (cands.length) {
    const future = cands.filter(c=>c>=todayUTC).sort((a,b)=>a-b);
    const hasRange = /→|–|—|->|\bto\b|through|window|thru/.test(low);
    let pick;
    if (future.length) pick = hasRange ? future[future.length-1] : future[0];
    else pick = Math.max.apply(null, cands);
    return { iso: new Date(pick).toISOString().slice(0,10), label: new Date(pick).toISOString().slice(0,10), bucket: 'dated' };
  }
  if (/rolling|ongoing|continuous|no posted deadline|accepts rolling|front door|open now|\bopen\b/.test(low))
    return { iso: null, label: 'Rolling / open', bucket: 'rolling' };
  return { iso: null, label: raw.length>44?raw.slice(0,44)+'…':raw, bucket: 'tbd' };
}

// Composite decision score: value of opportunity + deadline are the PRIMARY drivers,
// with the high/med/low label as a secondary baseline. Higher = sort first.
function decisionScore(d, refIdx) {
  const ref = d.relatedItem ? refIdx[d.relatedItem] : null;
  const text = [d.title, d.question, d.context, d.proposedAction].filter(Boolean).join(' ')
    + (ref ? ' ' + [ref.value, ref.description, ref.title, ref.next_action, ref.due].filter(Boolean).join(' ') : '');

  // 1) Opportunity value (primary). Prefer parsed $ from text/linked opp; fall back to linked numeric priority.
  const dollars = parseDollarValue(text);
  let valueScore = 0;
  if (dollars > 0) {
    // log scale: $50k→~24, $1M→~40, $10M→~52, $25M→~57, $100M+→~64 (capped 65)
    valueScore = Math.min(65, Math.max(0, (Math.log10(dollars) - 3) * 12));
  } else if (ref && typeof ref.priority === 'number') {
    valueScore = Math.min(65, ref.priority * 0.6); // linked item priority as value proxy
  }

  // 2) Deadline urgency (primary)
  const urgency = deadlineUrgency(text, ref && (ref.due_date || ref.due));

  // 3) Label baseline (secondary)
  const labelBase = { high: 30, med: 15, low: 5 }[d.priority] ?? 15;

  // Weighting: value + deadline dominate; label is a tiebreak-level baseline.
  return Math.round(valueScore * 1.0 + urgency * 0.8 + labelBase * 0.5);
}
function decisionsToken() {
  try { return fs.readFileSync(DTOKEN_FILE, 'utf-8').trim(); }
  catch {
    const t = crypto.randomBytes(24).toString('hex');
    fs.mkdirSync(path.dirname(DTOKEN_FILE), { recursive: true });
    fs.writeFileSync(DTOKEN_FILE, t, { mode: 0o600 });
    return t;
  }
}
// R-017 (Decisions Matrix Daily Update cron) reads/closes decisions headlessly via X-Exo-Token —
// it has no login session cookie. GET /api/decisions and POST /api/decisions/answer are otherwise
// session-gated for per-user scoping; this lets a valid token stand in as the cron's identity on
// ONLY those two exact paths (checked below), without weakening session auth anywhere else.
function isDecisionsCronToken(req) {
  return (req.headers['x-exo-token'] || '') === decisionsToken();
}
// Streaming backup download (see /backup/ route). Files live here; token gates access.
const BACKUP_DL_DIR = path.join(process.env.HOME || '/Users/exomac', 'exos-asset-backups', '_download');
const BTOKEN_FILE = path.join(__dirname, 'data', '.backup-token');
// Capstone/sandbox access audit: log every DENIED request by a sandboxed (early_adopter) user so
// scripts/capstone_access_monitor.py can alert Lizi/Jon on privilege-escalation probing.
const CAPSTONE_AUDIT = path.join(__dirname, '..', 'logs', 'capstone-access-audit.jsonl');
function auditDeny(session, req, reason) {
  try {
    const ip = (req.headers['x-forwarded-for'] || (req.socket && req.socket.remoteAddress) || '').toString().split(',')[0].trim();
    fs.appendFileSync(CAPSTONE_AUDIT, JSON.stringify({
      ts: new Date().toISOString(), reason,
      userId: session && session.userId, email: session && session.email, role: session && session.role,
      method: req.method, url: (req.url || '').slice(0, 300), ip,
    }) + '\n');
  } catch {}
}
function backupToken() {
  try { return fs.readFileSync(BTOKEN_FILE, 'utf-8').trim(); }
  catch {
    const t = crypto.randomBytes(24).toString('hex');
    fs.mkdirSync(path.dirname(BTOKEN_FILE), { recursive: true });
    fs.writeFileSync(BTOKEN_FILE, t, { mode: 0o600 });
    return t;
  }
}
function nextDecisionId(arr) {
  let max = 0;
  for (const d of arr) { const m = /^D-(\d+)$/.exec(d.id || ''); if (m) max = Math.max(max, parseInt(m[1], 10)); }
  return 'D-' + String(max + 1).padStart(3, '0');
}

// ── E-SIGN: storage + helpers ──
const ENVELOPES_FILE = path.join(__dirname, 'data', 'envelopes.json');
function esignToken() { return crypto.randomBytes(20).toString('hex'); }
function loadEnvelopes() { try { return JSON.parse(fs.readFileSync(ENVELOPES_FILE, 'utf-8')); } catch { return []; } }
function saveEnvelopes(arr) { fs.mkdirSync(path.dirname(ENVELOPES_FILE), { recursive: true }); fs.writeFileSync(ENVELOPES_FILE, JSON.stringify(arr, null, 2)); }
// ── MNDA registry (source of truth for the purple "MNDA on record" border; reused by CRM/ERP/dossiers) ──
function loadMndaRegistry() { try { return JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'mnda-registry.json'), 'utf-8')); } catch { return {}; } }
function _mndaNorm(s) { return String(s || '').toLowerCase().replace(/[^a-z0-9]/g, ''); }
function mndaForCompany(company) {
  const key = _mndaNorm(company); if (!key) return null;
  const reg = loadMndaRegistry();
  if (reg[key]) return reg[key];
  // conservative fuzzy: prefix match where the shorter name is >=50% of the longer
  // (blocks "appian" bleeding into "appianwaycapitalpartners"), min length 4.
  for (const k of Object.keys(reg)) {
    if (k.length < 4 || key.length < 4) continue;
    const [a, b] = key.length <= k.length ? [key, k] : [k, key];
    if (b.startsWith(a) && a.length / b.length >= 0.5) return reg[k];
  }
  return null;
}

// ── Payload-customer registry (former/active PAYING payload customers; joined onto CRM/company rows) ──
// Source of truth for the green "Payload Customer" flag. Keyed by normalized company name (mirrors MNDA).
// Each record captures high-level CONTRACT + PAYLOAD detail and the SIGNED-CONTRACT reference so Mission
// Control reports TRUE customer metrics (who paid, how many payloads, total contract $ vs paid $).
// Exo updates it any time a customer pays — via POST /api/payload-customers or scripts/payload_customer.py.
const PAYLOAD_CUSTOMERS_FILE = path.join(__dirname, 'data', 'payload-customers.json');
function loadPayloadCustomers() { try { return JSON.parse(fs.readFileSync(PAYLOAD_CUSTOMERS_FILE, 'utf-8')); } catch { return {}; } }
function savePayloadCustomers(reg) { fs.mkdirSync(path.dirname(PAYLOAD_CUSTOMERS_FILE), { recursive: true }); fs.writeFileSync(PAYLOAD_CUSTOMERS_FILE, JSON.stringify(reg, null, 2)); }
function payloadCustomerForCompany(company) {
  const key = _mndaNorm(company); if (!key) return null;
  const reg = loadPayloadCustomers();
  if (reg[key]) return reg[key];
  for (const k of Object.keys(reg)) {
    if (k.length < 4 || key.length < 4) continue;
    const [a, b] = key.length <= k.length ? [key, k] : [k, key];
    if (b.startsWith(a) && a.length / b.length >= 0.5) return reg[k];
  }
  return null;
}
function recomputePayloadCustomer(rec) {
  const pls = Array.isArray(rec.payloads) ? rec.payloads : [];
  rec.is_payload_customer = pls.length > 0;
  rec.payload_count = pls.length;
  rec.total_contract_value_usd = pls.reduce((s, p) => s + (Number(p.contract_value_usd) || 0), 0);
  rec.total_paid_usd = pls.reduce((s, p) => s + (Number(p.amount_paid_usd) || 0), 0);
  const paid = pls.map(p => p.paid_date).filter(Boolean).sort();
  rec.customer_since = paid[0] || rec.customer_since || null;
  rec.last_payload_date = paid[paid.length - 1] || rec.last_payload_date || null;
  return rec;
}
function payloadCustomerMetrics(reg) {
  const recs = Object.values(reg).filter(r => r && r.is_payload_customer);
  return {
    total_customers: recs.length,
    repeat_customers: recs.filter(r => (r.payload_count || 0) > 1).length,
    total_payloads: recs.reduce((s, r) => s + (r.payload_count || 0), 0),
    total_contract_value_usd: recs.reduce((s, r) => s + (r.total_contract_value_usd || 0), 0),
    total_paid_usd: recs.reduce((s, r) => s + (r.total_paid_usd || 0), 0),
    customers: recs.map(r => ({ company: r.company, payloads: r.payload_count || 0,
      contract_value_usd: r.total_contract_value_usd || 0, paid_usd: r.total_paid_usd || 0,
      customer_since: r.customer_since || null,
      signed_contracts: (r.payloads || []).filter(p => p.signed_contract_ref).length }))
      .sort((a, b) => (a.customer_since || '').localeCompare(b.customer_since || '')),
  };
}

function esignTransport() {
  const cert = fs.existsSync('/Users/exomac/.protonmail-bridge.crt') ? fs.readFileSync('/Users/exomac/.protonmail-bridge.crt') : undefined;
  return nodemailer.createTransport({ host: '127.0.0.1', port: 1025, secure: false, requireTLS: true, tls: { ca: cert, rejectUnauthorized: false }, auth: { user: 'jquinnexo@pm.me', pass: 'SPqYBivj98-jyF3RujLKxA' } });
}
function esignRequestEmail(signer, link, env) {
  return `<div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;">
    <div style="background:#0a1628;padding:20px 24px;border-radius:8px 8px 0 0;"><h2 style="color:#f5a623;margin:0;font-size:18px;">Exos Aerospace — Signature Requested</h2></div>
    <div style="background:#fff;padding:24px;border:1px solid #ddd;color:#333;line-height:1.6;">
      <p>Hi ${(signer.name||'there').split(/\s+/)[0]},</p>
      <p>${(env.message||'You have a document ready for your signature.').replace(/\n/g,'<br>')}</p>
      <p style="margin:24px 0;"><a href="${link}" style="background:#0066cc;color:#fff;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:bold;display:inline-block;">Review &amp; Sign: ${env.title}</a></p>
      <p style="font-size:12px;color:#888;">Or paste this link into your browser:<br><span style="color:#0066cc;">${link}</span></p>
      <p style="font-size:13px;color:#c0392b;font-weight:bold;">⏳ This secure link expires in 5 days${env.expiresAt ? ' (on ' + new Date(env.expiresAt).toLocaleDateString('en-US',{month:'long',day:'numeric',year:'numeric'}) + ')' : ''} — please sign before then.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
      <p style="font-size:11px;color:#999;">This is a legally binding electronic signature request under the U.S. E-SIGN Act (15 U.S.C. §7001) and UETA. Your signature, name, IP address, and timestamp will be recorded. Questions: <a href="mailto:jquinn@exosaero.com">jquinn@exosaero.com</a>.</p>
    </div>
    <div style="background:#f5f5f5;padding:12px 24px;border-radius:0 0 8px 8px;border:1px solid #ddd;border-top:none;"><p style="font-size:11px;color:#999;margin:0;">Exos Aerospace Systems &amp; Technologies, Inc. | 299 FM 1903, Greenville, TX 75402</p></div>
  </div>`;
}
function esignCertificate(env) {
  const rows = env.signers.map(s => `
    <div style="margin:14px 0;padding:12px;border:1px solid #ddd;border-radius:6px;">
      <img src="${s.signatureData}" alt="signature" style="max-height:64px;display:block;margin-bottom:6px;">
      <div style="font-weight:bold;">${s.name}${s.role ? ' — ' + s.role : ''}</div>
      <div style="font-size:12px;color:#666;">Signed electronically: ${s.signedAt} · IP: ${s.ip||'n/a'} · Method: ${s.signatureType||'typed'}</div>
    </div>`).join('');
  return `<hr style="margin:28px 0;border:none;border-top:2px solid #0a1628;">
    <h2 style="color:#0a1628;">Signature Certificate</h2>${rows}
    <p style="font-size:12px;color:#666;">Executed electronically by the parties under the U.S. E-SIGN Act (15 U.S.C. §7001 et seq.) and the Uniform Electronic Transactions Act (UETA). Envelope ID: ${env.id} · Completed: ${env.completedAt||''}</p>`;
}
async function esignDeliverCompleted(env) {
  const t = esignTransport();
  const completedHtml = `<div style="font-family:Arial,sans-serif;max-width:760px;margin:0 auto;color:#222;">
    <div style="background:#0a1628;padding:18px 24px;border-radius:8px 8px 0 0;"><h2 style="color:#22c55e;margin:0;font-size:18px;">✓ Fully Executed — ${env.title}</h2></div>
    <div style="background:#fff;padding:24px;border:1px solid #ddd;">
      <p style="color:#333;">All parties have signed. The fully executed document and signature certificate are below.</p>
      <hr style="border:none;border-top:1px solid #eee;margin:18px 0;">
      <h3 style="color:#0a1628;">${env.title}</h3>
      ${env.html || ''}
      ${esignCertificate(env)}
    </div>
  </div>`;
  const recipients = Array.from(new Set(env.signers.map(s => s.email).concat(['jquinn@exosaero.com'])));
  const info = await t.sendMail({ from: '"Exos Aerospace — DocuSign" <jquinnexo@pm.me>', replyTo: 'jquinn@exosaero.com', to: recipients.join(', '), subject: 'Fully Executed: ' + env.title, html: completedHtml });
  console.log('[E-Sign] Completed doc delivered for envelope ' + env.id + ' to ' + recipients.join(', '));
  return info;
}

// Ensure uploads directory exists
if (!fs.existsSync(UPLOADS_DIR)) fs.mkdirSync(UPLOADS_DIR, { recursive: true });

function loadUploadsMeta() {
  try { return JSON.parse(fs.readFileSync(UPLOADS_META, 'utf-8')); }
  catch { return []; }
}
function saveUploadsMeta(meta) {
  fs.writeFileSync(UPLOADS_META, JSON.stringify(meta, null, 2));
}

// --- Office-doc -> PDF rendition for in-browser "Open" (viewing) ---
// Browsers can't render .docx/.doc inline; we generate a cached PDF so the
// Open button previews. Download still serves the original. docx/doc only —
// converted via macOS `textutil` (docx/doc -> html) + headless Chrome (html -> pdf),
// which is reliable here (LibreOffice/soffice hangs in this environment).
const PDF_CACHE_DIR = path.join(UPLOADS_DIR, '.pdfcache');
const CHROME_BIN = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
// Use the version-independent mise shim, NOT a node-version-pinned path. A hardcoded
// installs/node/<ver>/bin path silently drifts out of sync with the running gateway on every
// node bump (was pinned to 24.14.0 / v2026.6.34 while the gateway ran v2026.7.1-2 → chat agent
// version skew and intermittent "No reply." failures). The shim always resolves to the active
// openclaw, matching the running gateway.
const OPENCLAW_BIN = '/Users/exomac/.local/share/mise/shims/openclaw';
const PDF_CONVERTIBLE = ['.docx', '.doc', '.pptx', '.ppt'];

// ── Exobot chat: async job store so answers survive page navigation ──
// The global chat widget (exobot-widget.js) POSTs a question, gets a jobId back
// immediately, then polls /api/chat/result. The agent runs in the background here
// keyed by jobId; the reply lands whatever page the user is on. Jobs are per-user
// (email-scoped) and expire after ~20 min to bound memory.
const chatJobs = new Map();  // jobId -> { email, skey, isMain, status:'pending'|'done', reply, ts }
const chatMainBusy = new Set();   // emails whose MAIN continuity session has a job in flight
const CHAT_MAX_PARALLEL = 4;      // per-user concurrent question cap (guards runaway agent spawns)
function chatJobsGC() {
  const cutoff = Date.now() - 20 * 60 * 1000;
  for (const [id, j] of chatJobs) if (j.ts < cutoff) {
    if (j.isMain && j.status === 'pending') chatMainBusy.delete(j.email);
    chatJobs.delete(id);
  }
}
function chatPendingCount(email) {
  let n = 0; for (const j of chatJobs.values()) if (j.email === email && j.status === 'pending') n++; return n;
}
// Lane assignment: the FIRST in-flight question uses the user's persistent continuity session
// (agent:main:mcchat-<slug>). A question fired while that one is still running forks into its own
// parallel lane (…-p<id>) so the two truly run at once without colliding on one session — like
// running a second task in a separate Discord channel. When the main lane frees, continuity resumes.
function chatAssignSession(email, jobId) {
  const slug = (email || 'anon').replace(/[^a-z0-9]+/gi, '-').toLowerCase();
  const mainKey = 'agent:main:mcchat-' + slug;
  if (!chatMainBusy.has(email)) { chatMainBusy.add(email); return { skey: mainKey, isMain: true }; }
  return { skey: mainKey + '-p' + jobId.slice(0, 6), isMain: false };
}
function runExobotChat(jobId, msg) {
  const job = chatJobs.get(jobId); if (!job) return;
  const tagged = `[Mission Control chat · ${job.email || 'user'}] ${msg}`;
  const { execFile } = require('child_process');
  const childEnv = { ...process.env, PATH: '/opt/homebrew/bin:' + (process.env.PATH || '/usr/bin:/bin') };
  execFile(OPENCLAW_BIN, ['agent', '--session-key', job.skey, '-m', tagged, '--json', '--timeout', '150'],
    { timeout: 165000, maxBuffer: 16 * 1024 * 1024, env: childEnv }, (err, stdout) => {
      let reply = '';
      try {
        // Tolerate any non-JSON prefix on stdout (e.g. a CLI version/upgrade warning that
        // bleeds to stdout): parse from the first '{' so a stray line never blanks the reply.
        const s = stdout.indexOf('{');
        const j = JSON.parse(s >= 0 ? stdout.slice(s) : stdout);
        reply = (j.result && Array.isArray(j.result.payloads) ? j.result.payloads.map(p => p && p.text).filter(Boolean).join('\n') : '')
          || (j.result && j.result.meta && j.result.meta.finalAssistantVisibleText) || '';
      } catch {}
      if (!reply) reply = err ? 'Exobot timed out or errored on that one — try again or use the email lane.' : 'No reply.';
      const cur = chatJobs.get(jobId) || job;
      cur.status = 'done'; cur.reply = reply; cur.ts = Date.now();
      chatJobs.set(jobId, cur);
      if (cur.isMain) chatMainBusy.delete(cur.email);   // free the continuity lane
    });
}
// docx -> HTML with EMBEDDED images (via mammoth). macOS `textutil` drops all embedded images
// (letterhead banners, diagrams, photos) from previews; mammoth keeps them. Kept as the primary
// path with a textutil fallback (mammoth is .docx-only / may be absent).
const DOCX2HTML = path.join(__dirname, '..', 'scripts', 'docx2html.py');
const PPTX2HTML = path.join(__dirname, '..', 'scripts', 'pptx2html.py');
function ensurePdfRendition(storedName) {
  const ext = path.extname(storedName).toLowerCase();
  if (!PDF_CONVERTIBLE.includes(ext)) return null;
  const src = path.join(UPLOADS_DIR, storedName);
  if (!src.startsWith(UPLOADS_DIR) || storedName.includes('..')) return null;
  if (!fs.existsSync(src) || !fs.statSync(src).isFile()) return null;
  if (!fs.existsSync(PDF_CACHE_DIR)) fs.mkdirSync(PDF_CACHE_DIR, { recursive: true });
  const pdfPath = path.join(PDF_CACHE_DIR, storedName + '.pdf');
  // Serve cached PDF if it is newer than the source
  try {
    if (fs.existsSync(pdfPath) && fs.statSync(pdfPath).mtimeMs >= fs.statSync(src).mtimeMs) return pdfPath;
  } catch {}
  const tmpHtml = path.join(PDF_CACHE_DIR, storedName + '.html');
  try {
    // PPTX/PPT: python-pptx → content HTML (soffice hangs here, so we render a content view,
    // not a pixel-perfect one — enough to review ordering/figures/narrative before approving).
    if (ext === '.pptx' || ext === '.ppt') {
      execFileSync('/usr/bin/python3', [PPTX2HTML, src, tmpHtml], { timeout: 90000, stdio: 'ignore' });
      if (!(fs.existsSync(tmpHtml) && fs.statSync(tmpHtml).size > 0)) throw new Error('empty pptx html');
    } else {
      // Primary: mammoth (embeds images). Fallback: textutil (text only) for .doc or if mammoth fails.
      try {
        execFileSync('/usr/bin/python3', [DOCX2HTML, src, tmpHtml], { timeout: 60000, stdio: 'ignore' });
        if (!(fs.existsSync(tmpHtml) && fs.statSync(tmpHtml).size > 0)) throw new Error('empty html');
      } catch (mErr) {
        execFileSync('textutil', ['-convert', 'html', '-output', tmpHtml, src], { timeout: 30000, stdio: 'ignore' });
      }
    }
    execFileSync(CHROME_BIN, ['--headless=new', '--disable-gpu', '--no-sandbox',
      '--no-pdf-header-footer', `--print-to-pdf=${pdfPath}`, 'file://' + tmpHtml],
      { timeout: 60000, stdio: 'ignore' });
    try { fs.unlinkSync(tmpHtml); } catch {}
    if (fs.existsSync(pdfPath) && fs.statSync(pdfPath).size > 0) return pdfPath;
  } catch (e) {
    try { fs.unlinkSync(tmpHtml); } catch {}
    console.log('pdf rendition failed for', storedName, e.message);
  }
  return null;
}

// Build an RFC 6266 / 5987-safe Content-Disposition value. A raw non-ASCII byte (e.g. an em-dash
// "—" in a document's filename) in an HTTP header throws ERR_INVALID_CHAR, and — uncaught in a
// request handler — crashes the ENTIRE server process (root cause of the /viewpdf crash-loop that
// looked like a restart storm). ASCII-only `filename="..."` fallback + UTF-8 `filename*` for the
// real name.
function safeContentDisposition(name, disposition) {
  const raw = String(name == null ? 'file' : name);
  const ascii = raw.replace(/[^\x20-\x7e]/g, '_').replace(/["\\]/g, '');
  return `${disposition || 'inline'}; filename="${ascii}"; filename*=UTF-8''${encodeURIComponent(raw)}`;
}

// Simple multipart parser for file uploads
function parseMultipart(req) {
  return new Promise((resolve, reject) => {
    const contentType = req.headers['content-type'] || '';
    const boundaryMatch = contentType.match(/boundary=(?:"([^"]+)"|([^\s;]+))/);
    if (!boundaryMatch) return reject(new Error('No boundary in content-type'));
    const boundary = boundaryMatch[1] || boundaryMatch[2];

    const chunks = [];
    let totalSize = 0;
    req.on('data', chunk => {
      totalSize += chunk.length;
      if (totalSize > MAX_UPLOAD_SIZE) {
        req.destroy();
        return reject(new Error(`File too large (max ${MAX_UPLOAD_SIZE / 1024 / 1024} MB)`));
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      const buf = Buffer.concat(chunks);
      const parts = {};
      const boundaryBuf = Buffer.from('--' + boundary);

      // Split by boundary
      let start = 0;
      const positions = [];
      while (true) {
        const idx = buf.indexOf(boundaryBuf, start);
        if (idx === -1) break;
        positions.push(idx);
        start = idx + boundaryBuf.length;
      }

      for (let i = 0; i < positions.length - 1; i++) {
        const partStart = positions[i] + boundaryBuf.length + 2; // skip boundary + \r\n
        const partEnd = positions[i + 1] - 2; // skip \r\n before next boundary
        if (partStart >= partEnd) continue;
        const partBuf = buf.slice(partStart, partEnd);

        // Split headers from body at \r\n\r\n
        const headerEnd = partBuf.indexOf('\r\n\r\n');
        if (headerEnd === -1) continue;
        const headerStr = partBuf.slice(0, headerEnd).toString();
        const body = partBuf.slice(headerEnd + 4);

        const nameMatch = headerStr.match(/name="([^"]+)"/);
        const filenameMatch = headerStr.match(/filename="([^"]+)"/);
        if (!nameMatch) continue;

        if (filenameMatch) {
          parts[nameMatch[1]] = { filename: filenameMatch[1], data: body, headers: headerStr };
        } else {
          parts[nameMatch[1]] = body.toString();
        }
      }
      resolve(parts);
    });
    req.on('error', reject);
  });
}

// Supabase config
const SUPABASE_URL = 'https://pcrgpuoljylqcumijvnw.supabase.co';
const SUPABASE_KEY = 'sb_publishable_qBnodkDgym8-xuHPy3_qcg_0h98BYWp';

// Teamwork config (moved server-side from teamwork.html)
const TEAMWORK_TOKEN = 'twp_qI3nZlYw4JHzCa87ef63uoP88LRC';
const TEAMWORK_BASE = 'https://exosaerospace.teamwork.com';
const TEAMWORK_PROJECTS = [1107372, 902146, 503346, 1106202, 930633, 993036];

function teamworkFetch(urlPath) {
  return new Promise((resolve, reject) => {
    const url = new URL(TEAMWORK_BASE + urlPath);
    const options = {
      hostname: url.hostname,
      path: url.pathname + url.search,
      method: 'GET',
      headers: {
        'Authorization': 'Basic ' + Buffer.from(TEAMWORK_TOKEN + ':x').toString('base64'),
      }
    };
    const req = https.request(options, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch { resolve(data); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

function teamworkDateToISO(d) {
  if (!d) return null;
  // Teamwork dates: YYYYMMDD
  return d.substring(0, 4) + '-' + d.substring(4, 6) + '-' + d.substring(6, 8);
}

function teamworkPriorityToNum(p) {
  if (p === 'high') return 90;
  if (p === 'medium') return 50;
  if (p === 'low') return 20;
  return 50;
}

function teamworkStateMap(status) {
  if (!status) return 'To Do';
  if (status === 'completed') return 'Done';
  if (status === 'reopened') return 'In Progress';
  return 'To Do';
}

// ── Short-TTL in-memory read cache for Supabase GETs ─────────────────────────
// Disk-IO remediation (2026-09-09): the Supabase project was draining its Disk IO
// Budget because every open dashboard tab (many auto-refresh on 15–60s timers) and
// every polling page hit Supabase disk with an UNCACHED read. This collapses all
// near-simultaneous list reads into ONE Supabase read per query per TTL window, no
// matter how many tabs/pollers are open — the dominant IO driver.
//   • Only multi-row list GETs are cached. Point lookups (id=eq.) and single-row
//     (limit=1) reads — i.e. read-before-write paths — are NEVER cached, so writes
//     stay correct.
//   • Any write (POST/PATCH/DELETE) through this server flushes the whole cache.
//   • Fully reversible: set MC_SB_CACHE_TTL_MS=0 to disable, or delete this block.
const SB_CACHE_TTL_MS = parseInt(process.env.MC_SB_CACHE_TTL_MS || '15000', 10);
const _sbCache = new Map(); // key -> { exp, payload }
function _sbCacheable(pathAndQuery) {
  return SB_CACHE_TTL_MS > 0
    && !/id=eq\./.test(pathAndQuery)
    && !/(^|[?&])limit=1(&|$)/.test(pathAndQuery);
}

function supabaseRequest(method, pathAndQuery, body) {
  const isGet = method === 'GET';
  const cacheKey = isGet ? ('GET ' + pathAndQuery) : null;
  if (isGet && _sbCacheable(pathAndQuery)) {
    const hit = _sbCache.get(cacheKey);
    if (hit && hit.exp > Date.now()) return Promise.resolve(structuredClone(hit.payload));
    if (hit) _sbCache.delete(cacheKey);
  }
  return new Promise((resolve, reject) => {
    const url = new URL(SUPABASE_URL + '/rest/v1/' + pathAndQuery);
    const options = {
      hostname: url.hostname,
      path: url.pathname + url.search,
      method,
      headers: {
        'apikey': SUPABASE_KEY,
        'Authorization': 'Bearer ' + SUPABASE_KEY,
        'Content-Type': 'application/json',
        'Prefer': method === 'POST' ? 'return=representation' : method === 'PATCH' ? 'return=representation' : '',
      }
    };
    const req = https.request(options, res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        let payload;
        try { payload = { status: res.statusCode, data: data ? JSON.parse(data) : null }; }
        catch { payload = { status: res.statusCode, data }; }
        if (isGet) {
          if (_sbCacheable(pathAndQuery) && payload.status >= 200 && payload.status < 300) {
            if (_sbCache.size > 300) _sbCache.clear(); // bound memory
            _sbCache.set(cacheKey, { exp: Date.now() + SB_CACHE_TTL_MS, payload: structuredClone(payload) });
          }
        } else {
          _sbCache.clear(); // any write invalidates cached reads
        }
        resolve(payload);
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
}

// GET that pages past PostgREST's hard 1000-row response cap. Pass a query WITHOUT limit/offset;
// returns { status, data: [...all rows] }. Use for any list that can exceed 1000 rows.
async function supabaseGetAll(pathAndQuery) {
  const sep = pathAndQuery.includes('?') ? '&' : '?';
  let all = [], offset = 0, status = 200;
  for (let page = 0; page < 100; page++) {
    const r = await supabaseRequest('GET', `${pathAndQuery}${sep}limit=1000&offset=${offset}`);
    status = r.status;
    const chunk = Array.isArray(r.data) ? r.data : [];
    all = all.concat(chunk);
    if (chunk.length < 1000) break;
    offset += 1000;
  }
  return { status, data: all };
}

// Map Supabase row → frontend format
function toFrontend(row) {
  return {
    id: row.crm_id || row.id,
    _uuid: row.id,
    company: row.organization || '',
    contact: row.name || '',
    title: row.title || '',
    category: row.type || '',
    tier: row.tier || '',
    stage: row.stage || '',
    email: row.email || '',
    phone: row.phone || '',
    linkedin: row.linkedin || '',
    owner: row.owner || '',
    status: row.status || 'Active',
    priority_score: row.priority_score || 0,
    cadence: row.cadence || null,
    next_action: row.next_action || '',
    notes: row.notes || '',
    source: row.source || '',
    tags: row.tags || [],
    fit_thesis: (row.tags || []).join(' / '),
    warm_intro: '',
    offer: '',
    last_touch: row.last_contacted ? row.last_contacted.slice(0, 10) : '',
    next_touch: row.next_followup ? row.next_followup.slice(0, 10) : '',
    created_at: row.created_at,
    updated_at: row.updated_at,
  };
}

// Region classification for the Non-CONUS (international) CRM segment. Computed at serve-time so it
// survives CRM regeneration. A contact is Non-CONUS if explicitly tagged 'non-conus'/'international'
// (tag one to force-include an international company), else by email ccTLD / country keyword / phone
// country code. Used to scope users (e.g. Toshi -> Non-CONUS) and to power the CRM region filter.
const NONCONUS_CCTLD = new Set(['jp','au','uk','gb','ca','de','fr','it','es','nl','se','no','fi','dk','ch','at','be','ie','in','sg','kr','cn','hk','tw','nz','br','mx','ae','il','za','pl','cz','pt','gr','lu','eu']);
const NONCONUS_KW = /japan|tokyo|hokkaido|hospo|space cotan|kumazawa|australia|eucla|space angel|torino|italia|\bitaly\b|euronext dublin|\bdublin\b|\bireland\b|united kingdom|\buk\b|\blondon\b|\bcanada\b|\bgermany\b|munich|\bfrance\b|cailabs|\bparis\b|\bindia\b|singapore|\bkorea\b|seoul|kolon|taiwan|new zealand|netherlands|switzerland|\bisrael\b|\buae\b|dubai|\bbrazil\b|\bmexico\b|\bspain\b|\bsweden\b|\bnorway\b/i;
function crmRegion(r) {
  const tags = (r.tags || []).map(t => String(t).toLowerCase().trim());
  if (tags.some(t => t === 'non-conus' || t === 'international' || t === 'intl')) return 'Non-CONUS';
  if (tags.some(t => t === 'conus' || t === 'domestic')) return 'CONUS';
  const email = String(r.email || '').toLowerCase();
  const m = email.match(/@[\w.-]+\.([a-z]{2})$/);
  if (m && NONCONUS_CCTLD.has(m[1])) return 'Non-CONUS';
  const blob = [r.company, r.contact, r.notes, r.title, r.category].join(' ').toLowerCase();
  if (NONCONUS_KW.test(blob)) return 'Non-CONUS';
  const pd = String(r.phone || '').replace(/[^\d+]/g, '');
  if (pd.startsWith('+') && !pd.startsWith('+1') && pd.length >= 8) return 'Non-CONUS';
  if (pd.startsWith('+1')) return 'CONUS';
  if (email.endsWith('.gov') || email.endsWith('.mil')) return 'CONUS';
  return 'Unknown';
}

// Map frontend fields → Supabase columns
function toSupabase(fields) {
  const map = {};
  if ('company' in fields) map.organization = fields.company;
  if ('contact' in fields) map.name = fields.contact;
  if ('title' in fields) map.title = fields.title;
  if ('category' in fields) map.type = fields.category;
  if ('tier' in fields) map.tier = fields.tier;
  if ('stage' in fields) map.stage = fields.stage;
  if ('email' in fields) map.email = fields.email;
  if ('phone' in fields) map.phone = fields.phone;
  if ('linkedin' in fields) map.linkedin = fields.linkedin;
  if ('owner' in fields) map.owner = fields.owner;
  if ('status' in fields) map.status = fields.status;
  if ('priority_score' in fields) map.priority_score = fields.priority_score ? Number(fields.priority_score) : null;
  if ('next_action' in fields) map.next_action = fields.next_action;
  if ('notes' in fields) map.notes = fields.notes;
  if ('source' in fields) map.source = fields.source;
  if ('fit_thesis' in fields) map.tags = fields.fit_thesis ? fields.fit_thesis.split('/').map(s => s.trim()).filter(Boolean) : [];
  if ('last_touch' in fields && fields.last_touch) map.last_contacted = fields.last_touch + 'T00:00:00Z';
  if ('next_touch' in fields && fields.next_touch) map.next_followup = fields.next_touch + 'T00:00:00Z';
  return map;
}

// ── TASK ASSIGNMENT EMAIL ──────────────────────────────────────────────
// Maps an owner string (name / first name / email) to a login account in
// users.json, then emails that person the full task details on assignment.
function escTaskHtml(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

function findOwnerUser(owner) {
  if (!owner) return null;
  let users = [];
  try { users = loadUsers(); } catch { return null; }
  const o = String(owner).trim().toLowerCase();
  if (!o || o === 'exo' || o === 'exomac' || o === 'both' || o === 'system') return null;
  // exact email or exact full name
  let u = users.find(x => (x.email && x.email.toLowerCase() === o) ||
                          (x.name && x.name.toLowerCase() === o));
  if (u) return u;
  // alias: "jon" → John Quinn
  if (o === 'jon') u = users.find(x => x.email && x.email.toLowerCase() === 'jquinn@exosaero.com');
  if (u) return u;
  // first-name / prefix match (e.g. "Lizi" → "Lizi Quinn")
  u = users.find(x => {
    if (!x.name) return false;
    const n = x.name.toLowerCase();
    return n === o || n.split(/\s+/)[0] === o || n.startsWith(o + ' ');
  });
  return u || null;
}

// Canonical, reachable Mission Control URL for links in outbound email.
// NEVER localhost — recipients open mail on their own machines. Source of truth:
// MC_PUBLIC_URL env → .public-url file → the WARP-reachable default.
function mcBaseUrl() {
  let u = process.env.MC_PUBLIC_URL;
  if (!u) { try { u = fs.readFileSync(path.join(__dirname, '.public-url'), 'utf-8').trim(); } catch {} }
  return (u || 'http://192.168.143.216:8080').replace(/\/+$/, '');
}

async function sendTaskAssignmentEmail(task, assignedBy) {
  try {
    const user = findOwnerUser(task && task.owner);
    if (!user || !user.email || user.active === false) return { skipped: 'no-matching-user' };

    const bridgeCert = fs.existsSync('/Users/exomac/.protonmail-bridge.crt')
      ? fs.readFileSync('/Users/exomac/.protonmail-bridge.crt') : undefined;
    const transporter = nodemailer.createTransport({
      host: '127.0.0.1', port: 1025, secure: false, requireTLS: true,
      tls: { ca: bridgeCert, rejectUnauthorized: false },
      auth: { user: 'jquinnexo@pm.me', pass: 'SPqYBivj98-jyF3RujLKxA' }
    });

    const due = task.due_date ? String(task.due_date).slice(0, 10) : 'None';
    const prio = (task.priority !== undefined && task.priority !== null) ? task.priority : '—';
    const title = task.title || 'Untitled task';
    const desc = task.description || '(no description provided)';
    const cat = task.category || '—';
    const state = task.state || 'To Do';
    const by = assignedBy || 'Mission Control';

    const text =
`You have been assigned a task in Exos Mission Control.

Task:        ${title}
Owner:       ${user.name} <${user.email}>
Status:      ${state}
Priority:    ${prio}
Category:    ${cat}
Due:         ${due}
Assigned by: ${by}

Details:
${desc}

Open Mission Control: ${mcBaseUrl()}/`;

    const html = `
      <div style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;">
        <div style="background:#0a1628;padding:18px 24px;border-radius:8px 8px 0 0;">
          <h2 style="color:#0080ff;margin:0;font-size:18px;">Exos Mission Control — New Task Assigned</h2>
        </div>
        <div style="background:#ffffff;padding:24px;border:1px solid #ddd;color:#222;">
          <p style="margin:0 0 16px;">Hi ${escTaskHtml(user.name.split(/\s+/)[0])}, you have been assigned the following task:</p>
          <table style="border-collapse:collapse;font-size:14px;width:100%;">
            <tr><td style="padding:5px 14px 5px 0;color:#666;white-space:nowrap;">Task</td><td style="padding:5px 0;"><strong>${escTaskHtml(title)}</strong></td></tr>
            <tr><td style="padding:5px 14px 5px 0;color:#666;">Status</td><td style="padding:5px 0;">${escTaskHtml(state)}</td></tr>
            <tr><td style="padding:5px 14px 5px 0;color:#666;">Priority</td><td style="padding:5px 0;">${escTaskHtml(String(prio))}</td></tr>
            <tr><td style="padding:5px 14px 5px 0;color:#666;">Category</td><td style="padding:5px 0;">${escTaskHtml(cat)}</td></tr>
            <tr><td style="padding:5px 14px 5px 0;color:#666;">Due</td><td style="padding:5px 0;">${escTaskHtml(due)}</td></tr>
            <tr><td style="padding:5px 14px 5px 0;color:#666;">Assigned by</td><td style="padding:5px 0;">${escTaskHtml(by)}</td></tr>
          </table>
          <h3 style="color:#0a1628;margin:18px 0 6px;font-size:15px;">Details</h3>
          <p style="white-space:pre-wrap;margin:0 0 20px;line-height:1.5;">${escTaskHtml(desc)}</p>
          <a href="${mcBaseUrl()}/" style="display:inline-block;padding:10px 18px;background:#0080ff;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;">Open Mission Control</a>
        </div>
        <div style="background:#f5f5f5;padding:12px 24px;border-radius:0 0 8px 8px;border:1px solid #ddd;border-top:none;">
          <p style="font-size:11px;color:#999;margin:0;">Exos Aerospace Systems &amp; Technologies, Inc. — Mission Control task notification.</p>
        </div>
      </div>`;

    const info = await transporter.sendMail({
      from: '"Exos Mission Control" <jquinnexo@pm.me>',
      replyTo: 'jquinn@exosaero.com',
      to: user.email,
      subject: `[Mission Control] Task assigned: ${title}`,
      text,
      html,
    });
    console.log(`[TaskAssign] Email sent to ${user.email} for "${title}" — messageId: ${info.messageId}`);
    return { sent: true, to: user.email, messageId: info.messageId };
  } catch (err) {
    console.error('[TaskAssign] Email send error:', err.message);
    return { error: err.message };
  }
}

function parseTasksFromMD() {
  if (!fs.existsSync(MD_FILE)) return [];
  const content = fs.readFileSync(MD_FILE, 'utf-8');
  const lines = content.split('\n');
  const tasks = [];
  
  let currentTask = null;
  let currentState = 'Blocked';

  for (const line of lines) {
    if (line.includes('🔴 BLOCKED')) currentState = 'Blocked';
    else if (line.includes('🟡 READY')) currentState = 'Blocked'; 
    else if (line.includes('🔵 IN PROGRESS')) currentState = 'In Progress';
    else if (line.includes('✅ COMPLETED')) currentState = 'Done';
    
    const taskMatch = line.match(/^###\s+([A-Z0-9-]+)\s+\|\s+(.+)/);
    if (taskMatch) {
      if (currentTask) tasks.push(currentTask);
      currentTask = {
        id: taskMatch[1],
        title: taskMatch[2].trim(),
        state: currentState,
        owner: 'Jon',
        description: ''
      };
      continue;
    }

    if (currentTask) {
      if (line.startsWith('**Owner:**')) {
        const ownerMatch = line.match(/\*\*Owner:\*\*\s+\[(.*?)\]/);
        if (ownerMatch) currentTask.owner = ownerMatch[1];
      } else if (line.trim() !== '' && !line.startsWith('---')) {
        currentTask.description += line.trim() + ' ';
      }
    }
  }
  if (currentTask) tasks.push(currentTask);
  return tasks;
}

// ── ROLE-BASED AUTH ──
const crypto = require('crypto');
const USERS_FILE = path.join(__dirname, 'users.json');

function loadUsers() {
  try { return JSON.parse(fs.readFileSync(USERS_FILE, 'utf-8')); }
  catch { return []; }
}
function saveUsers(users) {
  fs.writeFileSync(USERS_FILE, JSON.stringify(users, null, 2));
}
function hashPassword(pw, salt) {
  return crypto.pbkdf2Sync(pw, salt, 100000, 64, 'sha256').toString('hex');
}
function verifyPassword(pw, hash, salt) {
  return hashPassword(pw, salt) === hash;
}

// sessions maps token → { userId, email, name, role }
// Sessions are persisted to disk so a server restart does not silently log
// everyone out (browsers keep the crm_session cookie for 24h; an in-memory-only
// Map would reject every authenticated action after a restart, e.g. change-password).
const SESSIONS_FILE = path.join(__dirname, 'sessions.json');
const SESSION_MAX_AGE_MS = 86400 * 1000; // must match the cookie Max-Age (24h)
let sessions = new Map();
try {
  const raw = JSON.parse(fs.readFileSync(SESSIONS_FILE, 'utf8'));
  const now = Date.now();
  sessions = new Map(raw.filter(([, s]) => s && s.createdAt && (now - s.createdAt) < SESSION_MAX_AGE_MS));
} catch (e) { /* no prior sessions file */ }
function saveSessions() {
  try { fs.writeFileSync(SESSIONS_FILE, JSON.stringify([...sessions.entries()]), { mode: 0o600 }); } catch (e) {}
}

function parseCookies(req) {
  return (req.headers.cookie || '').split(';').reduce((acc, c) => {
    const [k, v] = c.trim().split('=');
    if (k && v) acc[k] = v;
    return acc;
  }, {});
}

function getSession(req) {
  const cookies = parseCookies(req);
  if (cookies.crm_session && sessions.has(cookies.crm_session)) {
    return sessions.get(cookies.crm_session);
  }
  return null;
}

// ── SEGREGATED DOCUSIGN ENTRY ──────────────────────────────────────────────
// A public link (/docusign) gated by its OWN passcode, granting access ONLY to
// the document send/assign actions — fully isolated from CRM, admin, tasks,
// deals, financials, uploads. A ds_session can never reach anything else.
const dsSessions = new Map();        // token -> { kind, createdAt, ip }
const dsLoginThrottle = new Map();   // ip -> { fails, until }
// Passcode source (no weak default): env var, else a local .ds-passcode file, else a random
// per-boot value that no one knows (effectively locks /docusign until the file is set).
const DS_PASSCODE = process.env.MC_DOCUSIGN_PASSCODE
  || (() => { try { return fs.readFileSync(path.join(__dirname, '.ds-passcode'), 'utf-8').trim(); } catch { return ''; } })()
  || crypto.randomBytes(24).toString('hex');
// Exact paths a DocuSign-only session is permitted to touch. Nothing else.
const DS_ALLOWED = new Set([
  '/docusign', '/docusign.html',
  '/api/docusign/login', '/api/docusign/logout',
  '/api/docusign/send', '/api/esign/create',
]);
function getDsSession(req) {
  const c = parseCookies(req);
  if (c.ds_session && dsSessions.has(c.ds_session)) return dsSessions.get(c.ds_session);
  return null;
}
function isDsAllowed(url) {
  return DS_ALLOWED.has((url || '').split('?')[0]);
}
function docusignGatePage() {
  return `<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Exos Aerospace — DocuSign</title>
  <style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,system-ui,sans-serif;background:#0a1628;color:#e8edf2;display:flex;align-items:center;justify-content:center;min-height:100vh}
  .box{background:#0f1e38;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:40px;width:90%;max-width:380px;text-align:center}
  h1{font-size:20px;margin-bottom:4px}h1 span{color:#f5a623}.sub{color:#a0aec0;font-size:13px;margin-bottom:24px;line-height:1.4}
  input{width:100%;padding:12px;background:#162a4a;border:1px solid rgba(255,255,255,0.08);border-radius:6px;color:#e8edf2;font-size:15px;outline:none;margin-bottom:16px;text-align:center;letter-spacing:2px}input:focus{border-color:#f5a623}
  button{width:100%;padding:12px;background:#f5a623;border:none;border-radius:6px;color:#0a1628;font-size:15px;font-weight:700;cursor:pointer}
  .err{color:#ff4444;font-size:13px;margin-top:10px;display:none}</style></head>
  <body><div class="box"><h1>Exos Aerospace <span>DocuSign</span></h1><p class="sub">Enter the access passcode to send documents for signature.</p>
  <input type="password" id="pc" placeholder="Passcode" autofocus autocomplete="off">
  <button onclick="go()">Unlock</button><div class="err" id="err">Invalid passcode</div></div>
  <script>
  document.getElementById('pc').addEventListener('keydown',e=>{if(e.key==='Enter')go()});
  async function go(){const pc=document.getElementById('pc').value;
    const r=await fetch('/api/docusign/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({passcode:pc})});
    if(r.ok){location.replace('/docusign');}else{const e=document.getElementById('err');e.style.display='block';e.textContent=r.status===429?'Too many attempts — wait a few minutes.':'Invalid passcode';}
  }</script></body></html>`;
}

function checkAuth(req, res) {
  if (req.method === 'OPTIONS') return true;
  return !!getSession(req);
}

function requireRole(req, res, ...roles) {
  const session = getSession(req);
  if (!session) {
    res.writeHead(401, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Unauthorized' }));
    return null;
  }
  if (roles.length > 0 && !roles.includes(session.role)) {
    res.writeHead(403, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Forbidden — insufficient permissions' }));
    return null;
  }
  return session;
}

// ── WELCOME PAGE GENERATOR (early adopter onboarding) ──
function generateWelcomePage(sess) {
  const userName = sess ? sess.name : 'Guest';
  const users = loadUsers();
  const user = sess ? users.find(u => u.id === sess.userId) : null;
  const projectName = user && user.project ? user.project : 'your assigned project';
  return `<!DOCTYPE html><html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Welcome - Exos Aerospace Mission Control</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a1628;color:#e8edf5;min-height:100vh;display:flex;flex-direction:column;align-items:center}
.hero{text-align:center;padding:60px 24px 40px;max-width:800px}
.logo{width:64px;height:64px;background:linear-gradient(135deg,#0066cc,#ff6b00);border-radius:12px;display:inline-flex;align-items:center;justify-content:center;font-weight:900;font-size:24px;color:#fff;margin-bottom:20px}
h1{font-size:28px;margin-bottom:8px}h1 span{color:#0080ff}
.subtitle{color:#a0aec0;font-size:15px;margin-bottom:40px}
.card{background:#0f1e38;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:32px;max-width:700px;width:90%;margin-bottom:24px;text-align:left}
.card h2{font-size:18px;margin-bottom:16px;color:#0080ff}
.card ul{list-style:none;padding:0}.card li{padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:14px;line-height:1.6;color:#c8d6e5}
.card li:last-child{border-bottom:none}.card li strong{color:#e8edf5}
.badge{display:inline-block;padding:3px 10px;border-radius:6px;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.5px}
.badge-ea{background:rgba(255,107,0,0.2);color:#fb923c;border:1px solid rgba(255,107,0,0.4)}
.badge-project{background:rgba(168,85,247,0.15);color:#a855f7;border:1px solid rgba(168,85,247,0.3)}
.rules{background:#162a4a;border:1px solid rgba(255,255,255,0.06);border-radius:8px;padding:20px;margin-top:16px}
.rules h3{font-size:14px;color:#ff6b00;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.5px}
.rules li{font-size:13px;color:#a0aec0;padding:4px 0}
.cta{display:inline-block;margin-top:32px;padding:14px 32px;background:#0080ff;color:#fff;border-radius:8px;font-size:16px;font-weight:600;text-decoration:none;transition:background 0.2s}
.cta:hover{background:#0066cc}
.footer{color:#4a5568;font-size:12px;padding:40px 24px;text-align:center}
</style></head><body>
<div class="hero"><div class="logo">EX</div>
<h1>Welcome to <span>Mission Control</span></h1>
<p class="subtitle">Exos Aerospace Early Adopter Program</p></div>
<div class="card"><h2>Your Account</h2><ul>
<li><strong>Name:</strong> ${userName}</li>
<li><strong>Role:</strong> <span class="badge badge-ea">Early Adopter</span></li>
<li><strong>Project:</strong> <span class="badge badge-project">${projectName}</span></li>
</ul></div>
<div class="card"><h2>What You Can Do</h2><ul>
<li><strong>View Tasks</strong> - See all tasks assigned to your project on the Kanban board</li>
<li><strong>Create Tasks</strong> - Add new tasks to track work items and action items</li>
<li><strong>Update Tasks</strong> - Move tasks between Blocked, In Progress, and Done</li>
<li><strong>Post Updates</strong> - Add notes and context to any task in your project</li>
<li><strong>Filter and Search</strong> - Use the toolbar to filter by owner, status, or keyword</li>
</ul>
<div class="rules"><h3>Usage Guidelines</h3><ul>
<li>You can view and manage tasks within <strong>${projectName}</strong> only</li>
<li>Task deletion is reserved for Exos administrators</li>
<li>CRM, DocuSign, Opportunities, and admin panels are not included in the early adopter preview</li>
<li>All activity is logged and visible to the project team</li>
<li>Do not share your login credentials with anyone outside your organization</li>
<li>This is a confidential preview - do not distribute screenshots or data externally</li>
<li>For support or access changes, contact <strong>jquinn@exosaero.com</strong></li>
</ul></div></div>
<div class="card"><h2>Getting Started</h2><ul>
<li><strong>Step 1:</strong> Click "Go to Mission Control" below to open the task board</li>
<li><strong>Step 2:</strong> Review existing tasks in your project</li>
<li><strong>Step 3:</strong> Click any task to open its detail panel with description, timeline, and notes</li>
<li><strong>Step 4:</strong> Use the "+ Add" bar at the top to create new tasks</li>
<li><strong>Step 5:</strong> Drag and drop tasks between columns, or use quick-move buttons</li>
</ul></div>
<div class="card"><h2>Commanding Exo with @exo</h2>
<p style="color:#c8d6e5;font-size:14px;line-height:1.6;margin-bottom:14px">You can tell Exo what to do right from a task. In the <strong>"Add an update or note…"</strong> box at the bottom of a task, type <strong>@exo</strong> followed by a command. Exo acts on that task within about two minutes and posts a ✅ confirmation note back. Click the small <strong>?</strong> in the top-right of that box to see the list any time. (<strong>@Exobot</strong> still works too.)</p>
<ul>
<li><strong>@exo done</strong> - mark the task Done (also close / complete / paid)</li>
<li><strong>@exo reopen</strong> - move it back to To Do</li>
<li><strong>@exo block</strong> / <strong>unblock</strong> - set or clear Blocked</li>
<li><strong>@exo reassign to Neil</strong> - hand it to someone (or "have Lizi take it", "give to Kyle")</li>
<li><strong>@exo urgent</strong> - raise the task's priority</li>
<li><strong>@exo order a new release servo</strong> - any plain-English request is routed to the right owner automatically; you don't need to know who handles it</li>
</ul>
<div class="rules"><h3>Good to know</h3><ul>
<li>A note <strong>without</strong> @exo (or @Exobot) just logs to the task - it will not trigger any action, so you can comment freely.</li>
<li>@exo also works in a <strong>Decision</strong> note, and by email to <strong>exosmc@proton.me</strong> with "@exo" and a request. <strong>@Exobot</strong> remains valid everywhere @exo is.</li>
<li>Anything external or sensitive is drafted and held for approval, never sent automatically.</li>
</ul></div></div>
<a href="/" class="cta">Go to Mission Control</a>
<div class="footer">Exos Aerospace Systems, Inc. - 299 FM 1903, Greenville, TX 75401<br>Early Adopter Preview - Confidential</div>
</body></html>`;
}

const server = http.createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, PATCH, DELETE, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(204);
    res.end();
    return;
  }

  // Login endpoint
  if (req.url === '/api/login' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const { email, password } = JSON.parse(body);
        const users = loadUsers();
        const user = users.find(u => u.email.toLowerCase() === (email || '').toLowerCase() && u.active);
        if (user && verifyPassword(password, user.password_hash, user.password_salt)) {
          const token = crypto.randomBytes(32).toString('hex');
          sessions.set(token, { userId: user.id, email: user.email, name: user.name, role: user.role, createdAt: Date.now() });
          saveSessions();
          // Stamp last login so onboarding/rollout success is verifiable (who's actually in).
          try { user.last_login = new Date().toISOString(); saveUsers(users); } catch (e) {}
          res.setHeader('Set-Cookie', `crm_session=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=86400`);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: true, user: { name: user.name, email: user.email, role: user.role } }));
        } else {
          res.writeHead(401, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'Invalid email or password' }));
        }
      } catch(e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Bad request' }));
      }
    }); return;
  }

  // Self-service password: a logged-in user sets their OWN password. No admin involved.
  if (req.url === '/api/change-password' && req.method === 'POST') {
    const session = getSession(req);
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const { newPassword } = JSON.parse(body || '{}');
        if (!newPassword || String(newPassword).length < 8) {
          res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Password must be at least 8 characters.' })); return;
        }
        const users = loadUsers();
        const user = users.find(u => u.id === session.userId);
        if (!user) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'User not found' })); return; }
        const salt = crypto.randomBytes(32).toString('hex');
        user.password_salt = salt;
        user.password_hash = hashPassword(newPassword, salt);
        user.password_set_at = new Date().toISOString();
        saveUsers(users);
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true }));
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Bad request' })); }
    }); return;
  }

  // Get current user info
  if (req.url === '/api/me' && req.method === 'GET') {
    const session = getSession(req);
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(session));
    return;
  }

  // ── CUSTOM DASHBOARD LAYOUTS ──────────────────────────────────────────────
  // Per-user dashboard arrangement, keyed by the logged-in identity (MC session, which
  // rides on top of Cloudflare Access). GET returns the user's layout, or the company
  // default when they have none. POST saves the user's layout; POST ?default=1 (admin only)
  // also promotes it to the company default. GET ?default=1 forces the company default
  // (the "reset to company default" button). Stored as data/layouts/<email>.json + _default.json.
  if (req.url.split('?')[0] === '/api/layout') {
    const sess = getSession(req);
    if (!sess) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    const LAYOUT_DIR = path.join(__dirname, 'data', 'layouts');
    try { fs.mkdirSync(LAYOUT_DIR, { recursive: true }); } catch (e) {}
    const DEFAULT_FILE = path.join(LAYOUT_DIR, '_default.json');
    const safe = (sess.email || 'anon').toLowerCase().replace(/[^a-z0-9._-]/g, '_');
    const userFile = path.join(LAYOUT_DIR, safe + '.json');
    const readJson = (f) => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch (e) { return null; } };
    const q = new URL(req.url, 'http://localhost').searchParams;

    if (req.method === 'GET') {
      let layout, isDefault = false;
      if (q.get('default') === '1') { layout = readJson(DEFAULT_FILE); isDefault = true; }
      else { layout = readJson(userFile); if (!layout) { layout = readJson(DEFAULT_FILE); isDefault = true; } }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ layout: layout || null, isDefault, email: sess.email, name: sess.name, role: sess.role }));
      return;
    }
    if (req.method === 'POST') {
      let body = ''; req.on('data', c => body += c); req.on('end', () => {
        try {
          const p = JSON.parse(body || '{}');
          const asDefault = q.get('default') === '1';
          if (asDefault && sess.role !== 'admin') {
            res.writeHead(403, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Only an admin can set the company default layout' })); return;
          }
          if (!p.layout || !Array.isArray(p.layout.widgets)) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'layout.widgets[] required' })); return;
          }
          fs.writeFileSync(userFile, JSON.stringify(p.layout, null, 2));
          if (asDefault) fs.writeFileSync(DEFAULT_FILE, JSON.stringify(p.layout, null, 2));
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: true, savedDefault: asDefault }));
        } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
      });
      return;
    }
    res.writeHead(405, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Method not allowed' })); return;
  }

  // Logout
  if (req.url === '/api/logout' && req.method === 'POST') {
    const cookies = parseCookies(req);
    if (cookies.crm_session) { sessions.delete(cookies.crm_session); saveSessions(); }
    res.setHeader('Set-Cookie', 'crm_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true }));
    return;
  }

  // ── ADMIN: User Management (admin only) ──
  if (req.url === '/api/admin/users' && req.method === 'GET') {
    const session = requireRole(req, res, 'admin');
    if (!session) return;
    const users = loadUsers().map(u => ({ id: u.id, email: u.email, name: u.name, role: u.role, active: u.active, created_at: u.created_at, project: u.project || null }));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(users));
    return;
  }

  if (req.url === '/api/admin/users' && req.method === 'POST') {
    const session = requireRole(req, res, 'admin');
    if (!session) return;
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const { email, name, password, role, project } = JSON.parse(body);
        if (!email || !name || !password) { res.writeHead(400); res.end(JSON.stringify({ error: 'email, name, password required' })); return; }
        if (!['admin', 'manager', 'member', 'early_adopter'].includes(role)) { res.writeHead(400); res.end(JSON.stringify({ error: 'role must be admin, manager, member, or early_adopter' })); return; }
        const users = loadUsers();
        if (users.find(u => u.email.toLowerCase() === email.toLowerCase())) { res.writeHead(409); res.end(JSON.stringify({ error: 'Email already exists' })); return; }
        const salt = crypto.randomBytes(32).toString('hex');
        const newUser = {
          id: users.length > 0 ? Math.max(...users.map(u => u.id)) + 1 : 1,
          email, name, role,
          password_hash: hashPassword(password, salt),
          password_salt: salt,
          created_at: new Date().toISOString(),
          active: true
        };
        if (role === 'early_adopter' && project) newUser.project = project;
        users.push(newUser);
        saveUsers(users);
        res.writeHead(201, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ id: newUser.id, email: newUser.email, name: newUser.name, role: newUser.role }));
      } catch(e) { res.writeHead(400); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  if (req.url === '/api/admin/users' && req.method === 'PATCH') {
    const session = requireRole(req, res, 'admin');
    if (!session) return;
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const { id, name, email, role, active, password, project } = JSON.parse(body);
        const users = loadUsers();
        const idx = users.findIndex(u => u.id === id);
        if (idx === -1) { res.writeHead(404); res.end(JSON.stringify({ error: 'User not found' })); return; }
        if (name) users[idx].name = name;
        if (email) users[idx].email = email;
        if (role && ['admin', 'manager', 'member', 'early_adopter'].includes(role)) users[idx].role = role;
        if (project !== undefined) users[idx].project = project;
        if (active !== undefined) users[idx].active = active;
        if (password) {
          const salt = crypto.randomBytes(32).toString('hex');
          users[idx].password_hash = hashPassword(password, salt);
          users[idx].password_salt = salt;
        }
        saveUsers(users);
        // Invalidate this user's sessions if deactivated
        if (active === false) {
          for (const [token, sess] of sessions.entries()) {
            if (sess.userId === id) sessions.delete(token);
          }
          saveSessions();
        }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ id: users[idx].id, email: users[idx].email, name: users[idx].name, role: users[idx].role, active: users[idx].active }));
      } catch(e) { res.writeHead(400); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  if (req.url.startsWith('/api/admin/users/delete') && req.method === 'POST') {
    const session = requireRole(req, res, 'admin');
    if (!session) return;
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      if (id === session.userId) { res.writeHead(400); res.end(JSON.stringify({ error: 'Cannot delete your own account' })); return; }
      const users = loadUsers().filter(u => u.id !== id);
      saveUsers(users);
      // Kill their sessions
      for (const [token, sess] of sessions.entries()) {
        if (sess.userId === id) sessions.delete(token);
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true }));
    }); return;
  }

  // Login page
  if (req.url === '/login' || req.url === '/login.html' || req.url.startsWith('/login?')) {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(`<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EXOS Mission Control — Login</title>
    <style>*{box-sizing:border-box;margin:0;padding:0}body{font-family:-apple-system,system-ui,sans-serif;background:#0a1628;color:#e8edf2;display:flex;align-items:center;justify-content:center;min-height:100vh}
    .login{background:#0f1e38;border:1px solid rgba(255,255,255,0.08);border-radius:12px;padding:40px;width:90%;max-width:400px;text-align:center}
    h1{font-size:24px;margin-bottom:4px}h1 span{color:#0080ff}.sub{color:#a0aec0;font-size:13px;margin-bottom:28px}
    label{display:block;text-align:left;font-size:12px;color:#a0aec0;margin-bottom:4px;text-transform:uppercase;letter-spacing:0.5px}
    input{width:100%;padding:12px;background:#162a4a;border:1px solid rgba(255,255,255,0.08);border-radius:6px;color:#e8edf2;font-size:15px;outline:none;margin-bottom:16px}input:focus{border-color:#0080ff}
    button{width:100%;padding:12px;background:#0080ff;border:none;border-radius:6px;color:#fff;font-size:15px;font-weight:600;cursor:pointer}button:hover{background:#0066cc}
    .err{color:#ff4444;font-size:13px;margin-top:8px;display:none}</style></head>
    <body><div class="login"><h1><span>EXOS</span> Mission Control</h1><p class="sub">Sign in with your account</p>
    <label>Email</label><input type="email" id="em" placeholder="you@exosaerospace.com" autofocus>
    <label>Password</label><input type="password" id="pw" placeholder="Password">
    <button onclick="login()">Sign In</button><div class="err" id="err">Invalid email or password</div></div>
    <script>
    document.getElementById('pw').addEventListener('keydown',e=>{if(e.key==='Enter')login()});
    document.getElementById('em').addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('pw').focus()});
    async function login(){
      const em=document.getElementById('em').value, pw=document.getElementById('pw').value;
      const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:em,password:pw})});
      if(r.ok){const d=await r.json();sessionStorage.setItem('mc_user',JSON.stringify(d.user));const dest=new URLSearchParams(location.search).get('next')||'/';window.location=dest;}
      else{document.getElementById('err').style.display='block'}
    }</script></body></html>`);
    return;
  }

  // ── DOCUSIGN PASSCODE: login / logout / gated page (segregated entry) ──
  if (req.url === '/api/docusign/login' && req.method === 'POST') {
    const ip = (req.headers['x-forwarded-for'] || '').split(',')[0].trim() || req.socket.remoteAddress || '';
    const now = Date.now();
    const th = dsLoginThrottle.get(ip);
    if (th && th.until > now) {
      res.writeHead(429, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Too many attempts. Try again shortly.' }));
      return;
    }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      let passcode = ''; try { passcode = (JSON.parse(body || '{}').passcode) || ''; } catch {}
      // constant-time-ish compare
      const ok = passcode.length === DS_PASSCODE.length &&
        crypto.timingSafeEqual(Buffer.from(passcode), Buffer.from(DS_PASSCODE));
      if (ok) {
        dsLoginThrottle.delete(ip);
        const token = crypto.randomBytes(24).toString('hex');
        dsSessions.set(token, { kind: 'docusign', createdAt: now, ip });
        res.setHeader('Set-Cookie', `ds_session=${token}; Path=/; HttpOnly; SameSite=Strict; Max-Age=43200`);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
      } else {
        const fails = ((th && th.fails) || 0) + 1;
        dsLoginThrottle.set(ip, { fails, until: fails >= 5 ? now + 5 * 60 * 1000 : 0 });
        res.writeHead(401, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid passcode' }));
      }
    });
    return;
  }
  if (req.url === '/api/docusign/logout' && req.method === 'POST') {
    const c = parseCookies(req);
    if (c.ds_session) dsSessions.delete(c.ds_session);
    res.setHeader('Set-Cookie', 'ds_session=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ ok: true }));
    return;
  }
  // DocuSign panel page: full MC session OR ds passcode unlocks it; else passcode prompt.
  if (req.method === 'GET' && (req.url === '/docusign' || req.url.split('?')[0] === '/docusign.html')) {
    const full = getSession(req);
    if (full && full.role === 'early_adopter') { res.writeHead(302, { 'Location': '/' }); res.end(); return; }
    if (full || getDsSession(req)) {
      try { res.writeHead(200, { 'Content-Type': 'text/html' }); res.end(fs.readFileSync(path.join(__dirname, 'docusign.html'))); }
      catch (e) { res.writeHead(404); res.end('DocuSign panel not found'); }
    } else {
      res.writeHead(200, { 'Content-Type': 'text/html' });
      res.end(docusignGatePage());
    }
    return;
  }

  // ── Streaming backup download (token-gated; STREAMS, never readFileSync) ──
  // Serves the latest asset-backup archive from BACKUP_DL_DIR for off-machine copy to
  // SharePoint over Cloudflare One. GET /backup/<file>?token=<t>. Uses createReadStream so a
  // multi-hundred-MB download never blocks the event loop (unlike /uploads). Token-gated on
  // top of the Cloudflare One org gate. Supports HTTP Range so downloads can resume.
  if (req.url.startsWith('/backup/') && req.method === 'GET') {
    const u = new URL(req.url, 'http://localhost');
    if ((u.searchParams.get('token') || '') !== backupToken()) { res.writeHead(403); res.end('Forbidden'); return; }
    const name = decodeURIComponent(u.pathname.replace('/backup/', ''));
    const file = path.join(BACKUP_DL_DIR, name);
    if (!file.startsWith(BACKUP_DL_DIR) || name.includes('..') || !fs.existsSync(file) || !fs.statSync(file).isFile()) {
      res.writeHead(404); res.end('Not found'); return;
    }
    const size = fs.statSync(file).size;
    const range = req.headers.range;
    const headers = { 'Content-Type': 'application/gzip', 'Accept-Ranges': 'bytes',
      'Content-Disposition': safeContentDisposition(path.basename(file), 'attachment') };
    let stream;
    if (range) {
      const m = /bytes=(\d+)-(\d*)/.exec(range) || [];
      const start = parseInt(m[1], 10) || 0;
      const end = m[2] ? parseInt(m[2], 10) : size - 1;
      res.writeHead(206, { ...headers, 'Content-Range': `bytes ${start}-${end}/${size}`, 'Content-Length': end - start + 1 });
      stream = fs.createReadStream(file, { start, end });
    } else {
      res.writeHead(200, { ...headers, 'Content-Length': size });
      stream = fs.createReadStream(file);
    }
    stream.on('error', () => { try { res.destroy(); } catch {} });
    req.on('close', () => { try { stream.destroy(); } catch {} });
    stream.pipe(res);
    return;
  }

  // ── AUTH GATE: protect all pages and APIs except login ──
  const publicPaths = ['/api/login', '/login', '/login.html', '/api/inbound-email', '/brand-assets/', '/sign', '/sign.html', '/api/esign/get', '/api/esign/sign', '/api/decisions/ingest', '/api/research/ingest'];
  const isPublic = publicPaths.some(p => req.url.startsWith(p));
  const decisionsCronPath = req.url.split('?')[0];
  const isDecisionsCronRequest = (decisionsCronPath === '/api/decisions' || decisionsCronPath === '/api/decisions/answer') && isDecisionsCronToken(req);
  const fullSession = getSession(req);
  const dsSession = getDsSession(req);
  if (!fullSession) {
    if (isDecisionsCronRequest) {
      // Token-authenticated cron request on an allowed decisions path — fall through to the handler.
    } else if (dsSession) {
      // DocuSign-only session: confined strictly to DocuSign actions (+ already-public assets).
      if (!isDsAllowed(req.url) && !isPublic) {
        if (req.url.startsWith('/api/')) {
          res.writeHead(403, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'This DocuSign link only permits sending documents for signature.' }));
        } else {
          res.writeHead(302, { 'Location': '/docusign' });
          res.end();
        }
        return;
      }
      // allowed → fall through to the handler
    } else if (!isPublic) {
      // No session at all: API calls get 401, pages redirect to login
      if (req.url.startsWith('/api/')) {
        res.writeHead(401, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Unauthorized' }));
      } else {
        const next = encodeURIComponent(req.url);
        res.writeHead(302, { 'Location': `/login?next=${next}` });
        res.end();
      }
      return;
    }
  }

  // ── ROLE RESTRICTIONS ──
  // member role: block deals, templates, admin, dashboard endpoints
  const session = getSession(req);
  if (session && session.role === 'member') {
    const fp = req.url.split('?')[0];
    // API + data endpoints members may not read. Includes the sensitive pages' data sources so
    // the block is real access control, not just a hidden nav button: HR directory, CTD DD (M&A
    // due-diligence), and Gov/DIB Readiness.
    const blockedForMember = ['/api/deals', '/api/templates', '/api/admin', '/api/dashboard',
      '/api/exosops', '/api/hr', '/data/ctd-dd.json', '/data/gov-readiness.json'];
    if (blockedForMember.some(p => fp.startsWith(p))) {
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Forbidden — you do not have access to this' }));
      return;
    }
    // Sensitive pages members may not open even by direct URL (nav buttons already hidden).
    const blockedPages = ['/ctd-dd', '/ctd-dd.html', '/hr', '/hr.html', '/gov-readiness', '/gov-readiness.html'];
    if (blockedPages.includes(fp)) {
      res.writeHead(302, { 'Location': '/' });
      res.end();
      return;
    }
  }

  // ── OPERATIONAL FINANCE (restricted financial view): explicit email allowlist, NOT role ──
  // Cash / burn / runway from QuickBooks (Operational-Finance-exo3). Sensitive → DEFAULT DENY.
  // Only emails in data/finance-access.json may load /finance.html or hit the API; every other
  // user is blocked regardless of admin/manager role (mirrors the /api/commissions allowlist).
  {
    const fp = req.url.split('?')[0];
    if (fp === '/finance' || fp === '/finance.html' || fp === '/api/operational-finance' || fp === '/api/capital-bridge') {
      let allow = [];
      try { allow = (JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'finance-access.json'))).allow || []); } catch (e) {}
      const allowSet = new Set(allow.map(x => String(x).toLowerCase()));
      const femail = (session && session.email || '').toLowerCase();
      if (!femail || !allowSet.has(femail)) {
        if (fp.startsWith('/api/')) { res.writeHead(403, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Forbidden — restricted financial view' })); }
        else { res.writeHead(302, { 'Location': '/' }); res.end(); }
        return;
      }
      if (fp === '/api/operational-finance') {
        try { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(fs.readFileSync(path.join(__dirname, 'data', 'operational-finance.json'))); }
        catch (e) { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{}'); }
        return;
      }
      if (fp === '/api/capital-bridge') {
        // 504 Reg D / PO10 raise status + "days since last commitment" (David's outreach trigger).
        try {
          const led = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'capital_bridge_ledger.json')));
          const target = led.target || 0, base = led.baseline_amount || 0;
          const entries = (led.entries || []).filter(e => e && typeof e === 'object');
          let logged = 0; entries.forEach(e => { if (typeof e.amount === 'number') logged += e.amount; });
          const received = base + logged;
          const parse = s => { const d = Date.parse(s); return isNaN(d) ? null : d; };
          const pend = (led.pending_packets || []).filter(p => p && typeof p === 'object');
          const commit = [];
          entries.forEach(e => ['date', 'signed_date'].forEach(k => { const d = parse(e[k]); if (d) commit.push({ t: d, who: e.investor || '?' }); }));
          pend.forEach(p => ['signed_date', 'date'].forEach(k => { const d = parse(p[k]); if (d) commit.push({ t: d, who: p.investor || '?' }); }));
          commit.sort((a, b) => a.t - b.t);
          const recvDates = entries.map(e => parse(e.date)).filter(Boolean);
          const now = Date.now(), DAY = 86400000;
          const lastRecv = recvDates.length ? Math.max(...recvDates) : null;
          const lastCommit = commit.length ? commit[commit.length - 1] : null;
          const dSinceCommit = lastCommit ? Math.floor((now - lastCommit.t) / DAY) : null;
          const dSinceRecv = lastRecv ? Math.floor((now - lastRecv) / DAY) : null;
          let THRESH = 7; try { THRESH = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'finance-access.json'))).commitment_trigger_days || 7; } catch (e) {}
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            program: led.program, target, received, pct: target ? Math.round(received / target * 100) : 0,
            pending_count: pend.length,
            last_received: lastRecv ? new Date(lastRecv).toISOString().slice(0, 10) : null, days_since_received: dSinceRecv,
            last_commitment: lastCommit ? new Date(lastCommit.t).toISOString().slice(0, 10) : null,
            last_commitment_who: lastCommit ? lastCommit.who : null, days_since_commitment: dSinceCommit,
            threshold_days: THRESH, trigger: (dSinceCommit != null && dSinceCommit >= THRESH),
            recent: entries.slice(-6).reverse().map(e => ({ date: e.date, investor: e.investor, amount: e.amount }))
          }));
        } catch (e) { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{}'); }
        return;
      }
      // /finance.html → authorized; fall through to the static file server
    }
  }

  // early_adopter role: strict sandbox — tasks board only, no CRM/deals/admin/docusign.
  // Task DATA is further scoped to the user's `project` (category) below. Uploads/viewpdf are
  // BLOCKED for this role: uploads are NOT project-scoped, so allowing them would leak every
  // doc (investor decks, 409A, financial model, ITAR-adjacent) to an external sandbox user
  // (e.g. the UTD capstone students, who are scoped to "Payload Sales" only).
  if (session && session.role === 'early_adopter') {
    // NOTE: /api/task-desc is allowed here but is PROJECT-SCOPED inside its own handler
    // (an early_adopter only gets the description of a task in their assigned project).
    // Without it the board detail panel lazy-load (index.html) 403s on every card open —
    // students can't read their own scoped tasks and each click is mislogged as
    // out-of-scope "probing". uploads stays OFF the list (docs aren't project-scoped).
    const allowedAPIs = ['/api/tasks', '/api/task-desc', '/api/me', '/api/logout', '/api/layout', '/api/capstone-program'];
    const isAllowedAPI = allowedAPIs.some(p => req.url.startsWith(p));
    if (req.url.startsWith('/api/') && !isAllowedAPI) {
      auditDeny(session, req, 'out-of-scope-api');
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'This feature is not available in the early adopter preview.' }));
      return;
    }
    // Block task deletion and task capture for early adopters
    if (req.url.startsWith('/api/tasks/delete') || req.url.startsWith('/api/tasks/capture')) {
      auditDeny(session, req, 'blocked-task-op');
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Not available in the early adopter preview.' }));
      return;
    }
    // Block doc download routes outright for this sandbox (not project-scoped).
    if (req.url.startsWith('/uploads/') || req.url.startsWith('/viewpdf/') || req.url.startsWith('/backup/')) {
      auditDeny(session, req, 'blocked-doc-route');
      res.writeHead(403); res.end('Forbidden'); return;
    }
    // Block internal pages — only allow tasks board and welcome
    const allowedPages = ['/', '/index.html', '/welcome', '/welcome.html', '/login', '/login.html', '/dashboard', '/dashboard.html', '/capstone-tracker', '/capstone-tracker.html', '/set-password', '/set-password.html'];
    const isAllowedPage = allowedPages.some(p => req.url === p || req.url.startsWith(p + '?'));
    if (req.method === 'GET' && !req.url.startsWith('/api/') && !isAllowedPage && !req.url.startsWith('/brand-assets')) {
      res.writeHead(302, { 'Location': '/' });
      res.end();
      return;
    }
  }

  // ── Capstone program feed (read-only; students + Edwin see the timeline gates + scorecard) ──
  if (req.url.split('?')[0] === '/api/capstone-program' && req.method === 'GET') {
    try {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(fs.readFileSync(path.join(__dirname, 'data', 'capstone-program.json')));
    } catch (e) { res.writeHead(404); res.end(JSON.stringify({ error: 'not found' })); }
    return;
  }

  // ── DD registry (read-only; CRM UI reads this for the DD field + red-glow failed companies) ──
  if (req.url.split('?')[0] === '/api/dd' && req.method === 'GET') {
    try {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(fs.readFileSync(path.join(__dirname, 'data', 'dd-registry.json')));
    } catch (e) { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{}'); }
    return;
  }

  // ── SALES COMMISSIONS (restricted): Jon + CTO see all; a sales agent sees ONLY their own ──
  // Data lives in the audited ERP db (erp-foundation/mc.db), not the CRM. Access is enforced here
  // by an explicit allowlist, NOT by MC role (Lizi is an admin AND an agent → must see only hers).
  if (req.url.split('?')[0] === '/api/commissions' && req.method === 'GET') {
    const s = getSession(req);
    const email = (s && s.email || '').toLowerCase();
    let cfg = { full_view: ['jquinn@exosaero.com'], cto_email: '' };
    try { cfg = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'commission-access.json'))); } catch (e) {}
    const fullView = new Set([...(cfg.full_view || []), cfg.cto_email].filter(Boolean).map(x => x.toLowerCase()));
    let erp;
    try {
      const { openErp } = require('../erp-foundation/dal');
      erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: email || 'mc-server', agent: 'mc-commissions-view' });
      let scope, rows;
      if (fullView.has(email)) {
        scope = 'full';
        rows = erp.listCommissions({ limit: 500 });
      } else {
        const agent = erp.getAgentByEmail(email);   // registered sales agent → sees ONLY their own
        if (agent) { scope = 'self'; rows = erp.listCommissions({ agent_id: agent.id, limit: 500 }); }
        else { scope = 'none'; rows = []; }
      }
      const totals = rows.reduce((a, r) => {
        if (r.status === 'paid') a.paid += r.commission_amount || 0; else a.due += r.commission_amount || 0;
        return a;
      }, { due: 0, paid: 0 });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ scope, viewer: email, rows, totals }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'commissions unavailable', detail: String(e).slice(0, 200) }));
    } finally { try { erp && erp.close(); } catch (e) {} }
    return;
  }

  // ── HR DIRECTORY (read-only) — read-through mirror of BambooHR; directory-level only, no PII ──
  // Bamboo remains the system of record; this serves name/title/department/manager/work-email
  // for the MC directory + org-chart views. Requires a logged-in session.
  if (req.url.split('?')[0] === '/api/hr/directory' && req.method === 'GET') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let erp;
    try {
      const { openErp } = require('../erp-foundation/dal');
      erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: (session && session.email) || 'mc-server', agent: 'mc-hr-directory' });
      const employees = erp.getEmployees();
      const org_units = erp.getOrgUnits();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ source: 'BambooHR (read-through mirror; Bamboo authoritative)', count: employees.length, employees, org_units }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'hr directory unavailable', detail: String(e).slice(0, 200) }));
    } finally { try { erp && erp.close(); } catch (e) {} }
    return;
  }

  // ── ASSET REGISTER (read-only) — serialized flight-hardware register + events (audited ERP db) ──
  if (req.url.split('?')[0] === '/api/assets' && req.method === 'GET') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let erp;
    try {
      const { openErp } = require('../erp-foundation/dal');
      erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: (session && session.email) || 'mc-server', agent: 'mc-asset-register' });
      const assets = erp.listAssets().map(a => ({ ...a, event_list: erp.listAssetEvents(a.id) }));
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ count: assets.length, assets }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'asset register unavailable', detail: String(e).slice(0, 200) }));
    } finally { try { erp && erp.close(); } catch (e) {} }
    return;
  }

  // ── PRODUCTION CONTROL (read-only) — work orders + routing/WIP + quality (MQ-1) ──
  if (req.url.split('?')[0] === '/api/production' && req.method === 'GET') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let erp;
    try {
      const { openErp } = require('../erp-foundation/dal');
      erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: (session && session.email) || 'mc-server', agent: 'mc-production' });
      const work_orders = erp.listWorkOrders().map(w => ({ ...w, ops_list: erp.listWorkOrderOps(w.id) }));
      const ncrs = erp.listNCRs();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ work_orders, ncrs }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'production unavailable', detail: String(e).slice(0, 200) }));
    } finally { try { erp && erp.close(); } catch (e) {} }
    return;
  }

  // ── SCHEDULE (read-only) — Teamwork -> ERP replicated project schedule ──
  // Critical Path Method over the schedule's finish-to-start dependencies. Mutates tasks in place,
  // adding predecessors[] (parsed), critical(bool), slack(days); returns {projectDays, criticalCount}.
  function scheduleCPM(tasks) {
    const byId = {};
    tasks.forEach(t => {
      let pre = []; try { pre = JSON.parse(t.predecessors_json || '[]') || []; } catch (e) {}
      t.predecessors = Array.isArray(pre) ? pre : [];
      delete t.predecessors_json;
      t._succ = []; byId[t.id] = t;
    });
    const dur = t => { if (t.start_date && t.due_date) { const d = (new Date(t.due_date) - new Date(t.start_date)) / 86400000; return Math.max(1, Math.round(d)); } return 1; };
    tasks.forEach(t => t.predecessors.forEach(p => { if (byId[p]) byId[p]._succ.push(t.id); }));
    // topological order (cycle-safe)
    const order = [], seen = {}, temp = {};
    const visit = t => { if (!t || seen[t.id] || temp[t.id]) return; temp[t.id] = 1; t.predecessors.forEach(p => visit(byId[p])); temp[t.id] = 0; seen[t.id] = 1; order.push(t); };
    tasks.forEach(t => visit(t));
    order.forEach(t => { let es = 0; t.predecessors.forEach(p => { if (byId[p]) es = Math.max(es, byId[p]._ef); }); t._es = es; t._ef = es + dur(t); });
    const end = tasks.reduce((m, t) => Math.max(m, t._ef || 0), 0);
    [...order].reverse().forEach(t => { let lf = end; if (t._succ.length) lf = Math.min(...t._succ.map(s => byId[s]._ls)); t._lf = lf; t._ls = lf - dur(t); });
    let crit = 0;
    tasks.forEach(t => { t.slack = Math.max(0, Math.round(t._ls - t._es)); t.critical = t.slack <= 0; if (t.critical) crit++; delete t._succ; delete t._es; delete t._ef; delete t._ls; delete t._lf; });
    return { projectDays: end, criticalCount: crit };
  }
  if (req.url.split('?')[0] === '/api/schedule' && req.method === 'GET') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let erp;
    try {
      const { openErp } = require('../erp-foundation/dal');
      erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: (session && session.email) || 'mc-server', agent: 'mc-schedule' });
      const projId = (new URLSearchParams(req.url.split('?')[1] || '')).get('project') || 'tw-902146';
      const sched = erp.getProjectSchedule(projId);
      const cpm = scheduleCPM(sched.tasks || []);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ source: 'Mission Control + ERP (system of record; Teamwork retired)', ...sched, cpm, projects: erp.listProjects() }));
    } catch (e) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'schedule unavailable', detail: String(e).slice(0, 200) }));
    } finally { try { erp && erp.close(); } catch (e) {} }
    return;
  }

  // ── SCHEDULE: edit a task's start/due/owner/status (audited ERP; MC is system of record) ──
  if (req.url.split('?')[0] === '/api/schedule/task' && req.method === 'PATCH') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let body = ''; req.on('data', c => { body += c; if (body.length > 1e5) req.destroy(); });
    req.on('end', () => {
      let erp;
      try {
        const { id, start_date, due_date, owner, state, predecessors } = JSON.parse(body);
        if (!id) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'id required' })); return; }
        const patch = {};
        if (start_date !== undefined) patch.start_date = start_date || null;
        if (due_date !== undefined) patch.due_date = due_date || null;
        if (owner !== undefined) patch.owner = owner || null;
        if (state !== undefined) patch.state = state || null;
        if (predecessors !== undefined) patch.predecessors = Array.isArray(predecessors) ? predecessors.filter(p => p && p !== id) : [];
        const { openErp } = require('../erp-foundation/dal');
        erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: (session && session.email) || 'mc-server', agent: 'mc-schedule-edit' });
        const row = erp.updateScheduleTask(id, patch);
        if (!row) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'task not found' })); return; }
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true }));
      } catch (e) { res.writeHead(500, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: String(e).slice(0, 200) })); }
      finally { try { erp && erp.close(); } catch (e) {} }
    });
    return;
  }

  // ── EXPENSE REPORTS: submit (employee) → auto-create manager approval task ──
  if (req.url.split('?')[0] === '/api/expense/submit' && req.method === 'POST') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let body = ''; req.on('data', c => { body += c; if (body.length > MAX_UPLOAD_SIZE) req.destroy(); });
    req.on('end', async () => {
      try {
        const { filename, dataBase64, amount, purpose, period } = JSON.parse(body);
        const email = (session.email || '').toLowerCase(), name = session.name || email;
        const EXP_DIR = path.join(UPLOADS_DIR, 'expenses'); fs.mkdirSync(EXP_DIR, { recursive: true });
        const id = 'EXP-' + Date.now().toString(36).toUpperCase();
        const safe = (filename || 'expense.xlsx').replace(/[^\w.\-]/g, '_');
        const stored = id + '_' + safe;
        if (dataBase64) fs.writeFileSync(path.join(EXP_DIR, stored), Buffer.from(String(dataBase64).split(',').pop(), 'base64'));
        // Extract amount / period / purpose from the uploaded sheet (no manual entry required).
        let exAmount = amount || null, exPurpose = purpose || null, exPeriod = period || null;
        try {
          const { execFileSync } = require('child_process');
          const outp = execFileSync('/usr/bin/python3',
            [path.join(__dirname, '..', 'scripts', 'parse_expense_report.py'), path.join(EXP_DIR, stored)],
            { env: { ...process.env, PYTHONPATH: '/Users/Shared/exos-archive/pylibs' }, timeout: 15000 }).toString();
          const pd = JSON.parse(outp);
          if (pd.amount != null) exAmount = pd.amount;
          if (pd.period) exPeriod = pd.period;
          if (pd.purpose) exPurpose = pd.purpose;
        } catch (e) { /* leave blank if unparseable; manager reads the attachment */ }
        let mgrEmail = null, mgrName = null;
        try { const { openErp } = require('../erp-foundation/dal'); const erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: email, agent: 'expense-submit' }); const me = erp.getEmployeeByEmail(email); mgrEmail = me && me.manager_email; mgrName = me && me.manager_name; erp.close(); } catch (e) {}
        const fileUrl = '/uploads/expenses/' + encodeURIComponent(stored);
        const amtStr = exAmount != null ? Number(exAmount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '?';
        const task = {
          title: `Approve expense report — ${name} ($${amtStr})`,
          owner: mgrName || 'John Quinn', assigned_email: mgrEmail || 'jquinn@exosaero.com', assigned_to: mgrName || null,
          state: 'To Do', priority: 75, category: 'Expense', source: 'expense-workflow', tags: ['expense-approval'],
          description: `Expense report from ${name} (${email}).\nAmount: $${amtStr} · Purpose: ${exPurpose || '—'} · Period: ${exPeriod || '—'}\n(auto-read from the uploaded report)\nReport file: ${fileUrl}\nAPPROVE by marking this task Done — payment then auto-routes to Finance (CFO + AP). Ref ${id}.`
        };
        const created = await supabaseRequest('POST', 'tasks', task).then(r => Array.isArray(r.data) ? r.data[0] : r.data).catch(() => null);
        // Attach the uploaded report to the task's Documents tab (uploads registry).
        if (created && created.id && dataBase64) {
          try {
            const um = loadUploadsMeta();
            um.push({
              id: crypto.randomBytes(8).toString('hex'),
              filename: filename || stored, stored_name: 'expenses/' + stored,
              size: fs.statSync(path.join(EXP_DIR, stored)).size,
              extension: (safe.split('.').pop() || '').toLowerCase(),
              task_id: created.id, project_id: null, decision_id: null,
              uploaded_by: name, uploaded_at: new Date().toISOString(),
            });
            saveUploadsMeta(um);
          } catch (e) { /* non-fatal: file still linked in the description */ }
        }
        const LEDGER = path.join(__dirname, 'data', 'expense-reports.json');
        let led = []; try { led = JSON.parse(fs.readFileSync(LEDGER, 'utf8')); } catch (e) {}
        led.unshift({ id, submitter_email: email, submitter_name: name, manager_email: mgrEmail, manager_name: mgrName, amount: exAmount != null ? exAmount : null, purpose: exPurpose || null, period: exPeriod || null, file: fileUrl, submitted_at: new Date().toISOString(), state: 'submitted', approval_task_id: created && created.id || null, payment_task_id: null });
        fs.writeFileSync(LEDGER, JSON.stringify(led, null, 2));
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, id, manager: mgrName, approval_task_id: created && created.id }));
      } catch (e) { res.writeHead(500, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: String(e).slice(0, 200) })); }
    });
    return;
  }
  // ── EXPENSE REPORTS: create from the web form (structured line items, no spreadsheet) ──
  // Runs the Exobot pre-screen (area-normal cost check + mileage math) and surfaces any flags
  // to the reviewer on the approval task BEFORE they approve.
  if (req.url.split('?')[0] === '/api/expense/create' && req.method === 'POST') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let body = ''; req.on('data', c => { body += c; if (body.length > MAX_UPLOAD_SIZE) req.destroy(); });
    req.on('end', async () => {
      try {
        const { purpose, period, line_items, receiptFilename, receiptBase64 } = JSON.parse(body);
        const email = (session.email || '').toLowerCase(), name = session.name || email;
        const items = Array.isArray(line_items) ? line_items : [];
        if (!items.length) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Add at least one expense line.' })); return; }
        const id = 'EXP-' + Date.now().toString(36).toUpperCase();
        // Exobot pre-screen: area-normal cost check + mileage computed at the IRS rate.
        let screen = { total: 0, flags: [], summary: '', mileage_total_miles: 0, mileage_total_usd: 0, mileage_rate: 0.70, flag_count: 0 };
        try {
          const { execFileSync } = require('child_process');
          const out = execFileSync('/usr/bin/python3',
            [path.join(__dirname, '..', 'scripts', 'expense_screen.py')],
            { input: JSON.stringify({ line_items: items }), env: { ...process.env }, timeout: 15000 }).toString();
          screen = JSON.parse(out);
        } catch (e) { /* screen best-effort; fall back to summed amounts below */ }
        // Normalize computed amounts back onto the lines (mileage → miles×rate).
        const rate = screen.mileage_rate || 0.70;
        const lines = items.map(it => {
          const cat = (it.category || 'Other');
          const amt = (String(cat).toLowerCase() === 'mileage')
            ? Math.round((Number(it.miles) || 0) * rate * 100) / 100
            : Math.round((Number(it.amount) || 0) * 100) / 100;
          return { ...it, category: cat, amount: amt };
        });
        const total = screen.total != null ? screen.total : lines.reduce((a, l) => a + l.amount, 0);
        // Optional receipt attachment (not required).
        let fileUrl = null, stored = null;
        if (receiptBase64) {
          const EXP_DIR = path.join(UPLOADS_DIR, 'expenses'); fs.mkdirSync(EXP_DIR, { recursive: true });
          const safe = (receiptFilename || 'receipt.pdf').replace(/[^\w.\-]/g, '_');
          stored = id + '_' + safe;
          fs.writeFileSync(path.join(EXP_DIR, stored), Buffer.from(String(receiptBase64).split(',').pop(), 'base64'));
          fileUrl = '/uploads/expenses/' + encodeURIComponent(stored);
        }
        let mgrEmail = null, mgrName = null;
        try { const { openErp } = require('../erp-foundation/dal'); const erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: email, agent: 'expense-create' }); const me = erp.getEmployeeByEmail(email); mgrEmail = me && me.manager_email; mgrName = me && me.manager_name; erp.close(); } catch (e) {}
        const amtStr = Number(total).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const flagged = (screen.flag_count || 0) > 0;
        const lineTxt = lines.map(l => {
          const extra = String(l.category).toLowerCase() === 'mileage' ? ` [${Number(l.miles) || 0} mi × $${rate.toFixed(2)}]` : '';
          return `  • ${l.date || '—'} · ${l.category} · $${Number(l.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${extra}${l.location ? ' · ' + l.location : ''}${l.description ? ' — ' + l.description : ''}`;
        }).join('\n');
        const screenTxt = flagged
          ? `\n\n⚠️ EXOBOT PRE-SCREEN — ${screen.flag_count} item(s) to review before approving:\n` + screen.flags.filter(f => f.severity === 'review').map(f => '  ⚠️ ' + f.message).join('\n')
          : `\n\n✅ EXOBOT PRE-SCREEN: all lines within area-normal cost ranges.`;
        const task = {
          title: `Approve expense report — ${name} ($${amtStr})${flagged ? ' ⚠️' : ''}`,
          owner: mgrName || 'John Quinn', assigned_email: mgrEmail || 'jquinn@exosaero.com', assigned_to: mgrName || null,
          state: 'To Do', priority: flagged ? 82 : 75, category: 'Expense', source: 'expense-workflow',
          tags: flagged ? ['expense-approval', 'expense-flagged'] : ['expense-approval'],
          description: `Expense report from ${name} (${email}).\nAmount: $${amtStr} · Purpose: ${purpose || '—'} · Period: ${period || '—'}\nMileage: ${screen.mileage_total_miles || 0} mi = $${Number(screen.mileage_total_usd || 0).toFixed(2)} @ $${rate.toFixed(2)}/mi\n\nLine items:\n${lineTxt}${screenTxt}\n\nAPPROVE by marking this task Done — payment then auto-routes to Finance. Ref ${id}.`
        };
        const created = await supabaseRequest('POST', 'tasks', task).then(r => Array.isArray(r.data) ? r.data[0] : r.data).catch(() => null);
        if (created && created.id && fileUrl) {
          try {
            const um = loadUploadsMeta();
            um.push({ id: crypto.randomBytes(8).toString('hex'), filename: receiptFilename || stored, stored_name: 'expenses/' + stored,
              size: fs.statSync(path.join(UPLOADS_DIR, 'expenses', stored)).size, extension: (stored.split('.').pop() || '').toLowerCase(),
              task_id: created.id, project_id: null, decision_id: null, uploaded_by: name, uploaded_at: new Date().toISOString() });
            saveUploadsMeta(um);
          } catch (e) {}
        }
        const LEDGER = path.join(__dirname, 'data', 'expense-reports.json');
        let led = []; try { led = JSON.parse(fs.readFileSync(LEDGER, 'utf8')); } catch (e) {}
        led.unshift({ id, submitter_email: email, submitter_name: name, manager_email: mgrEmail, manager_name: mgrName,
          amount: total, purpose: purpose || null, period: period || null, line_items: lines, file: fileUrl,
          screen: { flags: screen.flags || [], flag_count: screen.flag_count || 0, mileage_total_miles: screen.mileage_total_miles || 0, mileage_total_usd: screen.mileage_total_usd || 0, mileage_rate: rate },
          submitted_at: new Date().toISOString(), state: 'submitted', approval_task_id: created && created.id || null, payment_task_id: null });
        fs.writeFileSync(LEDGER, JSON.stringify(led, null, 2));
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, id, total, manager: mgrName, approval_task_id: created && created.id, flags: screen.flags || [], flag_count: screen.flag_count || 0, summary: screen.summary }));
      } catch (e) { res.writeHead(500, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: String(e).slice(0, 200) })); }
    });
    return;
  }
  // ── EXPENSE REPORTS: my submissions (status) ──
  if (req.url.split('?')[0] === '/api/expense/mine' && req.method === 'GET') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let led = []; try { led = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'expense-reports.json'), 'utf8')); } catch (e) {}
    const email = (session.email || '').toLowerCase();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ reports: led.filter(r => (r.submitter_email || '').toLowerCase() === email) }));
    return;
  }
  // ── EXPENSE REPORTS: norms (mileage rate + category list) for the web form ──
  if (req.url.split('?')[0] === '/api/expense/norms' && req.method === 'GET') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let norms = {}; try { norms = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'expense-norms.json'), 'utf8')); } catch (e) {}
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ mileage_rate: norms.mileage_rate || 0.70, categories: Object.keys(norms.categories || {}) }));
    return;
  }
  // ── EXPENSE REPORTS: manager decision (approve -> Finance / deny -> back to employee) ──
  if (req.url.split('?')[0] === '/api/expense/decide' && req.method === 'POST') {
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    let body = ''; req.on('data', c => { body += c; if (body.length > 1e6) req.destroy(); });
    req.on('end', async () => {
      try {
        const { id, decision, comment } = JSON.parse(body);
        const approver = session.name || session.email || 'Manager';
        const LEDGER = path.join(__dirname, 'data', 'expense-reports.json');
        let led = []; try { led = JSON.parse(fs.readFileSync(LEDGER, 'utf8')); } catch (e) {}
        const entry = led.find(r => String(r.approval_task_id) === String(id));
        if (decision === 'denied') {
          if (!comment || !String(comment).trim()) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'A reason is required to deny.' })); return; }
          if (entry) { entry.state = 'denied'; entry.denied_comment = String(comment).trim(); entry.denied_by = approver; entry.denied_at = new Date().toISOString(); fs.writeFileSync(LEDGER, JSON.stringify(led, null, 2)); }
          await supabaseRequest('PATCH', `tasks?id=eq.${id}`, { state: 'Done' }).catch(() => {});
          await supabaseRequest('POST', 'activities', { type: 'task_note', subject: `task:${id}`, body: `Expense DENIED by ${approver}: ${String(comment).trim()}`, owner: approver, status: 'completed' }).catch(() => {});
          if (entry && entry.submitter_email) {
            try {
              const { execFileSync } = require('child_process');
              const amt = entry.amount != null ? ` ($${Number(entry.amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })})` : '';
              const per = entry.period ? `, ${entry.period}` : '';
              const mail = `From: Exos Mission Control <jquinnexo@pm.me>\nTo: ${entry.submitter_email}\nSubject: Expense report returned - please revise and resubmit\n\nHello ${entry.submitter_name || ''},\n\nYour expense report${amt}${per} was reviewed by ${approver} and returned for changes.\n\nReason: ${String(comment).trim()}\n\nPlease correct it and resubmit in Mission Control under the Expenses page (the Submit an Expense Report button). Once resubmitted it routes back for approval.\n\n- Exos Mission Control`;
              execFileSync('/opt/homebrew/bin/msmtp', ['-a', 'protonmail', entry.submitter_email], { input: mail, timeout: 20000 });
            } catch (e) { /* email best-effort */ }
          }
          res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true, decision: 'denied', emailed: !!(entry && entry.submitter_email) }));
          return;
        }
        // approved: move to Done; the expense-workflow cron creates the Finance payment task(s).
        await supabaseRequest('PATCH', `tasks?id=eq.${id}`, { state: 'Done' }).catch(() => {});
        await supabaseRequest('POST', 'activities', { type: 'task_note', subject: `task:${id}`, body: `Expense APPROVED by ${approver} - routing to Finance for payment.`, owner: approver, status: 'completed' }).catch(() => {});
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true, decision: 'approved' }));
      } catch (e) { res.writeHead(500, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: String(e).slice(0, 200) })); }
    });
    return;
  }

  // ── REQUIRED READING: verified-read tracker with server-side anti-gaming ──
  // A ledger of required docs (data/required-reading.json). Reading is *proven* server-side:
  // the client cannot self-certify. We store an open timestamp, clamp active-dwell to real
  // wall-clock elapsed, require scroll-completion + multiple heartbeats, and only then record
  // a valid completion. The enabled button is never sufficient — every ack is re-validated here.
  {
    const RR_FILE = path.join(__dirname, 'data', 'required-reading.json');
    const rrLoad = () => { try { return JSON.parse(fs.readFileSync(RR_FILE, 'utf8')); } catch (e) { return { docs: [], progress: [], completions: [] }; } };
    const rrSave = (o) => fs.writeFileSync(RR_FILE, JSON.stringify(o, null, 2));
    const rrIsAdmin = (s) => s && (s.role === 'admin' || s.role === 'manager');
    // Linked accounts: one person with two logins completes required reading once, and it
    // shows complete under both. John Quinn = jquinn@exosaero.com + megawattcontrols@gmail.com.
    const RR_ALIASES = {
      'jquinn@exosaero.com': ['megawattcontrols@gmail.com'],
      'megawattcontrols@gmail.com': ['jquinn@exosaero.com'],
    };
    // Which required-reading docs apply to a given user (role + departments).
    const RR_DEPT_FOR_AUDIENCE = { '02-ground-operations': 'ops', '06-safety-ehs': 'ops', '04-procurement': 'procurement', '03-payload': 'sales', '08-security-cui': 'it-security', 'cmmc-2.0': 'it-security' };
    const rrRequired = (doc, role, depts) => {
      role = (role || '').toLowerCase();
      // Early adopters (external capstone sandbox): only Mission Control Getting Started (Jon 2026-08-30).
      if (role === 'early_adopter') return doc.id === 'getting-started';
      // Members: Getting Started + the org-wide AI Tool-Use Policy — but NOT the department training set (Jon 2026-08-30).
      if (role === 'member') return doc.id === 'getting-started' || doc.id === 'ai-tool-use-policy';
      if (!doc.audience || doc.audience === 'all') return true;
      if (role === 'admin' || role === 'manager') return true;
      return Array.isArray(depts) && depts.includes(RR_DEPT_FOR_AUDIENCE[doc.audience] || doc.audience);
    };

    // GET /api/required-reading → docs + this user's per-doc status
    if (req.url.split('?')[0] === '/api/required-reading' && req.method === 'GET') {
      if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
      const email = (session.email || '').toLowerCase();
      const rr = rrLoad();
      const meUser = (loadUsers() || []).find(u => (u.email || '').toLowerCase() === email);
      const myDepts = (meUser && Array.isArray(meUser.departments)) ? meUser.departments : [];
      const visibleDocs = rr.docs.filter(d => rrRequired(d, session.role, myDepts));
      const mine = visibleDocs.map(d => {
        const prog = (rr.progress || []).find(p => p.user_email === email && p.doc_id === d.id && p.version === d.version) || null;
        const comp0 = (rr.completions || []).find(c => c.user_email === email && c.doc_id === d.id && c.doc_version === d.version && c.valid) || null;
        // Annual re-certification: a completion older than 365 days is due again.
        const comp = (comp0 && d.recurrence === 'annual' && comp0.acknowledged_at &&
                      (Date.now() - new Date(comp0.acknowledged_at).getTime()) > 365 * 86400000) ? null : comp0;
        return {
          doc_id: d.id, version: d.version,
          completed: !!comp, valid: !!comp,
          active_seconds: comp ? comp.active_seconds : (prog ? (prog.active_seconds || 0) : 0),
          scroll_max_pct: comp ? comp.scroll_max_pct : (prog ? (prog.scroll_max_pct || 0) : 0),
          acknowledged_at: comp ? comp.acknowledged_at : null
        };
      });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ docs: visibleDocs, mine, role: (session.role || 'member'), name: (meUser && meUser.name) || '', is_admin: (session.role === 'admin') }));
      return;
    }

    // POST /api/required-reading/open → start/refresh a progress record for (user,doc,version)
    if (req.url.split('?')[0] === '/api/required-reading/open' && req.method === 'POST') {
      if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
      let body = ''; req.on('data', c => { body += c; if (body.length > 1e5) req.destroy(); });
      req.on('end', () => {
        try {
          const { doc_id } = JSON.parse(body || '{}');
          const email = (session.email || '').toLowerCase();
          const rr = rrLoad();
          const doc = rr.docs.find(d => d.id === doc_id);
          if (!doc) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'unknown doc' })); return; }
          rr.progress = rr.progress || [];
          let prog = rr.progress.find(p => p.user_email === email && p.doc_id === doc.id && p.version === doc.version);
          const now = new Date().toISOString();
          if (!prog) {
            prog = {
              user_email: email, user_name: session.name || email, doc_id: doc.id, version: doc.version,
              server_open_at: now, active_seconds: 0, scroll_max_pct: 0, heartbeats: 0,
              user_agent: req.headers['user-agent'] || '', ip: req.socket.remoteAddress || '', updated_at: now
            };
            rr.progress.push(prog);
          } else if (!prog.server_open_at) {
            prog.server_open_at = now;
            prog.user_agent = req.headers['user-agent'] || prog.user_agent;
            prog.ip = req.socket.remoteAddress || prog.ip;
          }
          rrSave(rr);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true, server_open_at: prog.server_open_at }));
        } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'bad request' })); }
      });
      return;
    }

    // POST /api/required-reading/heartbeat → accumulate dwell/scroll; clamp to wall-clock
    if (req.url.split('?')[0] === '/api/required-reading/heartbeat' && req.method === 'POST') {
      if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
      let body = ''; req.on('data', c => { body += c; if (body.length > 1e5) req.destroy(); });
      req.on('end', () => {
        try {
          const { doc_id, active_seconds, scroll_max_pct, heartbeats } = JSON.parse(body || '{}');
          const email = (session.email || '').toLowerCase();
          const rr = rrLoad();
          const doc = rr.docs.find(d => d.id === doc_id);
          if (!doc) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'unknown doc' })); return; }
          rr.progress = rr.progress || [];
          const prog = rr.progress.find(p => p.user_email === email && p.doc_id === doc.id && p.version === doc.version);
          if (!prog || !prog.server_open_at) { res.writeHead(409, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'not opened' })); return; }
          const elapsed = Math.floor((Date.now() - new Date(prog.server_open_at).getTime()) / 1000);
          const clamped = Math.max(0, Math.min(Number(active_seconds) || 0, elapsed));
          prog.active_seconds = clamped;
          prog.scroll_max_pct = Math.max(0, Math.min(100, Math.round(Number(scroll_max_pct) || 0)));
          prog.heartbeats = Math.max(prog.heartbeats || 0, Number(heartbeats) || 0);
          prog.updated_at = new Date().toISOString();
          rrSave(rr);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true, active_seconds: clamped }));
        } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'bad request' })); }
      });
      return;
    }

    // POST /api/required-reading/ack → SERVER re-validates before recording a valid completion
    if (req.url.split('?')[0] === '/api/required-reading/ack' && req.method === 'POST') {
      if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
      let body = ''; req.on('data', c => { body += c; if (body.length > 1e5) req.destroy(); });
      req.on('end', () => {
        try {
          const { doc_id } = JSON.parse(body || '{}');
          const email = (session.email || '').toLowerCase();
          const rr = rrLoad();
          const doc = rr.docs.find(d => d.id === doc_id);
          if (!doc) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'unknown doc' })); return; }
          rr.progress = rr.progress || []; rr.completions = rr.completions || [];
          // Already recorded for this version → idempotent success, don't nag.
          const existing = rr.completions.find(c => c.user_email === email && c.doc_id === doc.id && c.doc_version === doc.version && c.valid);
          if (existing) { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true, already: true, acknowledged_at: existing.acknowledged_at })); return; }
          const prog = rr.progress.find(p => p.user_email === email && p.doc_id === doc.id && p.version === doc.version);
          if (!prog || !prog.server_open_at) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Reading not started', reason: 'No open record for this document.', need: { min_active_seconds: doc.min_active_seconds, have_active_seconds: 0, scroll_max_pct: 0 } })); return; }
          const now = Date.now();
          const elapsed = Math.floor((now - new Date(prog.server_open_at).getTime()) / 1000);
          const active = Math.max(0, Math.min(prog.active_seconds || 0, elapsed));
          const scroll = Math.round(prog.scroll_max_pct || 0);
          const hb = prog.heartbeats || 0;
          const need = { min_active_seconds: doc.min_active_seconds, have_active_seconds: active, scroll_max_pct: scroll };
          if (active < doc.min_active_seconds) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not enough active reading time', reason: `You have ${active}s of verified active reading; ${doc.min_active_seconds}s is required.`, need })); return; }
          if (elapsed < doc.min_active_seconds) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Page not open long enough', reason: `The page has only been open ${elapsed}s; keep it open for the full review time.`, need })); return; }
          if (doc.require_scroll_complete && scroll < 90) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Document not fully scrolled', reason: `You reached ${scroll}% of the page; scroll through at least 90% before acknowledging.`, need })); return; }
          if (hb < 3) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not enough activity recorded', reason: 'The page must stay open and active long enough to record multiple check-ins.', need })); return; }
          const comp = {
            doc_id: doc.id, doc_version: doc.version, user_email: email, user_name: session.name || email,
            opened_at: prog.server_open_at, acknowledged_at: new Date(now).toISOString(),
            active_seconds: active, scroll_max_pct: scroll, heartbeats: hb,
            user_agent: prog.user_agent || (req.headers['user-agent'] || ''), ip: prog.ip || (req.socket.remoteAddress || ''), valid: true
          };
          rr.completions.push(comp);
          // Propagate to the same person's linked account(s) so they complete required reading once.
          for (const alias of (RR_ALIASES[email] || [])) {
            const dupe = rr.completions.find(c => c.user_email === alias && c.doc_id === doc.id && c.doc_version === doc.version && c.valid);
            if (!dupe) rr.completions.push(Object.assign({}, comp, { user_email: alias, mirrored_from: email }));
          }
          rrSave(rr);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true, acknowledged_at: comp.acknowledged_at }));
        } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'bad request' })); }
      });
      return;
    }

    // GET /api/required-reading/admin → per-doc completion matrix over all active users
    if (req.url.split('?')[0] === '/api/required-reading/admin' && req.method === 'GET') {
      if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
      if (!rrIsAdmin(session)) { res.writeHead(403, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Admin/manager only' })); return; }
      const rr = rrLoad();
      const users = loadUsers().filter(u => u.active !== false);
      const matrix = rr.docs.map(d => {
        const rows = users.filter(u => rrRequired(d, u.role, u.departments)).map(u => {
          const email = (u.email || '').toLowerCase();
          const comp = (rr.completions || []).find(c => c.user_email === email && c.doc_id === d.id && c.doc_version === d.version);
          const prog = (rr.progress || []).find(p => p.user_email === email && p.doc_id === d.id && p.version === d.version);
          let status;
          if (comp && comp.valid) status = 'completed';
          else if (comp && !comp.valid) status = 'flagged';
          else if (prog) status = 'in-progress';
          else status = 'not-started';
          // PII guardrail: the training tracking/admin system exposes ONLY the employee's NAME
          // (plus training metadata) — never employee number, work email, or any other regulated
          // personal data. This object is built by explicit whitelist, so no user field can leak.
          return {
            name: u.name || '', role: u.role || 'member', status,
            active_seconds: comp ? comp.active_seconds : (prog ? (prog.active_seconds || 0) : 0),
            scroll_max_pct: comp ? comp.scroll_max_pct : (prog ? (prog.scroll_max_pct || 0) : 0),
            acknowledged_at: comp ? comp.acknowledged_at : null
          };
        });
        const completed = rows.filter(r => r.status === 'completed').length;
        return {
          doc: { id: d.id, title: d.title, version: d.version, url: d.url, min_active_seconds: d.min_active_seconds, required: d.required, description: d.description },
          rows,
          summary: { doc_id: d.id, total: rows.length, completed, pending: rows.length - completed }
        };
      });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ matrix }));
      return;
    }
  }

  // ── APAC DEAL FLOW: save/book/delete an opportunity (persists data/apac-opportunities.json) ──
  // Editors: admins, managers, and the APAC BD owner (Toshi). Members otherwise can only read.
  {
    const apacFp = path.join(__dirname, 'data', 'apac-opportunities.json');
    const apacCanEdit = (s) => s && (s.role === 'admin' || s.role === 'manager' || (s.email || '').toLowerCase() === 'toshihisa@exosaero.com');
    const apacNum = (v) => { const n = Number(String(v).replace(/[^0-9.\-]/g, '')); return isFinite(n) ? n : 0; };
    if (req.url.split('?')[0] === '/api/apac-opportunities/save' && req.method === 'POST') {
      const s = getSession(req);
      if (!apacCanEdit(s)) { res.writeHead(403, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not authorized to edit APAC deal flow' })); return; }
      let body = ''; req.on('data', c => { body += c; if (body.length > 2e5) req.destroy(); });
      req.on('end', () => {
        try {
          const inp = JSON.parse(body);
          const doc = JSON.parse(fs.readFileSync(apacFp, 'utf8'));
          doc.opportunities = doc.opportunities || [];
          const clean = {
            title: String(inp.title || '').slice(0, 200), country: String(inp.country || '').slice(0, 60),
            type: String(inp.type || '').slice(0, 60), stage: String(inp.stage || '').slice(0, 60),
            status: String(inp.status || 'Pursuing').slice(0, 40), value_usd: Math.max(0, apacNum(inp.value_usd)),
            value_display: String(inp.value_display || '').slice(0, 120), payload_kg: Math.max(0, apacNum(inp.payload_kg)),
            booked: !!inp.booked, priority: Math.max(0, Math.min(130, apacNum(inp.priority))),
            owner: String(inp.owner || 'Toshihisa Kumazawa').slice(0, 80),
            next_action: String(inp.next_action || '').slice(0, 400), description: String(inp.description || '').slice(0, 2000)
          };
          let id = String(inp.id || '').trim();
          if (id) {
            const idx = doc.opportunities.findIndex(o => o.id === id);
            if (idx >= 0) doc.opportunities[idx] = Object.assign(doc.opportunities[idx], clean, { id });
            else doc.opportunities.push(Object.assign({ id }, clean));
          } else {
            let mx = 0; doc.opportunities.forEach(o => { const m = /APAC-(\d+)/.exec(o.id || ''); if (m) mx = Math.max(mx, +m[1]); });
            id = 'APAC-' + String(mx + 1).padStart(3, '0');
            doc.opportunities.push(Object.assign({ id }, clean));
          }
          doc.generated_display = new Date().toISOString().slice(0, 10) + ' · edited in Mission Control';
          const tmp = apacFp + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(doc, null, 2)); fs.renameSync(tmp, apacFp);
          res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true, id }));
        } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: String(e.message || e) })); }
      });
      return;
    }
    if (req.url.split('?')[0] === '/api/apac-opportunities/delete' && req.method === 'POST') {
      const s = getSession(req);
      if (!apacCanEdit(s)) { res.writeHead(403, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not authorized' })); return; }
      let body = ''; req.on('data', c => { body += c; if (body.length > 1e4) req.destroy(); });
      req.on('end', () => {
        try {
          const { id } = JSON.parse(body);
          const doc = JSON.parse(fs.readFileSync(apacFp, 'utf8'));
          doc.opportunities = (doc.opportunities || []).filter(o => o.id !== id);
          const tmp = apacFp + '.tmp'; fs.writeFileSync(tmp, JSON.stringify(doc, null, 2)); fs.renameSync(tmp, apacFp);
          res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true }));
        } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: String(e.message || e) })); }
      });
      return;
    }
  }

  // ── WELCOME PAGE (early adopter onboarding) ──
  if ((req.url === '/welcome' || req.url === '/welcome.html') && req.method === 'GET') {
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(generateWelcomePage(session));
    return;
  }

  // ── PROCESS LIBRARY documents (session-gated) ── serves files from the workspace
  // process-library/ folder, EXCEPT Security/CUI (08), which is handled in GCC High and never
  // served here. Path-traversal safe.
  if (req.url.startsWith('/process-library/') && req.method === 'GET') {
    if (!getSession(req)) { res.writeHead(302, { Location: '/login' }); res.end(); return; }
    let rel = decodeURIComponent(req.url.replace(/^\/process-library\//, '').split('?')[0]).replace(/\\/g, '/');
    const base = path.join(__dirname, '..', 'process-library');
    const full = path.normalize(path.join(base, rel));
    if (!full.startsWith(base + path.sep)) { res.writeHead(403, { 'Content-Type': 'text/plain' }); res.end('bad path'); return; }
    if (/(^|\/)08-security-cui(\/|$)/i.test(rel)) {
      res.writeHead(403, { 'Content-Type': 'text/plain' });
      res.end('CUI documents are handled in GCC High (CMMC boundary), not Mission Control.'); return;
    }
    if (!fs.existsSync(full) || !fs.statSync(full).isFile()) { res.writeHead(404, { 'Content-Type': 'text/plain' }); res.end('not found'); return; }
    const ext = path.extname(full).toLowerCase();
    const ct = { '.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      '.doc': 'application/msword', '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
      '.md': 'text/markdown; charset=utf-8', '.txt': 'text/plain; charset=utf-8' }[ext] || 'application/octet-stream';
    res.writeHead(200, { 'Content-Type': ct, 'Content-Disposition': safeContentDisposition(path.basename(full), 'inline') });
    fs.createReadStream(full).pipe(res); return;
  }

  // ── TASKS API (Supabase-backed) ──
  // ── Global search across Mission Control (tasks, CRM, opportunities, decisions, …) ──
  if (req.url.split('?')[0] === '/api/search' && req.method === 'GET') {
    const s = getSession(req);
    if (!s) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    (async () => {
      const raw = (new URLSearchParams(req.url.split('?')[1] || '').get('q') || '').trim();
      if (raw.length < 2) { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ q: raw, groups: [], total: 0 })); return; }
      const ql = raw.toLowerCase();
      const enc = encodeURIComponent(raw.replace(/[(),*]/g, ' ').trim());
      const ilikeOr = cols => `or=(${cols.map(c => `${c}.ilike.*${enc}*`).join(',')})`;
      const dataDir = path.join(__dirname, 'data');
      const readJson = f => { try { return JSON.parse(fs.readFileSync(path.join(dataDir, f), 'utf8')); } catch (e) { return null; } };
      const hit = (obj, fields) => fields.some(f => String(obj[f] == null ? '' : obj[f]).toLowerCase().includes(ql));
      const groups = [];

      // -- Supabase-backed entities (live) --
      const sb = async (label, icon, table, cols, selectCols, mapper) => {
        try {
          const r = await supabaseRequest('GET', `${table}?select=${selectCols}&${ilikeOr(cols)}&limit=25`);
          const rows = Array.isArray(r.data) ? r.data : [];
          if (rows.length) groups.push({ key: table, label, icon, results: rows.map(mapper) });
        } catch (e) { /* one source failing must not break search */ }
      };
      await Promise.all([
        sb('Tasks', '📋', 'tasks', ['title', 'owner', 'category', 'description'],
           'id,title,owner,state,category,due_date',
           t => ({ title: t.title || '(untitled)', subtitle: [t.owner, t.category].filter(Boolean).join(' · '),
                   badge: t.state, url: `/index.html?task=${encodeURIComponent(t.id)}` })),
        sb('Contacts', '👤', 'contacts', ['name', 'email', 'organization', 'title', 'notes'],
           'id,name,email,organization,title',
           c => ({ title: c.name || c.email || '(contact)', subtitle: [c.title, c.organization, c.email].filter(Boolean).join(' · '),
                   badge: 'CRM', url: `/crm.html?q=${encodeURIComponent(c.name || c.email || '')}` })),
        sb('Companies', '🏢', 'companies', ['name', 'domain', 'industry', 'description'],
           'id,name,domain,industry',
           c => ({ title: c.name || c.domain || '(company)', subtitle: [c.industry, c.domain].filter(Boolean).join(' · '),
                   badge: 'CRM', url: `/crm.html?q=${encodeURIComponent(c.name || c.domain || '')}` })),
        sb('Deals', '💰', 'deals', ['name', 'notes', 'stage'],
           'id,name,stage,amount',
           d => ({ title: d.name || '(deal)', subtitle: [d.stage, d.amount ? ('$' + Number(d.amount).toLocaleString()) : ''].filter(Boolean).join(' · '),
                   badge: 'Deal', url: `/crm.html?q=${encodeURIComponent(d.name || '')}` })),
      ]);

      // -- Local JSON-backed entities (analytics-derived) --
      const opps = readJson('opportunities.json');
      if (opps && Array.isArray(opps.opportunities)) {
        const r = opps.opportunities.filter(o => hit(o, ['title', 'description', 'next_action', 'category', 'type', 'id'])).slice(0, 25);
        if (r.length) groups.push({ key: 'opportunities', label: 'Opportunities', icon: '🎯',
          results: r.map(o => ({ title: o.title || o.id, subtitle: [o.type, o.status, o.value].filter(Boolean).join(' · '),
            badge: o.priority ? ('P' + o.priority) : 'Opp', url: `/opportunities.html?focus=${encodeURIComponent(o.id)}` })) });
      }
      const dec = readJson('decisions.json');
      if (Array.isArray(dec)) {
        const r = dec.filter(d => hit(d, ['question', 'context', 'note', 'proposedAction', 'answer', 'id'])).slice(0, 25);
        if (r.length) groups.push({ key: 'decisions', label: 'Decisions', icon: '🗳️',
          results: r.map(d => ({ title: d.question || d.proposedAction || d.id, subtitle: (d.answer ? 'Answered: ' + d.answer : (d.context || '')).slice(0, 120),
            badge: d.answer ? 'answered' : 'open', url: `/decisions.html?focus=${encodeURIComponent(d.id)}` })) });
      }
      const dos = readJson('dossiers.json');
      if (dos && Array.isArray(dos.dossiers)) {
        const r = dos.dossiers.filter(d => hit(d, ['name', 'headline', 'next_step', 'status', 'stage', 'id'])).slice(0, 25);
        if (r.length) groups.push({ key: 'dossiers', label: 'Relationship Dossiers', icon: '🤝',
          results: r.map(d => ({ title: d.name || d.id, subtitle: (d.headline || d.next_step || '').slice(0, 120),
            badge: d.stage || 'dossier', url: `/dossier.html?q=${encodeURIComponent(d.name || '')}` })) });
      }
      const con = readJson('consortium.json');
      if (con && Array.isArray(con.partners)) {
        const r = con.partners.filter(p => hit(p, ['name', 'role', 'capabilities', 'scopes', 'status'])).slice(0, 25);
        if (r.length) groups.push({ key: 'consortium', label: 'Consortium Partners', icon: '🧩',
          results: r.map(p => ({ title: p.name, subtitle: (p.role || p.capabilities || '').toString().slice(0, 120),
            badge: p.status || 'partner', url: `/consortium.html` })) });
      }
      const gaps = readJson('capability-gaps.json');
      if (gaps && Array.isArray(gaps.gaps)) {
        const r = gaps.gaps.filter(g => hit(g, ['capability', 'description', 'category', 'tag', 'id'])).slice(0, 25);
        if (r.length) groups.push({ key: 'gaps', label: 'Capability Gaps', icon: '🧠',
          results: r.map(g => ({ title: g.capability || g.id, subtitle: (g.description || '').slice(0, 120),
            badge: g.severity || 'gap', url: `/capability-gaps.html` })) });
      }

      const total = groups.reduce((n, g) => n + g.results.length, 0);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ q: raw, total, groups }));
    })().catch(e => { res.writeHead(500, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: String(e && e.message || e) })); });
    return;
  }

  // ── Management report: per-employee task metrics (live from Supabase) ──────────────
  // Read-only analytics for the weekly leadership review. Admin/manager only (this exposes
  // whole-company workload, not just the caller's tasks). Names are normalized to a canonical
  // roster because owner strings drift (Jon / John Quinn / Jquinn / "Jon+Exo" all = one person).
  if (req.url.split('?')[0] === '/api/people-metrics' && req.method === 'GET') {
    const s = getSession(req);
    if (!s) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'auth required' })); return; }
    if (!(s.role === 'admin' || s.role === 'manager')) {
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Management report — leadership access only.' }));
      return;
    }
    (async () => {
      try {
        const COLS = 'id,title,owner,state,priority,due_date,completed_at,assigned_to,category';
        let rows = [];
        for (let page = 0, offset = 0; page < 50; page++) {
          const r = await supabaseRequest('GET', `tasks?select=${COLS}&order=id&limit=1000&offset=${offset}`);
          const chunk = Array.isArray(r.data) ? r.data : [];
          rows = rows.concat(chunk);
          if (chunk.length < 1000) break;
          offset += 1000;
        }

        // Canonical roster (from users.json) + known name aliases → one identity per person.
        const roster = loadUsers().filter(u => u.active).map(u => u.name);
        const ALIAS = {
          'jon': 'John Quinn', 'john quinn': 'John Quinn', 'jquinn': 'John Quinn', 'jon+exo': 'John Quinn', 'j quinn': 'John Quinn', 'quinn': 'John Quinn',
          'lizi quinn': 'Lizi Quinn', 'lquinn': 'Lizi Quinn', 'elizabeth quinn': 'Lizi Quinn', 'lizi': 'Lizi Quinn',
          'neil milburn': 'Neil Milburn', 'neil': 'Neil Milburn', 'nmilburn': 'Neil Milburn',
          'steve norsworthy': 'Steve Norsworthy', 'steven norsworthy': 'Steve Norsworthy', 'snorsworthy': 'Steve Norsworthy', 'steve': 'Steve Norsworthy',
          'phil eaton': 'Phil Eaton', 'phillip eaton': 'Phil Eaton', 'peaton': 'Phil Eaton', 'phil': 'Phil Eaton',
          'kyle ballard': 'Kyle Ballard', 'kballard': 'Kyle Ballard', 'kyle': 'Kyle Ballard',
          'russ blink': 'Russ Blink', 'russell blink': 'Russ Blink', 'rblink': 'Russ Blink', 'russ': 'Russ Blink',
          'mike talley': 'Mike Talley', 'michael talley': 'Mike Talley', 'mtalley': 'Mike Talley', 'mike': 'Mike Talley',
          'toshihisa kumazawa': 'Toshihisa Kumazawa', 'toshi': 'Toshihisa Kumazawa', 'toshihisa': 'Toshihisa Kumazawa',
          'andrew overman': 'Andrew Overman', 'aoverman': 'Andrew Overman',
          'victor castilleja': 'Victor Castilleja', 'vcastilleja': 'Victor Castilleja', 'victor': 'Victor Castilleja',
          'exo': 'Exo (AI)',
        };
        const HUMANS = ['John Quinn', 'Lizi Quinn', 'Neil Milburn', 'Steve Norsworthy', 'Phil Eaton', 'Kyle Ballard', 'Russ Blink', 'Mike Talley', 'Toshihisa Kumazawa', 'Andrew Overman', 'Victor Castilleja'];
        function canon(raw) {
          if (!raw) return '(unassigned)';
          // strip shared-task suffix "Name + 2 others" → attribute to the named lead
          let o = String(raw).replace(/\s*\+\s*\d+\s+other[s]?\s*$/i, '').trim();
          const k = o.toLowerCase();
          if (ALIAS[k]) return ALIAS[k];
          return o;
        }

        const now = Date.now(), DAY = 86400000;
        const wk = now + 7 * DAY, cut7 = now - 7 * DAY, cut30 = now - 30 * DAY;
        const ACTIVE = new Set(['To Do', 'In Progress', 'Queued', 'Blocked', 'Open']);
        const pd = (x) => { if (!x) return null; const t = Date.parse(x); return isNaN(t) ? null : t; };
        const M = {};
        const blank = () => ({ total: 0, open: 0, inprog: 0, blocked: 0, overdue: 0, dueweek: 0, high: 0, nodue: 0, done: 0, done7: 0, done30: 0, cats: {} });
        for (const t of rows) {
          const p = canon(t.owner || t.assigned_to);
          const m = (M[p] = M[p] || blank());
          m.total++;
          const st = t.state, pr = t.priority || 0;
          if (ACTIVE.has(st)) {
            m.open++;
            if (st === 'In Progress') m.inprog++;
            if (st === 'Blocked') m.blocked++;
            if (pr >= 80) m.high++;
            if (t.category) m.cats[t.category] = (m.cats[t.category] || 0) + 1;
            const dd = pd(t.due_date);
            if (dd) { if (dd < now) m.overdue++; else if (dd <= wk) m.dueweek++; }
            else m.nodue++;
          } else if (st === 'Done') {
            m.done++;
            const ca = pd(t.completed_at);
            if (ca && ca >= cut7) m.done7++;
            if (ca && ca >= cut30) m.done30++;
          }
        }
        // top category per person (their biggest active workstream)
        for (const p in M) {
          const c = M[p].cats; let best = null, bn = 0;
          for (const k in c) if (c[k] > bn) { bn = c[k]; best = k; }
          M[p].topCategory = best; M[p].topCategoryCount = bn; delete M[p].cats;
        }
        const people = Object.keys(M).map(name => ({ name, ...M[name] }));
        const isHuman = (n) => HUMANS.includes(n) || roster.includes(n);
        const employees = people.filter(p => isHuman(p.name)).sort((a, b) => b.open - a.open);
        const exo = people.find(p => p.name === 'Exo (AI)') || null;
        const others = people.filter(p => !isHuman(p.name) && p.name !== 'Exo (AI)')
          .sort((a, b) => (b.open + b.total) - (a.open + a.total));
        const totals = employees.reduce((s, p) => {
          for (const k of ['total', 'open', 'inprog', 'blocked', 'overdue', 'dueweek', 'high', 'done7', 'done30']) s[k] += p[k];
          return s;
        }, { total: 0, open: 0, inprog: 0, blocked: 0, overdue: 0, dueweek: 0, high: 0, done7: 0, done30: 0 });
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ generated_at: new Date().toISOString(), task_count: rows.length, totals, employees, exo, others }));
      } catch (e) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: String(e && e.message || e) }));
      }
    })();
    return;
  }

  if (req.url.split('?')[0] === '/api/tasks' && req.method === 'GET') {
    (async () => {
      try {
        // Column projection: skip `description` (≈70% of payload) from the board list — the detail
        // panel lazy-loads it via /api/task-desc. (Supabase health-check finding.)
        const BOARD_COLS = 'id,title,owner,state,created_at,priority,due_date,category,contact_id,deal_id,company_id,source,tags,completed_at,updated_at,assigned_to,assigned_email,assigned_at';
        // Delta polling: ?since=<iso> returns only rows changed since then (tiny), so the recurring
        // 30s poll stops re-pulling the whole board. The client does a periodic FULL load to
        // reconcile deletes. PostgREST caps responses at 1000 rows, so the full path pages by offset.
        const since = new URLSearchParams(req.url.split('?')[1] || '').get('since');
        let data = [], status = 200;
        if (since) {
          const r = await supabaseRequest('GET', `tasks?select=${BOARD_COLS}&updated_at=gt.${encodeURIComponent(since)}&order=updated_at.desc&limit=1000`);
          status = r.status; data = Array.isArray(r.data) ? r.data : [];
        } else {
          for (let page = 0, offset = 0; page < 50; page++) {
            const r = await supabaseRequest('GET', `tasks?select=${BOARD_COLS}&order=priority.desc.nullslast,due_date.asc.nullslast&limit=1000&offset=${offset}`);
            status = r.status;
            const chunk = Array.isArray(r.data) ? r.data : [];
            data = data.concat(chunk);
            if (chunk.length < 1000) break;
            offset += 1000;
          }
        }
        let filtered = data;
        // Members see tasks ASSIGNED to them (by email — the source of truth), plus legacy
        // name-owned tasks, plus shared/group tasks (owner 'Team' or tagged 'group').
        if (session && session.role === 'member' && Array.isArray(data)) {
          const me = (session.email || '').toLowerCase(), myname = session.name;
          filtered = data.filter(t =>
            (t.assigned_email || '').toLowerCase() === me
            || t.owner === myname || t.owner === session.email
            || t.owner === 'Team' || (Array.isArray(t.tags) && t.tags.includes('group')));
        }
        // Early adopters only see tasks in their assigned project (stored in user's project field)
        if (session && session.role === 'early_adopter' && Array.isArray(data)) {
          const users = loadUsers();
          const user = users.find(u => u.id === session.userId);
          const allowedProject = user && user.project ? user.project : null;
          if (allowedProject) {
            filtered = data.filter(t => t.category === allowedProject);
          } else {
            // No project assigned — show nothing (admin must assign a project)
            filtered = [];
          }
        }
        // Legacy MC board items (migrated into Supabase for decision-enrichment only)
        // are kept out of the active team board. They remain first-class, editable rows.
        if (Array.isArray(filtered)) filtered = filtered.filter(t => t.source !== 'mc-board-legacy');
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(filtered));
      } catch (e) { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); }
    })();
    return;
  }

  // Lazy-load a single task's description (the board list omits it to cut payload).
  if (req.url.split('?')[0] === '/api/task-desc' && req.method === 'GET') {
    const id = (new URLSearchParams(req.url.split('?')[1] || '')).get('id');
    if (!id) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'id required' })); return; }
    // early_adopter sandbox: only return the description if the task is in the user's
    // assigned project (same rule that scopes the board list). Prevents a sandbox user
    // from reading arbitrary task descriptions by id, while letting their own board work.
    const descCols = (session && session.role === 'early_adopter') ? 'id,description,category' : 'id,description';
    supabaseRequest('GET', `tasks?id=eq.${encodeURIComponent(id)}&select=${descCols}`)
      .then(({ data }) => {
        const row = Array.isArray(data) ? data[0] : null;
        if (session && session.role === 'early_adopter') {
          const users = loadUsers();
          const user = users.find(u => u.id === session.userId);
          const allowedProject = user && user.project ? user.project : null;
          if (!row || !allowedProject || row.category !== allowedProject) {
            auditDeny(session, req, 'out-of-scope-task-desc');
            res.writeHead(403, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Not permitted' }));
            return;
          }
        }
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ id, description: row ? (row.description || '') : '' }));
      })
      .catch(e => { res.writeHead(500, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: String(e).slice(0, 200) })); });
    return;
  }

  if (req.url === '/api/tasks' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const task = JSON.parse(body);
      if (!task.state) task.state = 'To Do';
      if (!task.priority && task.priority !== 0) task.priority = 50;
      supabaseRequest('POST', 'tasks', task)
        .then(({ status, data }) => {
          const created = Array.isArray(data) ? data[0] : data;
          // Assignment emails are now handled UNIVERSALLY by scripts/assignment-notifier.py
          // (covers app + auto-capture + agents + direct DB writes). Inline send disabled
          // here to avoid double-emailing app-path assignments. 2026-07-19.
          // if (created && created.owner) sendTaskAssignmentEmail(created, ...)
          res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(created));
        }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  if (req.url === '/api/tasks' && req.method === 'PATCH') {
    let body = ''; req.on('data', c => body += c); req.on('end', async () => {
      try {
        const { id, ...fields } = JSON.parse(body);
        if (fields.state === 'Done' && !fields.completed_at) fields.completed_at = new Date().toISOString();
        if (fields.state && fields.state !== 'Done') fields.completed_at = null;
        fields.updated_at = new Date().toISOString();   // stamp so delta polling reliably catches app edits

        // Fetch current task to diff changes
        const current = await supabaseRequest('GET', `tasks?id=eq.${id}&limit=1`);
        const oldTask = Array.isArray(current.data) && current.data[0] ? current.data[0] : {};

        // Keep assignment fields in sync when owner changes via the board dropdown.
        // The "My Tasks" filter treats assigned_email as the SOLE source of truth, so a
        // reassign that only touched `owner` left a stale assigned_email — making the task
        // still show under the PREVIOUS assignee (e.g. Neil's task lingering under Jon).
        // Resolve the new owner to a login account: set the email when matched, null it out
        // otherwise so the filter falls back to owner-name matching (the @Exobot path already
        // sets all three; this brings the UI dropdown to parity).
        if (fields.owner && fields.owner !== oldTask.owner) {
          // Multi-assignee: owner may be "Person A+Person B"; resolve each part to an email
          const ownerParts = String(fields.owner).split('+').map(p => p.trim()).filter(Boolean);
          const emails = ownerParts.map(p => {
            const u = findOwnerUser(p);
            return (u && u.email) ? u.email.toLowerCase() : null;
          }).filter(Boolean);
          fields.assigned_to = fields.owner;
          fields.assigned_email = emails.length > 0 ? emails.join(',') : null;
          fields.assigned_at = new Date().toISOString();
        }

        // Apply update
        const result = await supabaseRequest('PATCH', `tasks?id=eq.${id}`, fields);

        // Auto-log meaningful changes as comments
        const changes = [];
        if (fields.state && fields.state !== oldTask.state) changes.push(`State: ${oldTask.state || '?'} → ${fields.state}`);
        if (fields.owner && fields.owner !== oldTask.owner) changes.push(`Owner: ${oldTask.owner || '?'} → ${fields.owner}`);
        if (fields.title && fields.title !== oldTask.title) changes.push(`Title updated`);
        if (fields.priority !== undefined && fields.priority !== oldTask.priority) changes.push(`Priority: ${oldTask.priority || 0} → ${fields.priority}`);
        if (fields.due_date !== undefined && fields.due_date !== oldTask.due_date) {
          const oldD = oldTask.due_date ? oldTask.due_date.slice(0,10) : 'none';
          const newD = fields.due_date || 'none';
          changes.push(`Due date: ${oldD} → ${newD}`);
        }
        if (fields.description !== undefined && fields.description !== oldTask.description) changes.push(`Description updated`);
        if (fields.category !== undefined && fields.category !== oldTask.category) changes.push(`Category: ${oldTask.category || '?'} → ${fields.category || '?'}`);

        if (changes.length > 0) {
          const activity = {
            type: 'task_update',
            subject: `task:${id}`,
            body: `[Update] ${changes.join(' | ')}`,
            owner: fields.owner || oldTask.owner || 'System',
            status: 'completed',
          };
          supabaseRequest('POST', 'activities', activity).catch(() => {});
        }

        // Reassignment emails now handled UNIVERSALLY by scripts/assignment-notifier.py
        // (app + auto-capture + agents + direct DB). Inline send disabled to avoid
        // double-emailing. 2026-07-19.

        res.writeHead(result.status >= 400 ? result.status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(Array.isArray(result.data) ? result.data[0] : result.data));
      } catch(e) { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  if (req.url.startsWith('/api/tasks/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      supabaseRequest('DELETE', `tasks?id=eq.${id}`)
        .then(({ status }) => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true })); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── RESCORE — instant re-run of mission-score.py after a pin is set ──
  if (req.url === '/api/rescore' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { spawn } = require('child_process');
      const py = spawn('python3', ['/Users/exomac/.openclaw/workspace/scripts/mission-score.py'], {
        detached: true, stdio: 'ignore'
      });
      py.unref();
      res.writeHead(202, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ queued: true }));
    }); return;
  }

  // ── TASK UPDATES (uses activities table as timeline) ──
  if (req.url.startsWith('/api/tasks/updates') && req.method === 'GET') {
    const urlObj = new URL(req.url, 'http://localhost');
    const taskId = urlObj.searchParams.get('task_id');
    if (!taskId) { res.writeHead(400); res.end(JSON.stringify({ error: 'task_id required' })); return; }
    supabaseRequest('GET', `activities?subject=eq.task:${taskId}&order=created_at.asc&limit=500`)
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }

  if (req.url === '/api/tasks/updates' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { task_id, body: updateBody, owner } = JSON.parse(body);
      const activity = {
        type: 'task_note',
        subject: `task:${task_id}`,
        body: updateBody || '',
        owner: owner || 'Jon',
        status: 'completed',
      };
      supabaseRequest('POST', 'activities', activity)
        .then(({ status, data }) => {
          res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(Array.isArray(data) ? data[0] : data));
        }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── AUTO-CAPTURE: Create tasks from Series A / BD items ──
  if (req.url === '/api/tasks/capture' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { title, description, category, priority, due_date, owner, source, tags } = JSON.parse(body);
      const task = {
        title: title || 'Untitled task',
        description: description || null,
        category: category || 'Series A',
        priority: priority || (category === 'Series A' ? 90 : category === 'Revenue' ? 85 : 50),
        due_date: due_date || null,
        owner: owner || 'Jon',
        source: source || 'Telegram Series A',
        tags: tags || [],
        state: 'To Do',
      };
      supabaseRequest('POST', 'tasks', task)
        .then(({ status, data }) => {
          res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(Array.isArray(data) ? data[0] : data));
        }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // CRM API — backed by Supabase
  // Members: read-only CRM access
  if (req.url.startsWith('/api/crm') && req.method !== 'GET' && session && session.role === 'member') {
    res.writeHead(403, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ error: 'Read-only access — contact an admin to modify contacts' }));
    return;
  }
  // MNDA registry — reusable across CRM / ERP / dossiers. Optional ?company=Name → single match.
  if (req.url.split('?')[0] === '/api/mnda' && req.method === 'GET') {
    if (!getSession(req)) { res.writeHead(401, {'Content-Type':'application/json'}); res.end(JSON.stringify({error:'Unauthorized'})); return; }
    const q = new URL(req.url, 'http://localhost').searchParams.get('company');
    res.writeHead(200, {'Content-Type':'application/json'});
    res.end(JSON.stringify(q ? { company: q, mnda: mndaForCompany(q) } : { registry: loadMndaRegistry() }));
    return;
  }

  if (req.url.split('?')[0] === '/api/crm' && req.method === 'GET') {
    // Supabase caps at 1000 per request, so paginate
    async function fetchAllContacts() {
      const all = [];
      let offset = 0;
      const pageSize = 1000;
      while (true) {
        const { status, data } = await supabaseRequest('GET',
          `contacts?order=priority_score.desc.nullslast&limit=${pageSize}&offset=${offset}`);
        if (status >= 400) throw new Error(JSON.stringify(data));
        all.push(...data);
        if (data.length < pageSize) break;
        offset += pageSize;
      }
      return all;
    }
    fetchAllContacts()
      .then(data => {
        // Attach region; scope the result. A user with crm_region set (e.g. Toshi = Non-CONUS) is
        // FORCED to that segment; anyone else may filter with ?region=Non-CONUS|CONUS.
        const meU = (loadUsers().find(u => session && (u.id === session.userId
          || (session.email && (u.email || '').toLowerCase() === session.email.toLowerCase()))) || {});
        const q = new URL(req.url, 'http://localhost').searchParams.get('region');
        const want = meU.crm_region || (q && q.toLowerCase() !== 'all' ? q : null);
        let rows = data.map(toFrontend).map(r => ({ ...r, region: crmRegion(r), mnda: mndaForCompany(r.company), payloadCustomer: payloadCustomerForCompany(r.company) }));
        if (want) rows = rows.filter(r => (r.region || '').toLowerCase() === want.toLowerCase());
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(rows));
      })
      .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }

  if (req.url === '/api/crm' && req.method === 'PATCH') {
    let body = '';
    req.on('data', chunk => body += chunk.toString());
    req.on('end', () => {
      const update = JSON.parse(body);
      // DD pipeline gate: a failed-DD company can't advance to an engaged stage without an explicit override.
      const ddOverride = update.fields && (update.fields.dd_override === true || update.fields.dd_override === 'true');
      if (update.fields) delete update.fields.dd_override;   // control flag, not a Supabase column
      const sbFields = toSupabase(update.fields);
      const filter = update.id.startsWith('EXOS-')
        ? `contacts?crm_id=eq.${encodeURIComponent(update.id)}`
        : `contacts?id=eq.${encodeURIComponent(update.id)}`;
      const doPatch = () => {
        supabaseRequest('PATCH', filter, sbFields)
          .then(({ status, data }) => {
            if (status >= 400) { res.writeHead(status); res.end(JSON.stringify(data)); return; }
            const row = Array.isArray(data) && data[0] ? toFrontend(data[0]) : {};
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(row));
          })
          .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
      };
      const ADVANCED = ['Meeting Requested','Meeting Held','Engaged','Term Sheet / Proposal','Active','Engaged — Active Broker','Closed Won'];
      const newStage = update.fields && update.fields.stage;
      if (newStage && ADVANCED.includes(newStage) && !ddOverride) {
        supabaseRequest('GET', filter + '&select=email', null).then(({ data }) => {
          try {
            const email = ((Array.isArray(data) && data[0] && data[0].email) || '').toLowerCase();
            const dom = email.includes('@') ? email.split('@')[1] : '';
            let ddreg = {};
            try { ddreg = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'dd-registry.json'), 'utf-8')); } catch (e) {}
            const rec = dom && ddreg[dom];
            if (rec && rec.status === 'fail') {
              res.writeHead(409, { 'Content-Type': 'application/json' });
              res.end(JSON.stringify({ error: 'DD gate', ddFail: true, summary: rec.summary || '',
                message: `${dom} failed due diligence — cannot advance to "${newStage}" without an override. (${rec.summary || ''})` }));
              return;
            }
          } catch (e) {}
          doPatch();
        }).catch(() => doPatch());   // fail-open: never block editing on a lookup error
        return;
      }
      doPatch();
    });
    return;
  }

  if (req.url === '/api/crm' && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk.toString());
    req.on('end', () => {
      const newContact = JSON.parse(body);
      const sbFields = toSupabase(newContact);
      sbFields.status = 'Active';
      supabaseRequest('POST', 'contacts', sbFields)
        .then(({ status, data }) => {
          if (status >= 400) { res.writeHead(status); res.end(JSON.stringify(data)); return; }
          const row = Array.isArray(data) && data[0] ? toFrontend(data[0]) : {};
          res.writeHead(201, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(row));
        })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    });
    return;
  }

  // ── SENT REVIEW panel (option C): unlinked outbound sends + one-click link/dismiss ──
  {
    const SR_FILE = path.join(__dirname, 'data', 'sent-review.json');
    const SR_DISMISS = path.join(__dirname, '..', 'logs', 'sent-review-dismissed.json');
    const SR_LOG = path.join(__dirname, '..', 'logs', 'sent-followup-log.json');
    const srLoad = (p, d) => { try { return JSON.parse(fs.readFileSync(p, 'utf8')); } catch (e) { return d; } };
    if (req.url.split('?')[0] === '/api/sent-review' && req.method === 'GET') {
      if (!getSession(req)) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end('{"error":"auth"}'); return; }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(srLoad(SR_FILE, { items: [] }))); return;
    }
    if ((req.url.split('?')[0] === '/api/sent-review/link' || req.url.split('?')[0] === '/api/sent-review/dismiss') && req.method === 'POST') {
      const sess = getSession(req);
      if (!sess) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end('{"error":"auth"}'); return; }
      const isLink = req.url.split('?')[0].endsWith('/link');
      let body = ''; req.on('data', c => { body += c; if (body.length > 1e5) req.destroy(); });
      req.on('end', () => {
        let inp = {}; try { inp = JSON.parse(body); } catch (e) {}
        const contact = String(inp.contact || '').toLowerCase();
        if (!contact) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end('{"error":"contact required"}'); return; }
        const review = srLoad(SR_FILE, { items: [] });
        const item = (review.items || []).find(i => String(i.contact).toLowerCase() === contact) || {};
        // drop it from the review list + remember the decision so it doesn't re-surface
        review.items = (review.items || []).filter(i => String(i.contact).toLowerCase() !== contact);
        try { fs.writeFileSync(SR_FILE, JSON.stringify(review, null, 2)); } catch (e) {}
        const dis = srLoad(SR_DISMISS, []); if (!dis.includes(contact)) dis.push(contact);
        try { fs.writeFileSync(SR_DISMISS, JSON.stringify(dis, null, 2)); } catch (e) {}
        // update the follow-up log so the tracker keeps the linkage / doesn't re-add
        const flog = srLoad(SR_LOG, { contacts: {} });
        if (flog.contacts && flog.contacts[contact]) {
          flog.contacts[contact].conf = isLink ? 'high' : 'dismissed';
          if (isLink && inp.task_id) flog.contacts[contact].task_id = inp.task_id;
          try { fs.writeFileSync(SR_LOG, JSON.stringify(flog, null, 2)); } catch (e) {}
        }
        const finish = () => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true })); };
        if (isLink && inp.task_id) {
          supabaseRequest('POST', 'activities', {
            type: 'task_note', subject: 'task:' + inp.task_id, owner: 'Exo', status: 'completed',
            body: `📤 Email sent to ${item.name || contact} <${contact}> on ${item.last_sent || ''} — ${item.subj || ''}`
                  + (item.replied ? '' : '  ·  ⏳ awaiting reply')
          }).then(finish).catch(finish);
        } else { finish(); }
      });
      return;
    }
  }

  // ── FOLLOW-UPS panel (option B): awaiting-reply contacts + one-tap "✓ replied" / "dismiss" ──
  {
    const FU_LOG = path.join(__dirname, '..', 'logs', 'sent-followup-log.json');
    const fuLoad = () => { try { return JSON.parse(fs.readFileSync(FU_LOG, 'utf8')); } catch (e) { return { contacts: {} }; } };
    const MINd = 7, MAXd = 45;
    if (req.url.split('?')[0] === '/api/followups' && req.method === 'GET') {
      if (!getSession(req)) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end('{"error":"auth"}'); return; }
      const now = Date.now(); const out = [];
      const cs = fuLoad().contacts || {};
      for (const [a, c] of Object.entries(cs)) {
        if (c.replied || c.cleared || !c.last_sent) continue;
        const age = Math.floor((now - new Date(c.last_sent).getTime()) / 86400000);
        if (age < MINd || age > MAXd) continue;
        out.push({ contact: a, name: c.name || a, subj: (c.subj || '').slice(0, 80),
                   last_sent: String(c.last_sent).slice(0, 10), age, task_id: c.task_id || null });
      }
      out.sort((x, y) => y.age - x.age);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ count: out.length, items: out })); return;
    }
    if (req.url.split('?')[0] === '/api/followups/clear' && req.method === 'POST') {
      if (!getSession(req)) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end('{"error":"auth"}'); return; }
      let body = ''; req.on('data', c => { body += c; if (body.length > 1e4) req.destroy(); });
      req.on('end', () => {
        let inp = {}; try { inp = JSON.parse(body); } catch (e) {}
        const contact = String(inp.contact || '').toLowerCase();
        const doc = fuLoad();
        if (doc.contacts && doc.contacts[contact]) {
          if (inp.action === 'replied') doc.contacts[contact].replied = true;
          else doc.contacts[contact].cleared = true;
          try { fs.writeFileSync(FU_LOG, JSON.stringify(doc, null, 2)); } catch (e) {}
        }
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('{"ok":true}');
      });
      return;
    }
  }

  if (req.url.startsWith('/api/crm/delete') && req.method === 'POST') {
    let body = '';
    req.on('data', chunk => body += chunk.toString());
    req.on('end', () => {
      const { id } = JSON.parse(body);
      const filter = id.startsWith('EXOS-')
        ? `contacts?crm_id=eq.${encodeURIComponent(id)}`
        : `contacts?id=eq.${encodeURIComponent(id)}`;
      supabaseRequest('DELETE', filter)
        .then(({ status }) => {
          res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: status < 400 }));
        })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    });
    return;
  }

  // ── COMPANIES API ──
  if (req.url === '/api/companies' && req.method === 'GET') {
    supabaseGetAll('companies?order=name.asc')
      .then(({ status, data }) => {
        const out = Array.isArray(data) ? data.map(c => ({ ...c, mnda: mndaForCompany(c.name), payloadCustomer: payloadCustomerForCompany(c.name) })) : data;
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(out));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }
  if (req.url === '/api/companies' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      supabaseRequest('POST', 'companies', JSON.parse(body))
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url === '/api/companies' && req.method === 'PATCH') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id, ...fields } = JSON.parse(body);
      supabaseRequest('PATCH', `companies?id=eq.${id}`, fields)
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url.startsWith('/api/companies/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      supabaseRequest('DELETE', `companies?id=eq.${id}`)
        .then(({ status }) => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true })); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── Payload customers: read registry + TRUE customer metrics (feeds CRM badge + reporting) ──
  if (req.url.split('?')[0] === '/api/payload-customers' && req.method === 'GET') {
    const reg = loadPayloadCustomers();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ registry: reg, metrics: payloadCustomerMetrics(reg) }));
    return;
  }
  // ── Payload customers: upsert a PAID payload → flags the company as a payload customer ──
  // Body: { company, payload: { payload_name, mission, flight_date, mass_kg, contract_id,
  //   contract_value_usd, amount_paid_usd, paid_date, signed_contract_ref, signed_date, notes } }
  // (Exo can also update directly via scripts/payload_customer.py — same registry file.)
  if (req.url === '/api/payload-customers' && req.method === 'POST') {
    if (!session || (session.role !== 'admin' && session.role !== 'member')) {
      res.writeHead(403, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'forbidden' })); return;
    }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const company = (p.company || '').trim();
        if (!company) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'company required' })); return; }
        const reg = loadPayloadCustomers();
        const key = _mndaNorm(company);
        const now = new Date().toISOString().slice(0, 10);
        const rec = reg[key] || { company, payloads: [], created: now };
        rec.company = rec.company || company;
        rec.payloads = Array.isArray(rec.payloads) ? rec.payloads : [];
        if (p.payload && typeof p.payload === 'object') {
          rec.payloads.push({ ...p.payload, paid_date: p.payload.paid_date || now,
            logged: now, logged_by: (session && session.email) || 'Exo' });
        }
        recomputePayloadCustomer(rec);
        rec.updated = now;
        reg[key] = rec;
        savePayloadCustomers(reg);
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(rec));
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // ── DEALS API ──
  if (req.url === '/api/deals' && req.method === 'GET') {
    supabaseGetAll('deals?order=created_at.desc')
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }
  if (req.url === '/api/deals' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      supabaseRequest('POST', 'deals', JSON.parse(body))
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url === '/api/deals' && req.method === 'PATCH') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id, ...fields } = JSON.parse(body);
      supabaseRequest('PATCH', `deals?id=eq.${id}`, fields)
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url.startsWith('/api/deals/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      supabaseRequest('DELETE', `deals?id=eq.${id}`)
        .then(({ status }) => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true })); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── ACTIVITIES API ──
  if (req.url.startsWith('/api/activities') && req.method === 'GET') {
    const urlObj = new URL(req.url, 'http://localhost');
    const contact_id = urlObj.searchParams.get('contact_id');
    const deal_id = urlObj.searchParams.get('deal_id');
    const company_id = urlObj.searchParams.get('company_id');
    let query = 'activities?order=created_at.desc&limit=500';
    if (contact_id) query += `&contact_id=eq.${contact_id}`;
    if (deal_id) query += `&deal_id=eq.${deal_id}`;
    if (company_id) query += `&company_id=eq.${company_id}`;
    supabaseRequest('GET', query)
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }
  if (req.url === '/api/activities' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      supabaseRequest('POST', 'activities', JSON.parse(body))
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── EMAIL TEMPLATES API ──
  if (req.url === '/api/templates' && req.method === 'GET') {
    supabaseRequest('GET', 'email_templates?order=usage_count.desc&limit=100')
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }
  if (req.url === '/api/templates' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      supabaseRequest('POST', 'email_templates', JSON.parse(body))
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url === '/api/templates' && req.method === 'PATCH') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id, ...fields } = JSON.parse(body);
      supabaseRequest('PATCH', `email_templates?id=eq.${id}`, fields)
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url.startsWith('/api/templates/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      supabaseRequest('DELETE', `email_templates?id=eq.${id}`)
        .then(({ status }) => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true })); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── TEAM ROSTER (login accounts — used to populate owner dropdowns) ──
  if (req.url.startsWith('/api/team') && req.method === 'GET') {
    let team = [];
    try {
      team = loadUsers()
        .filter(u => u.active !== false)
        .map(u => ({ name: u.name, email: u.email, role: u.role }));
    } catch (e) {}
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(team));
    return;
  }

  // ── USERS API ──
  if (req.url.startsWith('/api/users') && req.method === 'GET') {
    supabaseRequest('GET', 'users?order=name.asc&limit=500')
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }

  // ── PROJECTS API ──
  if (req.url === '/api/projects' && req.method === 'GET') {
    supabaseRequest('GET', 'projects?order=name.asc&limit=500')
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }
  if (req.url === '/api/projects' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const proj = JSON.parse(body);
      if (!proj.status) proj.status = 'active';
      supabaseRequest('POST', 'projects', proj)
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url === '/api/projects' && req.method === 'PATCH') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id, ...fields } = JSON.parse(body);
      fields.updated_at = new Date().toISOString();
      supabaseRequest('PATCH', `projects?id=eq.${id}`, fields)
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url.startsWith('/api/projects/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      supabaseRequest('DELETE', `projects?id=eq.${id}`)
        .then(() => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true })); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── PROJECT DETAIL (tasks, lists, milestones for a single project) ──
  if (req.url.match(/^\/api\/projects\/[a-f0-9-]+$/) && req.method === 'GET') {
    const projId = req.url.split('/').pop();
    Promise.all([
      supabaseRequest('GET', `projects?id=eq.${projId}&limit=1`),
      supabaseRequest('GET', `task_lists?project_id=eq.${projId}&order=position.asc&limit=500`),
      supabaseGetAll(`tasks?project_id=eq.${projId}&order=position.asc`),
      supabaseRequest('GET', `milestones?project_id=eq.${projId}&order=due_date.asc&limit=100`),
      supabaseRequest('GET', `time_entries?project_id=eq.${projId}&order=date.desc&limit=500`),
    ]).then(([project, lists, tasks, milestones, timeEntries]) => {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        project: Array.isArray(project.data) ? project.data[0] : project.data,
        task_lists: Array.isArray(lists.data) ? lists.data : [],
        tasks: Array.isArray(tasks.data) ? tasks.data : [],
        milestones: Array.isArray(milestones.data) ? milestones.data : [],
        time_entries: Array.isArray(timeEntries.data) ? timeEntries.data : [],
      }));
    }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }

  // ── TASK LISTS API ──
  if (req.url.startsWith('/api/task-lists') && req.method === 'GET') {
    const urlObj = new URL(req.url, 'http://localhost');
    const project_id = urlObj.searchParams.get('project_id');
    let query = 'task_lists?order=position.asc&limit=500';
    if (project_id) query += `&project_id=eq.${project_id}`;
    supabaseRequest('GET', query)
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }
  if (req.url === '/api/task-lists' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      supabaseRequest('POST', 'task_lists', JSON.parse(body))
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url === '/api/task-lists' && req.method === 'PATCH') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id, ...fields } = JSON.parse(body);
      supabaseRequest('PATCH', `task_lists?id=eq.${id}`, fields)
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url.startsWith('/api/task-lists/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      supabaseRequest('DELETE', `task_lists?id=eq.${id}`)
        .then(() => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true })); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── MILESTONES API ──
  if (req.url.startsWith('/api/milestones') && req.method === 'GET') {
    const urlObj = new URL(req.url, 'http://localhost');
    const project_id = urlObj.searchParams.get('project_id');
    let query = 'milestones?order=due_date.asc&limit=500';
    if (project_id) query += `&project_id=eq.${project_id}`;
    supabaseRequest('GET', query)
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }
  if (req.url === '/api/milestones' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      supabaseRequest('POST', 'milestones', JSON.parse(body))
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url === '/api/milestones' && req.method === 'PATCH') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id, ...fields } = JSON.parse(body);
      supabaseRequest('PATCH', `milestones?id=eq.${id}`, fields)
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url.startsWith('/api/milestones/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      supabaseRequest('DELETE', `milestones?id=eq.${id}`)
        .then(() => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true })); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── TIME ENTRIES API ──
  if (req.url.startsWith('/api/time-entries') && req.method === 'GET') {
    const urlObj = new URL(req.url, 'http://localhost');
    const task_id = urlObj.searchParams.get('task_id');
    const project_id = urlObj.searchParams.get('project_id');
    const user_id = urlObj.searchParams.get('user_id');
    let query = 'time_entries?order=date.desc&limit=1000';
    if (task_id) query += `&task_id=eq.${task_id}`;
    if (project_id) query += `&project_id=eq.${project_id}`;
    if (user_id) query += `&user_id=eq.${user_id}`;
    supabaseRequest('GET', query)
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }
  if (req.url === '/api/time-entries' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      supabaseRequest('POST', 'time_entries', JSON.parse(body))
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url.startsWith('/api/time-entries/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      supabaseRequest('DELETE', `time_entries?id=eq.${id}`)
        .then(() => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true })); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── COMMENTS API ──
  if (req.url.startsWith('/api/comments') && req.method === 'GET') {
    const urlObj = new URL(req.url, 'http://localhost');
    const task_id = urlObj.searchParams.get('task_id');
    let query = 'comments?order=created_at.asc&limit=500';
    if (task_id) query += `&task_id=eq.${task_id}`;
    supabaseRequest('GET', query)
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }
  if (req.url === '/api/comments' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      supabaseRequest('POST', 'comments', JSON.parse(body))
        .then(({ status, data }) => { res.writeHead(status >= 400 ? status : 201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(Array.isArray(data) ? data[0] : data)); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }
  if (req.url.startsWith('/api/comments/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      const { id } = JSON.parse(body);
      supabaseRequest('DELETE', `comments?id=eq.${id}`)
        .then(() => { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ success: true })); })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    }); return;
  }

  // ── INBOUND EMAIL WEBHOOK (for project-email-router) ──
  if (req.url === '/api/inbound-email' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const { project_id, task_id, subject, sender_name, sender_email, body: emailBody, state_change } = JSON.parse(body);

        const promises = [];

        // Log as comment on project/task
        const comment = {
          project_id: project_id || null,
          task_id: task_id || null,
          body: `Email from ${sender_name} (${sender_email}): ${subject}\n\n${(emailBody || '').substring(0, 500)}`,
        };
        promises.push(supabaseRequest('POST', 'comments', comment));

        // Update task state if detected
        if (task_id && state_change) {
          const updates = { state: state_change };
          if (state_change === 'Done') {
            updates.completed_at = new Date().toISOString();
            updates.progress = 100;
          }
          promises.push(supabaseRequest('PATCH', `tasks?id=eq.${task_id}`, updates));
        }

        Promise.all(promises).then(() => {
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: true, project_id, task_id, state_change }));
        }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid JSON: ' + e.message }));
      }
    }); return;
  }

  // ── NOTIFICATIONS FEED (Discord notification queue) ──
  if (req.url === '/api/notifications' && req.method === 'GET') {
    const notifFile = path.join(__dirname, '../scripts/discord-notifications.jsonl');
    if (fs.existsSync(notifFile)) {
      const lines = fs.readFileSync(notifFile, 'utf-8').split('\n').filter(Boolean);
      const notifications = lines.map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(notifications.slice(-50))); // last 50
    } else {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end('[]');
    }
    return;
  }

  if (req.url === '/api/notifications/clear' && req.method === 'POST') {
    const notifFile = path.join(__dirname, '../scripts/discord-notifications.jsonl');
    if (fs.existsSync(notifFile)) fs.writeFileSync(notifFile, '');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true }));
    return;
  }

  // ── EXOSOPS DASHBOARD (unified stats) ──
  if (req.url === '/api/exosops/dashboard' && req.method === 'GET') {
    Promise.all([
      supabaseRequest('GET', 'projects?select=id,name,status&limit=500'),
      supabaseGetAll('tasks?select=id,state,project_id,priority,due_date'),
      supabaseRequest('GET', 'milestones?select=id,status,due_date&limit=500'),
      supabaseGetAll('time_entries?select=id,hours,date'),
      supabaseRequest('GET', 'users?select=id,name&limit=100'),
      supabaseRequest('GET', 'contacts?select=id&limit=1'),
      supabaseGetAll('deals?select=id,stage,amount'),
    ]).then(([projects, tasks, milestones, timeEntries, users, contacts, deals]) => {
      const projData = Array.isArray(projects.data) ? projects.data : [];
      const taskData = Array.isArray(tasks.data) ? tasks.data : [];
      const msData = Array.isArray(milestones.data) ? milestones.data : [];
      const teData = Array.isArray(timeEntries.data) ? timeEntries.data : [];
      const dealData = Array.isArray(deals.data) ? deals.data : [];

      const totalHours = teData.reduce((s, e) => s + (Number(e.hours) || 0), 0);
      const pipelineValue = dealData.reduce((s, d) => s + (Number(d.amount) || 0), 0);

      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        projects: { total: projData.length, active: projData.filter(p => p.status === 'active').length },
        tasks: {
          total: taskData.length,
          todo: taskData.filter(t => t.state === 'To Do').length,
          in_progress: taskData.filter(t => t.state === 'In Progress').length,
          blocked: taskData.filter(t => t.state === 'Blocked').length,
          done: taskData.filter(t => t.state === 'Done').length,
          overdue: taskData.filter(t => t.due_date && new Date(t.due_date) < new Date() && t.state !== 'Done').length,
        },
        milestones: { total: msData.length, upcoming: msData.filter(m => m.status === 'upcoming').length },
        time: { total_hours: Math.round(totalHours * 10) / 10 },
        team: { total: Array.isArray(users.data) ? users.data.length : 0 },
        crm: {
          contacts: Array.isArray(contacts.data) ? contacts.data.length : 0,
          deals: dealData.length,
          pipeline_value: pipelineValue,
        },
      }));
    }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }

  // ── DASHBOARD STATS API ──
  if (req.url === '/api/dashboard' && req.method === 'GET') {
    Promise.all([
      supabaseRequest('GET', 'contacts?select=id&limit=1&Prefer=count=exact'),
      supabaseGetAll('deals?select=id,stage,amount'),
      supabaseRequest('GET', 'activities?select=id,type,created_at&order=created_at.desc&limit=100'),
      supabaseRequest('GET', 'companies?select=id&limit=1'),
    ]).then(([contacts, deals, activities, companies]) => {
      const dealData = Array.isArray(deals.data) ? deals.data : [];
      const pipeline = {};
      let totalValue = 0;
      let weightedValue = 0;
      dealData.forEach(d => {
        pipeline[d.stage] = (pipeline[d.stage] || 0) + 1;
        const amt = Number(d.amount) || 0;
        totalValue += amt;
      });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        total_contacts: Array.isArray(contacts.data) ? contacts.data.length : 0,
        total_deals: dealData.length,
        total_companies: Array.isArray(companies.data) ? companies.data.length : 0,
        pipeline_value: totalValue,
        pipeline_stages: pipeline,
        recent_activities: Array.isArray(activities.data) ? activities.data.slice(0, 20) : [],
      }));
    }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }

  // ── TEAMWORK SYNC (import Teamwork tasks into local Supabase) ──
  if (req.url === '/api/teamwork/sync' && req.method === 'POST') {
    (async () => {
      try {
        // 1. Fetch all open tasks from Teamwork projects
        const results = await Promise.all(
          TEAMWORK_PROJECTS.map(pid =>
            teamworkFetch(`/projects/${pid}/tasks.json?includeCompletedTasks=false&pageSize=250`)
              .then(d => (d['todo-items'] || []).map(t => ({ ...t, _projectId: pid })))
          )
        );
        const twTasks = results.flat();

        // 2. Fetch existing synced tasks from Supabase
        const existing = await supabaseGetAll('tasks?source=like.teamwork-*');
        const existingMap = {};
        if (Array.isArray(existing.data)) {
          existing.data.forEach(t => { existingMap[t.source] = t; });
        }

        let created = 0, updated = 0, skipped = 0;

        for (const tw of twTasks) {
          const sourceKey = `teamwork-${tw.id}`;
          const assignee = tw['responsible-party-summary'] || '';
          let owner = 'Jon';
          if (assignee.toLowerCase().includes('quinn') || assignee === 'You') owner = 'Jon';
          else if (assignee && assignee !== 'Unassigned') owner = assignee.split(',')[0].trim();

          const taskData = {
            title: tw.content,
            description: `[${tw['project-name'] || 'Teamwork'}] ${tw['todo-list-name'] || ''}\nAssignee: ${assignee}`.trim(),
            state: teamworkStateMap(tw.status),
            owner,
            priority: teamworkPriorityToNum(tw.priority),
            due_date: teamworkDateToISO(tw['due-date']),
            category: tw['project-name'] || 'Teamwork',
            source: sourceKey,
            tags: ['teamwork', tw['project-name'] || ''].filter(Boolean),
          };

          if (existingMap[sourceKey]) {
            // Update existing — preserve local state overrides
            const ex = existingMap[sourceKey];
            // Only update title, description, due_date, priority if not locally modified
            await supabaseRequest('PATCH', `tasks?id=eq.${ex.id}`, {
              title: taskData.title,
              description: taskData.description,
              due_date: taskData.due_date,
              priority: taskData.priority,
              category: taskData.category,
            });
            updated++;
          } else {
            // Create new
            await supabaseRequest('POST', 'tasks', taskData);
            created++;
          }
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({
          success: true,
          total_teamwork: twTasks.length,
          created,
          updated,
          skipped,
          message: `Synced ${twTasks.length} tasks from Teamwork (${created} new, ${updated} updated)`
        }));
      } catch (e) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Teamwork sync failed: ' + e.message }));
      }
    })();
    return;
  }

  // ── TEAMWORK STATUS (check connection without syncing) ──
  if (req.url === '/api/teamwork/status' && req.method === 'GET') {
    teamworkFetch('/projects.json')
      .then(data => {
        const projects = data.projects || [];
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ connected: true, projects: projects.length }));
      })
      .catch(e => {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ connected: false, error: e.message }));
      });
    return;
  }

  // ── DocuSign: Send document via email ──
  if (req.url === '/api/docusign/send' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', async () => {
      try {
        const { recipients, subject, message, documentTitle, documentHtml } = JSON.parse(body);
        if (!recipients || !recipients.length) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'No recipients specified' }));
          return;
        }

        // Build Proton Bridge SMTP transport
        const bridgeCert = fs.existsSync('/Users/exomac/.protonmail-bridge.crt')
          ? fs.readFileSync('/Users/exomac/.protonmail-bridge.crt') : undefined;
        const transporter = nodemailer.createTransport({
          host: '127.0.0.1',
          port: 1025,
          secure: false,
          requireTLS: true,
          tls: { ca: bridgeCert, rejectUnauthorized: false },
          auth: { user: 'jquinnexo@pm.me', pass: 'SPqYBivj98-jyF3RujLKxA' }
        });

        // Build HTML email body
        const htmlBody = `
          <div style="font-family:Arial,sans-serif;max-width:700px;margin:0 auto;">
            <div style="background:#0a1628;padding:20px 24px;border-radius:8px 8px 0 0;">
              <h2 style="color:#f5a623;margin:0;font-size:18px;">Exos Aerospace — Document for Signature</h2>
            </div>
            <div style="background:#ffffff;padding:24px;border:1px solid #ddd;">
              <p style="color:#333;line-height:1.6;">${message.replace(/\n/g, '<br>')}</p>
              <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
              <h3 style="color:#0a1628;margin-bottom:12px;">${documentTitle || 'Document'}</h3>
              ${documentHtml || ''}
              <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
              <p style="font-size:12px;color:#888;line-height:1.5;">
                This document was sent via Exos Aerospace DocuSign.<br>
                To sign, please review the document above, print, sign, and return a scanned copy to
                <a href="mailto:jquinn@exosaero.com">jquinn@exosaero.com</a>.<br><br>
                <em>This is a legally binding document. By signing, you agree to the terms contained herein
                under the U.S. E-SIGN Act (15 U.S.C. §7001) and UETA.</em>
              </p>
            </div>
            <div style="background:#f5f5f5;padding:12px 24px;border-radius:0 0 8px 8px;border:1px solid #ddd;border-top:none;">
              <p style="font-size:11px;color:#999;margin:0;">
                Exos Aerospace Systems & Technologies, Inc. | 299 FM 1903, Greenville, TX 75402 | jquinn@exosaero.com
              </p>
            </div>
          </div>`;

        const recipientEmails = recipients.map(r => r.email).filter(Boolean);
        const recipientNames = recipients.map(r => `${r.name} <${r.email}>`).filter(r => r.includes('@'));

        const info = await transporter.sendMail({
          from: '"John Quinn — Exos Aerospace" <jquinnexo@pm.me>',
          replyTo: 'jquinn@exosaero.com',
          to: recipientEmails.join(', '),
          subject: subject || `Exos Aerospace — ${documentTitle || 'Document'} for Signature`,
          html: htmlBody
        });

        console.log(`[DocuSign] Email sent to ${recipientEmails.join(', ')} — messageId: ${info.messageId}`);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, messageId: info.messageId, recipients: recipientEmails }));
      } catch(e) {
        console.error('[DocuSign] Email send error:', e.message);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Failed to send email: ' + e.message }));
      }
    }); return;
  }

  // ════════════════════════════════════════════════════════════════════
  //  E-SIGN: real self-hosted e-signature (signing links + capture)
  // ════════════════════════════════════════════════════════════════════
  if (req.url === '/api/esign/create' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', async () => {
      try {
        const { title, html, message, subject, signers } = JSON.parse(body);
        const valid = (signers || []).filter(s => s && s.email);
        if (!valid.length) { res.writeHead(400, {'Content-Type':'application/json'}); res.end(JSON.stringify({error:'No signers with email'})); return; }
        const host = req.headers['host'] || 'localhost:8080';
        // Prefer explicit env var, then fall back to a local config file, then use host header
        let mcPublicUrl = process.env.MC_PUBLIC_URL;
        if (!mcPublicUrl) {
          try { mcPublicUrl = require('fs').readFileSync(require('path').join(__dirname, '.public-url'), 'utf-8').trim(); } catch {}
        }
        const base = (mcPublicUrl || ('http://' + host)).replace(/\/+$/, '');
        // Signing order (John 2026-09-01): the counterparty signs FIRST, Exos countersigns LAST,
        // so we control final execution and are never bound while waiting on the other side. Push any
        // Exos signer to the end (stable, preserves counterparty order) regardless of submitted order.
        const isExosSigner = (s) => /@exosaero\.com$/i.test(s.email||'') || /\bquinn\b/i.test(s.name||'');
        const ordered = [...valid].sort((a,b) => (isExosSigner(a)?1:0) - (isExosSigner(b)?1:0));
        const env = {
          id: esignToken().slice(0,12), title: title || 'Document', html: html || '',
          message: message || '', subject: subject || ('Signature requested: ' + (title||'Document')),
          createdAt: new Date().toISOString(), expiresAt: new Date(Date.now() + 5*24*60*60*1000).toISOString(), status: 'pending',
          base: base,
          signers: ordered.map(s => ({ name: s.name||'Signer', email: s.email, role: s.role||'', token: esignToken(), signed:false, signedAt:null, ip:null, signatureType:null, signatureData:null }))
        };
        const all = loadEnvelopes(); all.push(env); saveEnvelopes(all);
        const t = esignTransport();
        // All links (for the API response/admin), but SEQUENTIAL routing: email only the first
        // (counterparty) signer now; each subsequent signer is emailed as the prior one completes.
        const links = env.signers.map(s => ({ email: s.email, name: s.name, link: base + '/sign?token=' + s.token }));
        const first = env.signers.find(s => !s.signed);
        if (first) {
          const link = base + '/sign?token=' + first.token;
          try { await t.sendMail({ from: '"John Quinn — Exos Aerospace" <jquinnexo@pm.me>', replyTo: 'jquinn@exosaero.com', to: first.email, subject: env.subject, html: esignRequestEmail(first, link, env) }); }
          catch (e) { console.error('[E-Sign] link email error to', first.email, e.message); }
        }
        console.log('[E-Sign] Envelope ' + env.id + ' created; sequential signing, first link sent to ' + (first ? first.email : 'n/a'));
        res.writeHead(200, {'Content-Type':'application/json'}); res.end(JSON.stringify({ success:true, id: env.id, links }));
      } catch (e) { console.error('[E-Sign] create error:', e.message); res.writeHead(500,{'Content-Type':'application/json'}); res.end(JSON.stringify({error:e.message})); }
    }); return;
  }

  if (req.url.startsWith('/api/esign/get') && req.method === 'GET') {
    const token = new URLSearchParams((req.url.split('?')[1]||'')).get('token');
    const all = loadEnvelopes();
    let env=null, signer=null;
    for (const e of all) { const s = e.signers.find(x => x.token === token); if (s) { env=e; signer=s; break; } }
    if (!env) { res.writeHead(404,{'Content-Type':'application/json'}); res.end(JSON.stringify({error:'Invalid or expired signing link'})); return; }
    // Hardening: link closes once this signer has signed, or after the 5-day TTL (can't reopen to view).
    const _expired = env.expiresAt && Date.now() > Date.parse(env.expiresAt);
    if (signer.signed || _expired) {
      res.writeHead(410,{'Content-Type':'application/json'});
      res.end(JSON.stringify({ closed:true, reason: signer.signed?'signed':'expired', signedAt: signer.signedAt, expiresAt: env.expiresAt,
        error: signer.signed ? 'This document has already been signed — the link is now closed.' : 'This signing link has expired (5-day limit).' }));
      return;
    }
    res.writeHead(200,{'Content-Type':'application/json'});
    res.end(JSON.stringify({
      title: env.title, html: env.html, message: env.message, status: env.status,
      signer: { name: signer.name, email: signer.email, role: signer.role, signed: signer.signed, signedAt: signer.signedAt },
      signers: env.signers.map(s => ({ name: s.name, role: s.role, signed: s.signed, signedAt: s.signedAt }))
    }));
    return;
  }

  if (req.url === '/api/esign/list' && req.method === 'GET') {
    const session = getSession(req);
    if (!session) { res.writeHead(401,{'Content-Type':'application/json'}); res.end(JSON.stringify({error:'Unauthorized'})); return; }
    const all = loadEnvelopes();
    const isAdmin = session.role === 'admin';
    const myEmail = (session.email||'').toLowerCase();
    const now = Date.now();
    const out = [];
    for (const e of all) {
      const mine = (e.signers||[]).find(s => (s.email||'').toLowerCase() === myEmail);
      if (!isAdmin && !mine) continue; // non-admins see only envelopes they are a signer on
      const expired = e.expiresAt && now > Date.parse(e.expiresAt);
      out.push({
        id: e.id, title: e.title, status: expired && e.status!=='completed' ? 'expired' : e.status,
        createdAt: e.createdAt, expiresAt: e.expiresAt,
        myToken: (mine && !mine.signed && !expired) ? mine.token : null,
        mySigned: mine ? mine.signed : null,
        signers: (e.signers||[]).map(s => ({ name:s.name, email:s.email, role:s.role, signed:s.signed, signedAt:s.signedAt }))
      });
    }
    out.sort((a,b) => String(b.createdAt||'').localeCompare(String(a.createdAt||'')));
    res.writeHead(200,{'Content-Type':'application/json'}); res.end(JSON.stringify({ envelopes: out }));
    return;
  }

  if (req.url === '/api/esign/sign' && req.method === 'POST') {
    let body=''; req.on('data',c=>body+=c); req.on('end', async () => {
      try {
        const { token, signatureType, signatureData } = JSON.parse(body);
        if (!signatureData) { res.writeHead(400,{'Content-Type':'application/json'}); res.end(JSON.stringify({error:'No signature provided'})); return; }
        const all = loadEnvelopes();
        let env=null, signer=null;
        for (const e of all) { const s = e.signers.find(x => x.token === token); if (s) { env=e; signer=s; break; } }
        if (!env) { res.writeHead(404,{'Content-Type':'application/json'}); res.end(JSON.stringify({error:'Invalid signing link'})); return; }
        if (env.expiresAt && Date.now() > Date.parse(env.expiresAt)) { res.writeHead(410,{'Content-Type':'application/json'}); res.end(JSON.stringify({error:'This signing link has expired (5-day limit).'})); return; }
        if (signer.signed) { res.writeHead(409,{'Content-Type':'application/json'}); res.end(JSON.stringify({error:'This document has already been signed — the link is closed.'})); return; }
        if (!signer.signed) {
          signer.signed = true;
          signer.signedAt = new Date().toISOString();
          signer.ip = (req.headers['x-forwarded-for']||'').split(',')[0].trim() || req.socket.remoteAddress || '';
          signer.signatureType = signatureType || 'typed';
          signer.signatureData = signatureData;
        }
        const allSigned = env.signers.every(s => s.signed);
        if (allSigned && env.status !== 'completed') { env.status = 'completed'; env.completedAt = new Date().toISOString(); }
        saveEnvelopes(all);
        // Sequential routing: now that this signer is done, email the NEXT unsigned signer their link
        // (counterparty first → Exos last). Failure here is logged, not fatal to this signature.
        if (!allSigned) {
          const next = env.signers.find(s => !s.signed);
          if (next) {
            try {
              const t2 = esignTransport();
              const base2 = env.base || ('http://' + (req.headers.host || ''));
              const link = base2 + '/sign?token=' + next.token;
              await t2.sendMail({ from: '"John Quinn — Exos Aerospace" <jquinnexo@pm.me>', replyTo: 'jquinn@exosaero.com', to: next.email, subject: env.subject, html: esignRequestEmail(next, link, env) });
              console.log('[E-Sign] Envelope ' + env.id + ': ' + signer.email + ' signed; next link sent to ' + next.email);
            } catch(e){ console.error('[E-Sign] next-signer email error:', e.message); }
          }
        }
        if (allSigned) { try { await esignDeliverCompleted(env); } catch(e){ console.error('[E-Sign] completed delivery error:', e.message); } }
        res.writeHead(200,{'Content-Type':'application/json'}); res.end(JSON.stringify({ success:true, allSigned }));
      } catch (e) { console.error('[E-Sign] sign error:', e.message); res.writeHead(500,{'Content-Type':'application/json'}); res.end(JSON.stringify({error:e.message})); }
    }); return;
  }

  // ── DOCUMENT UPLOADS API ──

  // Upload a file attached to a task/project
  if (req.url === '/api/uploads' && req.method === 'POST') {
    (async () => {
      try {
        const parts = await parseMultipart(req);
        const file = parts.file;
        const taskId = parts.task_id || null;
        const projectId = parts.project_id || null;
        const decisionId = parts.decision_id || null;

        if (!file || !file.filename) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: 'No file provided' }));
          return;
        }

        // Validate extension
        const ext = path.extname(file.filename).toLowerCase();
        if (!ALLOWED_EXTENSIONS.includes(ext)) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: `File type ${ext} not allowed. Supported: ${ALLOWED_EXTENSIONS.join(', ')}` }));
          return;
        }

        // Generate unique filename
        const timestamp = Date.now();
        const safeName = file.filename.replace(/[^a-zA-Z0-9._-]/g, '_');
        const storedName = `${timestamp}_${safeName}`;
        const filePath = path.join(UPLOADS_DIR, storedName);

        fs.writeFileSync(filePath, file.data);

        // Save metadata
        const meta = loadUploadsMeta();
        const entry = {
          id: crypto.randomBytes(8).toString('hex'),
          filename: file.filename,
          stored_name: storedName,
          size: file.data.length,
          extension: ext,
          task_id: taskId,
          project_id: projectId,
          decision_id: decisionId,
          uploaded_by: session ? session.name : 'Unknown',
          uploaded_at: new Date().toISOString(),
        };
        meta.push(entry);
        saveUploadsMeta(meta);

        // Log as activity on the task
        if (taskId) {
          const sizeKB = Math.round(file.data.length / 1024);
          supabaseRequest('POST', 'activities', {
            type: 'task_note',
            subject: `task:${taskId}`,
            body: `Document uploaded: ${file.filename} (${sizeKB} KB)`,
            owner: session ? session.name : 'System',
            status: 'completed',
          }).catch(() => {});
        }

        res.writeHead(201, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(entry));
      } catch (e) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: e.message }));
      }
    })();
    return;
  }

  // List uploads for a task or project
  if (req.url.startsWith('/api/uploads') && req.method === 'GET') {
    const urlObj = new URL(req.url, 'http://localhost');
    const taskId = urlObj.searchParams.get('task_id');
    const projectId = urlObj.searchParams.get('project_id');
    const decisionId = urlObj.searchParams.get('decision_id');
    const history = urlObj.searchParams.get('history');
    let meta = loadUploadsMeta();
    if (taskId) meta = meta.filter(m => String(m.task_id) === String(taskId));
    else if (projectId) meta = meta.filter(m => String(m.project_id) === String(projectId));
    else if (decisionId) meta = meta.filter(m => String(m.decision_id) === String(decisionId));
    // Default: only the current version of each document; archived prior versions are
    // hidden unless ?history=1. Legacy records (no `current` field) count as current.
    if (!history) meta = meta.filter(m => m.current !== false);
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(meta));
    return;
  }

  // Delete an uploaded file
  if (req.url.startsWith('/api/uploads/delete') && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const { id } = JSON.parse(body);
        let meta = loadUploadsMeta();
        const entry = meta.find(m => m.id === id);
        if (!entry) { res.writeHead(404); res.end(JSON.stringify({ error: 'File not found' })); return; }
        // Delete physical file
        const filePath = path.join(UPLOADS_DIR, entry.stored_name);
        if (fs.existsSync(filePath)) fs.unlinkSync(filePath);
        // Remove metadata
        meta = meta.filter(m => m.id !== id);
        saveUploadsMeta(meta);

        // Log deletion
        if (entry.task_id) {
          supabaseRequest('POST', 'activities', {
            type: 'task_note',
            subject: `task:${entry.task_id}`,
            body: `Document deleted: ${entry.filename}`,
            owner: session ? session.name : 'System',
            status: 'completed',
          }).catch(() => {});
        }

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true }));
      } catch (e) { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // Serve uploaded files for download
  // In-browser preview for Office docs: convert (cached) to PDF and serve inline.
  // Falls back to serving the original file inline if conversion is unavailable.
  if (req.url.startsWith('/viewpdf/') && req.method === 'GET') {
    const fileName = decodeURIComponent(req.url.replace('/viewpdf/', '').split('?')[0]);
    const filePath = path.join(UPLOADS_DIR, fileName);
    if (!filePath.startsWith(UPLOADS_DIR) || fileName.includes('..') || fileName.startsWith('_')) {
      res.writeHead(403); res.end('Forbidden'); return;
    }
    if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
      res.writeHead(404); res.end('Not Found'); return;
    }
    const meta = loadUploadsMeta().find(m => m.stored_name === fileName);
    const origBase = (meta ? meta.filename : fileName).replace(/\.[^.]+$/, '');
    const pdfPath = ensurePdfRendition(fileName);
    if (pdfPath) {
      res.writeHead(200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': safeContentDisposition(origBase + '.pdf', 'inline'),
      });
      res.end(fs.readFileSync(pdfPath));
    } else {
      // Conversion not possible — serve original inline as a fallback.
      res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Disposition': safeContentDisposition(fileName, 'inline') });
      res.end(fs.readFileSync(filePath));
    }
    return;
  }

  if (req.url.startsWith('/uploads/') && req.method === 'GET') {
    const fileName = decodeURIComponent(req.url.replace('/uploads/', ''));
    const filePath = path.join(UPLOADS_DIR, fileName);
    // Prevent directory traversal
    if (!filePath.startsWith(UPLOADS_DIR) || fileName.includes('..')) {
      res.writeHead(403); res.end('Forbidden'); return;
    }
    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile() && !fileName.startsWith('_')) {
      const ext = path.extname(filePath).toLowerCase();
      const mimeTypes = {
        '.pdf': 'application/pdf', '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.doc': 'application/msword', '.xls': 'application/vnd.ms-excel', '.ppt': 'application/vnd.ms-powerpoint',
        '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.gif': 'image/gif', '.svg': 'image/svg+xml',
        '.csv': 'text/csv', '.txt': 'text/plain', '.zip': 'application/zip', '.md': 'text/markdown',
      };
      const meta = loadUploadsMeta().find(m => m.stored_name === fileName);
      let origName = meta ? meta.filename : fileName;
      // Some display filenames were stored WITHOUT an extension (e.g. "… Master Deck (DRAFT v1)"),
      // so the download saved with no file type and wouldn't open. Always carry the real extension.
      if (ext && !origName.toLowerCase().endsWith(ext)) origName = origName + ext;
      // Office docs / archives are not meaningfully "inline"-viewable — force a proper download so
      // the browser keeps the filename+extension instead of trying to render and dropping it.
      const inlineOk = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.txt', '.md', '.csv'].includes(ext);
      res.writeHead(200, {
        'Content-Type': mimeTypes[ext] || 'application/octet-stream',
        'Content-Disposition': safeContentDisposition(origName, inlineOk ? 'inline' : 'attachment'),
      });
      res.end(fs.readFileSync(filePath));
    } else {
      res.writeHead(404); res.end('Not Found');
    }
    return;
  }

  // E-Sign signing page: /sign?token=... serves sign.html
  if (req.method === 'GET' && (req.url === '/sign' || req.url.startsWith('/sign?'))) {
    try { res.writeHead(200, { 'Content-Type': 'text/html' }); res.end(fs.readFileSync(path.join(__dirname, 'sign.html'))); }
    catch (e) { res.writeHead(404); res.end('Signing page not found'); }
    return;
  }

  // ── DECISIONS INBOX API ──
  // ── Research & Intel feed ──
  // GET: merge generator-built research.json with live agent-ingested briefs.
  if (req.url.split('?')[0] === '/api/research' && req.method === 'GET') {
    const base = loadResearch();
    const ingested = loadResearchIngest();
    const seen = new Set();
    const merged = [];
    for (const b of [...ingested, ...(base.briefs || [])]) {
      const key = (b.id || b.title || '') + '|' + (b.date || '');
      if (seen.has(key)) continue;
      seen.add(key); merged.push(b);
    }
    merged.sort((a, b) => String(b.date || '').localeCompare(String(a.date || '')));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      generated_at: base.generated_at || null,
      generated_display: base.generated_display || '',
      count: merged.length,
      briefs: merged,
    }));
    return;
  }

  // Ingest a research brief (token-protected; used by the cloud research agents / cron).
  if (req.url === '/api/research/ingest' && req.method === 'POST') {
    if ((req.headers['x-exo-token'] || '') !== decisionsToken()) {
      res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'bad token' })); return;
    }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const incoming = Array.isArray(p) ? p : [p];
        const arr = loadResearchIngest();
        const now = new Date().toISOString();
        const out = [];
        for (const item of incoming) {
          const brief = {
            id: item.id || ('ingest-' + Date.now() + '-' + Math.random().toString(36).slice(2, 7)),
            title: item.title || 'Research brief',
            date: item.date || now.slice(0, 10),
            category: item.category || 'Research',
            source: item.source || 'Research Team',
            item_count: item.item_count || (Array.isArray(item.highlights) ? item.highlights.length : 0),
            highlights: Array.isArray(item.highlights) ? item.highlights.slice(0, 12) : [],
            body: (item.body || '').slice(0, 8000),
            ingested_at: now,
          };
          // De-dupe by id: replace if same id already ingested.
          const ix = arr.findIndex(b => b.id === brief.id);
          if (ix >= 0) arr[ix] = brief; else arr.unshift(brief);
          out.push(brief);
        }
        // Keep the ingest store bounded.
        saveResearchIngest(arr.slice(0, 500));
        res.writeHead(201, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true, ingested: out.length, briefs: out }));
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // Capability-Gap Ledger — the acquire/build/license/partner pipeline fed by the commercialization
  // engine. GET serves the ledger; token-protected POST lets the opportunity/quote engines log a gap
  // when a deal is lost/blocked for a missing capability (the recursive corp-dev loop).
  if (req.url.split('?')[0] === '/api/capability-gaps' && req.method === 'GET') {
    let d = { generated_at: null, gaps: [] };
    try { d = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'capability-gaps.json'))); } catch (e) {}
    const order = { high: 0, medium: 1, low: 2 };
    (d.gaps || []).sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3) || String(a.capability).localeCompare(String(b.capability)));
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ generated_at: d.generated_at || null, count: (d.gaps || []).length, gaps: d.gaps || [] }));
    return;
  }
  // Ranked corp-dev shortlist — which target/partner to move on first (third-party fit-scorer).
  if (req.url.split('?')[0] === '/api/gap-targets' && req.method === 'GET') {
    let d = { generated_at: null, targets: [], unmatched: [] };
    try { d = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'gap-targets.json'))); } catch (e) {}
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify(d));
    return;
  }
  // Update a gap's status/tag from the UI (auth'd session; admin/Jon).
  if (req.url === '/api/capability-gaps/update' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const fp = path.join(__dirname, 'data', 'capability-gaps.json');
        const d = JSON.parse(fs.readFileSync(fp));
        const g = (d.gaps || []).find(x => x.id === p.id);
        if (!g) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'not found' })); return; }
        if (p.status) g.status = p.status;
        if (p.tag) g.tag = p.tag;
        if (typeof p.note === 'string') g.note = p.note.slice(0, 1000);
        g.updated = new Date().toISOString();
        d.generated_at = g.updated;
        fs.writeFileSync(fp, JSON.stringify(d, null, 2));
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true, gap: g }));
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }
  // Token-protected ingest — the engines call this when a deal reveals a missing capability.
  if (req.url === '/api/capability-gaps/ingest' && req.method === 'POST') {
    if ((req.headers['x-exo-token'] || '') !== decisionsToken()) {
      res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'bad token' })); return;
    }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const cp = require('child_process');
        const args = ['scripts/capability_gap_ledger.py', 'add', '--capability', String(p.capability || '').slice(0, 120)];
        if (p.description) { args.push('--description', String(p.description).slice(0, 500)); }
        if (p.source) { args.push('--source', String(p.source).slice(0, 120)); }
        if (p.severity) { args.push('--severity', String(p.severity)); }
        if (p.tag) { args.push('--tag', String(p.tag)); }
        const r = cp.execFileSync('python3', args, { cwd: path.join(__dirname, '..'), encoding: 'utf8', timeout: 20000 });
        res.writeHead(201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true, result: r.trim() }));
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // Ingest a new decision (token-protected; used by Exo / cron agents). Public path, validates X-Exo-Token.
  if (req.url === '/api/decisions/ingest' && req.method === 'POST') {
    if ((req.headers['x-exo-token'] || '') !== decisionsToken()) {
      res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'bad token' })); return;
    }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const arr = loadDecisions();
        const now = new Date().toISOString();
        // De-dupe is GLOBAL on dedupeKey (any status), not just open. A stable dedupeKey identifies
        // one decision for its whole life. If it was already answered/closed, an agent re-raising the
        // same key must NOT spawn a fresh duplicate — that was the "same card multiple times a day"
        // bug (overnight resolver + morning digest each re-created the rollup after Jon answered it).
        const isOpenStatus = s => { s = (s || 'open'); return s === 'open' || s === 'pending'; };
        if (p.dedupeKey) {
          const already = arr.find(d => d.dedupeKey === p.dedupeKey && !isOpenStatus(d.status));
          if (already) {
            // Already resolved — respect the answer, do not duplicate.
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ ...already, deduped: true, reason: 'already answered — not re-raised' }));
            return;
          }
        }
        // Open decision with the same dedupeKey exists → update it in place instead of adding.
        let existing = p.dedupeKey ? arr.find(d => isOpenStatus(d.status) && d.dedupeKey === p.dedupeKey) : null;
        if (existing) {
          Object.assign(existing, {
            title: p.title || existing.title, question: p.question || existing.question,
            context: p.context ?? existing.context, proposedAction: p.proposedAction ?? existing.proposedAction,
            type: p.type || existing.type, options: p.options || existing.options,
            priority: p.priority || existing.priority, relatedItem: p.relatedItem ?? existing.relatedItem,
            source: p.source || existing.source, updated: now,
            agentClass: p.agentClass || existing.agentClass || '', correlationId: p.correlationId || existing.correlationId || '',
            approver: p.approver ?? existing.approver ?? '', assignedTo: p.assignedTo ?? existing.assignedTo ?? '',
          });
          saveDecisions(arr);
          res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(existing)); return;
        }
        const d = {
          id: nextDecisionId(arr), created: now, updated: now,
          source: p.source || 'Exo', relatedItem: p.relatedItem || '',
          title: p.title || 'Decision needed', question: p.question || '',
          context: p.context || '', proposedAction: p.proposedAction || '',
          type: p.type || 'yesno', options: p.options || ['Yes', 'No'],
          priority: p.priority || 'med', dedupeKey: p.dedupeKey || '',
          status: 'open', answer: null, note: '', answeredAt: null,
          agentClass: p.agentClass || '', correlationId: p.correlationId || '',
          approver: p.approver || '', assignedTo: p.assignedTo || '',
        };
        arr.push(d); saveDecisions(arr);
        // Event-driven delivery: a "deliver-to-Jon draft" decision is delivered NOW, not on the
        // polling watcher's timer — a draft Jon requested shouldn't wait for another job to sweep it.
        try {
          const _blob = `${d.proposedAction || ''} ${d.question || ''} ${d.context || ''}`;
          if (/deliver .{0,30}?(your|to your) inbox|for you to send|to your inbox to send|on\s+yes[, ].{0,40}?deliver|i deliver the draft/i.test(_blob)) {
            const { execFile } = require('child_process');
            execFile('/usr/bin/python3', [path.join(__dirname, '..', 'scripts', 'decision-send-watcher.py')],
              { timeout: 90000, env: { ...process.env, PATH: '/opt/homebrew/bin:' + (process.env.PATH || '/usr/bin:/bin') } }, () => {});
          }
        } catch {}
        res.writeHead(201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(d));
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // List decisions (session-gated for admin). ?status=open|answered|all (default open)
  if (req.url.startsWith('/api/decisions') && req.method === 'GET') {
    const urlObj = new URL(req.url, 'http://localhost');
    const status = urlObj.searchParams.get('status') || 'open';
    let arr = loadDecisions();
    // ── User scoping ── each person sees only decisions assigned to them (or where they are the
    // named approver). Legacy decisions have no assignee and belong to Jon (the original
    // "Needs Jon" queue), so they default to jquinn@exosaero.com — others no longer see them.
    // Admins can pass ?scope=all to see the whole board.
    const dsess = getSession(req);
    const me = ((dsess && dsess.email) || '').toLowerCase();
    const scopeAll = (urlObj.searchParams.get('scope') === 'all' && dsess && dsess.role === 'admin') || isDecisionsCronToken(req);
    if (!scopeAll) {
      arr = arr.filter(d => {
        const assignee = String(d.assignedTo || 'jquinn@exosaero.com').toLowerCase();
        const am = /([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})/i.exec(d.approver || '');
        const approverEmail = am ? am[1].toLowerCase() : '';
        return (me && assignee === me) || (approverEmail && approverEmail === me);
      });
    }
    // Normalize actionable-status synonyms: agent-written decisions sometimes use 'pending'
    // instead of the canonical 'open'; treat them as open so they can never hide from the board.
    const normStatus = s => { s = (s || 'open'); return s === 'pending' ? 'open' : s; };
    if (status !== 'all') arr = arr.filter(d => normStatus(d.status) === status);
    // Rank by composite score: opportunity value + deadline are the primary drivers.
    // Answered items keep recency order (most recently answered first); open items rank by score.
    if (status === 'answered') {
      arr.sort((a, b) => (b.answeredAt || '').localeCompare(a.answeredAt || ''));
    } else {
      const refIdx = loadDecisionRefIndex();
      for (const d of arr) d._score = decisionScore(d, refIdx);
      arr.sort((a, b) => (b._score - a._score) || (a.created || '').localeCompare(b.created || ''));
      for (const d of arr) delete d._score;
    }
    // Attach uploaded documents so a decision can be REVIEWED from the Decisions board.
    // Match docs linked directly to the decision OR to its related task (relatedItem like
    // "… (task 2467)") — most "approve this document" decisions carry the file on the task, not
    // the decision. Office docs get a /viewpdf review link (inline PDF render); others open raw.
    try {
      const upMeta = loadUploadsMeta();
      const OFFICE = new Set(['docx', 'pptx', 'xlsx', 'doc', 'ppt', 'xls']);
      for (const d of arr) {
        const tm = /task\s*#?\s*(\d+)/i.exec(d.relatedItem || '');
        const taskId = tm ? tm[1] : null;
        const linked = upMeta.filter(m =>
          String(m.decision_id) === String(d.id) ||
          (taskId && m.task_id != null && String(m.task_id) === String(taskId)));
        d.attachments = linked.map(m => {
          const ext = (String(m.stored_name).split('.').pop() || '').toLowerCase();
          const enc = encodeURIComponent(m.stored_name);
          return {
            id: m.id, filename: m.filename, ext,
            url: '/uploads/' + enc,
            review_url: OFFICE.has(ext) ? '/viewpdf/' + enc : '/uploads/' + enc,
            size: m.size, uploaded_at: m.uploaded_at,
          };
        });
        // An explicit review_url on the decision record wins as the primary reviewable.
        if (d.review_url && !d.attachments.some(a => a.review_url === d.review_url)) {
          d.attachments.unshift({ filename: d.review_label || 'Review document', review_url: d.review_url, url: d.review_url, ext: '' });
        }
      }
    } catch (e) { /* attachments are best-effort */ }
    res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(arr)); return;
  }

  // Create a decision from inside the dashboard (session-gated)
  if (req.url === '/api/decisions' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}'); const arr = loadDecisions(); const now = new Date().toISOString();
        const d = { id: nextDecisionId(arr), created: now, updated: now, source: p.source || 'Jon',
          relatedItem: p.relatedItem || '', title: p.title || 'Decision needed', question: p.question || '',
          context: p.context || '', proposedAction: p.proposedAction || '', type: p.type || 'yesno',
          options: p.options || ['Yes', 'No'], priority: p.priority || 'med', dedupeKey: p.dedupeKey || '',
          status: 'open', answer: null, note: '', answeredAt: null, approver: p.approver || '', assignedTo: p.assignedTo || '' };
        arr.push(d); saveDecisions(arr);
        res.writeHead(201, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(d));
      } catch (e) { res.writeHead(400); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // Answer one or many decisions at once (session-gated). Body: {answers:[{id,answer,note}]} or {id,answer,note}
  if (req.url === '/api/decisions/answer' && req.method === 'POST') {
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const items = Array.isArray(p.answers) ? p.answers : [p];
        const arr = loadDecisions(); const now = new Date().toISOString(); const updated = [];
        const who = (session && session.name) || (isDecisionsCronToken(req) ? 'Decisions Daily Update' : 'Jon');
        for (const it of items) {
          const d = arr.find(x => x.id === it.id);
          if (!d) continue;
          if (it.answer === undefined && !it.note) continue;
          d.answer = it.answer ?? d.answer; d.note = it.note || ''; d.status = 'answered';
          d.answeredAt = now; d.answeredBy = who; d.updated = now;
          updated.push(d.id);
        }
        saveDecisions(arr);
        // Fire rendered notifications async (non-blocking) for each answered decision.
        // Notifies the internal person waiting (owner field → @exosaero.com email) via
        // Discord DM + email. Never blocks the HTTP response.
        if (updated.length) {
          const { spawn } = require('child_process');
          const NOTIFY = path.join(__dirname, '..', 'scripts', 'decision-rendered-notify.py');
          const answererName = (session && session.name) || who;
          for (const id of updated) {
            const d = arr.find(x => x.id === id);
            if (!d) continue;
            const args = ['--id', id, '--answer', d.answer || '', '--note', d.note || '', '--by', answererName];
            try {
              const env = Object.assign({}, process.env, {
                PATH: ['/Users/exomac/.local/share/mise/shims', '/opt/homebrew/bin', '/usr/local/bin', process.env.PATH || ''].join(':')
              });
              spawn('python3', [NOTIFY, ...args], { detached: true, stdio: 'ignore', env }).unref();
            } catch (e) { /* notify is best-effort; never fail the answer */ }
          }
        }
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ updated })); return;
      } catch (e) { res.writeHead(400); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // Attach a note to a decision WITHOUT answering it — the note is saved on the still-open
  // decision so the person can then Approve/Deny with the note riding along. This exists because
  // saving a note must NOT resolve the card (that surprised Phil + Steve: "Save Note" made the
  // box vanish before they could approve). Body: { id, note }. Session-gated.
  if (req.url === '/api/decisions/note' && req.method === 'POST') {
    const nsess = getSession(req);
    if (!nsess) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const arr = loadDecisions();
        const d = arr.find(x => String(x.id) === String(p.id));
        if (!d) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'decision not found' })); return; }
        d.note = (p.note || '').toString();        // attach the note; do NOT change status
        d.updated = new Date().toISOString();
        saveDecisions(arr);
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true, id: d.id, note: d.note })); return;
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // "Not mine" — reassign a misrouted decision to the correct owner, or flag it for Exo to reroute.
  // Body: { id, to?  (name or email), reason? }. Session-gated.
  if (req.url === '/api/decisions/reassign' && req.method === 'POST') {
    const rsess = getSession(req);
    if (!rsess) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const arr = loadDecisions();
        const d = arr.find(x => String(x.id) === String(p.id));
        if (!d) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'decision not found' })); return; }
        const who = (rsess.name || rsess.email || 'someone');
        const now = new Date().toISOString();
        // Resolve the target owner's email.
        let email = '', label = '';
        const to = (p.to || '').trim();
        if (/@/.test(to)) { email = to.toLowerCase(); label = to; }
        else if (to) {
          try {
            const { openErp } = require('../erp-foundation/dal');
            const erp = openErp(path.join(__dirname, '..', 'erp-foundation', 'mc.db'), { actor: rsess.email || 'mc', agent: 'decision-reassign' });
            const emps = erp.getEmployees(); erp.close();
            const hit = emps.find(e => (e.full_name || '').toLowerCase() === to.toLowerCase())
              || emps.find(e => (e.full_name || '').toLowerCase().includes(to.toLowerCase()));
            if (hit && hit.work_email) { email = hit.work_email.toLowerCase(); label = hit.full_name; }
          } catch (e) {}
        }
        const from = String(d.assignedTo || 'jquinn@exosaero.com');
        const note = `Reassigned by ${who} (not mine)${p.reason ? ': ' + p.reason : ''}`;
        d.note = (d.note ? d.note + ' | ' : '') + note;
        d.reassignedFrom = from; d.updated = now;
        // The "my decisions" filter matches on assignee OR the named approver. If the person
        // reassigning is the stale approver, leaving that field would keep the card glued to their
        // board even after handoff (this is why Phil kept seeing cards he'd reassigned). Clear/repoint
        // the approver whenever it points at the reassigner (or is empty) so handoff actually sticks.
        const reassignerEmail = ((rsess.email) || '').toLowerCase();
        const curApM = /([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})/i.exec(d.approver || '');
        const curApproverEmail = curApM ? curApM[1].toLowerCase() : '';
        const approverIsReassigner = !d.approver || (curApproverEmail && curApproverEmail === reassignerEmail);
        if (email) {
          d.assignedTo = email; d.status = d.status === 'answered' ? d.status : 'open';
          if (approverIsReassigner) d.approver = email;   // new owner is now the approver of record
          d.needsExoRouting = false;
          saveDecisions(arr);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true, reassignedTo: label || email }));
        } else {
          // Couldn't determine the owner — take it out of the sender's inbox and flag it for Exo.
          d.assignedTo = 'exo@exosaero.com'; d.status = 'reassigning'; d.needsExoRouting = true;
          if (approverIsReassigner) d.approver = '';       // don't let it linger on the reassigner's board
          saveDecisions(arr);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ ok: true, queued: true, message: "Flagged for Exo to reroute — it's out of your inbox." }));
        }
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // Update an opportunity from the detail/edit panel (session-gated). Persists to
  // opportunity-overrides.json (survives the markdown->json regeneration) AND patches the live
  // opportunities.json so the edit reflects immediately without waiting for the generator.
  if (req.url === '/api/opportunities/update' && req.method === 'POST') {
    const session = getSession(req);
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const id = (p.id || '').toString();
        if (!id) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'missing id' })); return; }
        const ALLOWED = ['status', 'value', 'due', 'next_action', 'priority', 'type', 'description', 'title', 'closed', 'closed_reason', 'closed_at'];
        const fields = {};
        for (const k of ALLOWED) {
          if (p.fields && p.fields[k] !== undefined) fields[k] = (k === 'priority') ? Number(p.fields[k]) || 0 : p.fields[k];
        }
        // Optional: closing as Failed DD also flags the party in the shared Failed-DD blocklist
        // so any future inbound from them is recognized as a known do-not-engage across Exos.
        if (p.failed_dd && p.failed_dd_firm) {
          try {
            const args = ['scripts/failed_dd.py', 'add', '--firm', String(p.failed_dd_firm),
              '--reason', String(p.failed_dd_reason || 'Failed DD (closed from Mission Control)'),
              '--source', 'mc-opportunity-close'];
            for (const e of (Array.isArray(p.failed_dd_emails) ? p.failed_dd_emails : [])) { if (e) args.push('--email', String(e)); }
            for (const d of (Array.isArray(p.failed_dd_domains) ? p.failed_dd_domains : [])) { if (d) args.push('--domain', String(d)); }
            execFileSync('python3', args, { cwd: path.join(__dirname, '..'), timeout: 20000 });
          } catch (e) { /* registry add best-effort; the close still proceeds */ }
        }
        if (!Object.keys(fields).length) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'no fields' })); return; }
        // 1) merge into the overrides file
        const ovPath = path.join(__dirname, 'data', 'opportunity-overrides.json');
        let ov = {}; try { ov = JSON.parse(fs.readFileSync(ovPath, 'utf-8')); } catch {}
        ov[id] = Object.assign({}, ov[id] || {}, fields, { _updated: new Date().toISOString(), _by: (session.email || '') });
        fs.mkdirSync(path.dirname(ovPath), { recursive: true });
        fs.writeFileSync(ovPath, JSON.stringify(ov, null, 2));
        // 2) patch live opportunities.json for instant reflect
        try {
          const oppPath = path.join(__dirname, 'data', 'opportunities.json');
          const oj = JSON.parse(fs.readFileSync(oppPath, 'utf-8'));
          const arr = Array.isArray(oj) ? oj : (oj.opportunities || []);
          const it = arr.find(o => o.id === id);
          if (it) { Object.assign(it, fields); fs.writeFileSync(oppPath, JSON.stringify(oj, null, 2)); }
        } catch {}
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true, id, fields }));
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // Update a Series A CRM firm from the detail/edit panel (session-gated). Persists to
  // crm-overrides.json (keyed by firm, survives regeneration) AND patches live crm.json.
  if (req.url === '/api/crm/update' && req.method === 'POST') {
    const session = getSession(req);
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const firm = (p.firm || '').toString();
        if (!firm) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'missing firm' })); return; }
        const ALLOWED = ['stage', 'next_action', 'last_touched', 'notes', 'tier'];
        const fields = {};
        for (const k of ALLOWED) { if (p.fields && p.fields[k] !== undefined) fields[k] = p.fields[k]; }
        if (!Object.keys(fields).length) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'no fields' })); return; }
        const ovPath = path.join(__dirname, 'data', 'crm-overrides.json');
        let ov = {}; try { ov = JSON.parse(fs.readFileSync(ovPath, 'utf-8')); } catch {}
        ov[firm] = Object.assign({}, ov[firm] || {}, fields, { _updated: new Date().toISOString(), _by: (session.email || '') });
        fs.mkdirSync(path.dirname(ovPath), { recursive: true });
        fs.writeFileSync(ovPath, JSON.stringify(ov, null, 2));
        try {
          const crmPath = path.join(__dirname, 'data', 'crm.json');
          const cj = JSON.parse(fs.readFileSync(crmPath, 'utf-8'));
          const arr = cj.contacts || [];
          const it = arr.find(c => c.firm === firm);
          if (it) { Object.assign(it, fields); fs.writeFileSync(crmPath, JSON.stringify(cj, null, 2)); }
        } catch {}
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ ok: true, firm, fields }));
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    }); return;
  }

  // In-MC chat with Exobot (session-gated). Runs a synchronous agent turn via the OpenClaw
  // gateway, in a per-user chat session (agent:main:mcchat-<email>), and returns the reply.
  // Each logged-in user gets their own persistent Exobot thread — no email round-trip.
  if (req.url === '/api/chat' && req.method === 'POST') {
    const session = getSession(req);
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    let body = ''; req.on('data', c => { body += c; if (body.length > 30 * 1024 * 1024) req.destroy(); }); req.on('end', () => {
      let payload = {};
      try { payload = JSON.parse(body || '{}'); } catch {}
      let msg = (payload.message || '').toString().trim();
      if (msg.length > 8000) msg = msg.slice(0, 8000);
      // Pasted / attached documents (base64). Saved to disk so the agent (full file tools)
      // can read them; the paths are handed to the agent in the prompt.
      const atts = Array.isArray(payload.attachments) ? payload.attachments.slice(0, 10) : [];
      if (!msg && !atts.length) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'empty message' })); return; }
      // Async + parallel: create a background job, return its id immediately. The widget
      // polls /api/chat/result, so the answer survives navigation; and a question fired
      // while another is still running forks into its own lane so both run at once.
      chatJobsGC();
      const email = session.email || 'user';
      if (chatPendingCount(email) >= CHAT_MAX_PARALLEL) {
        res.writeHead(429, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: `You already have ${CHAT_MAX_PARALLEL} questions running — let one finish before adding another.` }));
        return;
      }
      const jobId = crypto.randomBytes(12).toString('hex');
      let attNote = '';
      if (atts.length) {
        try {
          const dir = path.join(UPLOADS_DIR, 'chat', jobId);
          fs.mkdirSync(dir, { recursive: true });
          const saved = [];
          for (const a of atts) {
            const safe = (String(a.name || 'document').replace(/[^\w.\-]/g, '_').slice(0, 120)) || 'document';
            const b64 = String(a.data || '').split(',').pop();
            if (!b64) continue;
            const buf = Buffer.from(b64, 'base64');
            if (!buf.length || buf.length > 25 * 1024 * 1024) continue;
            const fp = path.join(dir, safe);
            fs.writeFileSync(fp, buf);
            saved.push(fp);
          }
          if (saved.length) attNote = '\n\n[The user attached ' + (saved.length > 1 ? saved.length + ' documents' : 'a document')
            + ' via the Ask Exobot chat — read the file' + (saved.length > 1 ? 's' : '') + ' at '
            + (saved.length > 1 ? 'these paths' : 'this path') + ' for full content:]\n' + saved.map(p => '- ' + p).join('\n');
        } catch (e) { /* if save fails, proceed with text only */ }
      }
      const fullMsg = (msg || '(see attached document)') + attNote;
      const lane = chatAssignSession(email, jobId);
      chatJobs.set(jobId, { email, skey: lane.skey, isMain: lane.isMain, status: 'pending', reply: '', ts: Date.now() });
      runExobotChat(jobId, fullMsg);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ jobId }));
    });
    return;
  }

  // Async chat result poll — returns the reply once the background job finishes.
  if (req.url.split('?')[0] === '/api/chat/result' && req.method === 'GET') {
    const session = getSession(req);
    if (!session) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    const id = new URL(req.url, 'http://localhost').searchParams.get('id') || '';
    const job = chatJobs.get(id);
    if (!job || job.email !== (session.email || 'user')) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ status: 'unknown' })); return; }
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: job.status, reply: job.reply }));
    // leave the job in place (GC clears it after 20 min) so multiple tabs all get the reply
    return;
  }

  // Submittal deadlines: parsed + sorted deadlines for all live submittal opportunities.
  if (req.url.startsWith('/api/submittals') && req.method === 'GET') {
    try {
      const raw = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'opportunities.json'), 'utf-8'));
      const arr = Array.isArray(raw) ? raw : (raw.opportunities || []);
      const DEAD = /closed|dead|dropped|scam|declined|\bpass\b|do not enga|investment pass|listing drop/i;
      const now = new Date(); const todayUTC = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
      const out = [];
      for (const o of arr) {
        const status = (o.status || '').toString();
        if (DEAD.test(status)) continue;
        const dl = parseSubmittalDeadline(o.due, todayUTC);
        const daysLeft = dl.iso ? Math.round((Date.UTC(+dl.iso.slice(0,4), +dl.iso.slice(5,7)-1, +dl.iso.slice(8,10)) - todayUTC) / 86400000) : null;
        // Drop confirmed-missed deadlines: a parsed date already in the past is not worth showing.
        if (daysLeft != null && daysLeft < 0) continue;
        out.push({ id: o.id, title: o.title || '(untitled)', status, type: o.type || '',
          due_raw: o.due || '', deadline: dl.iso, deadline_label: dl.label, bucket: dl.bucket,
          days_left: daysLeft, next_action: o.next_action || '' });
      }
      const rank = { dated: 0, rolling: 1, tbd: 2 };
      out.sort((a, b) => (rank[a.bucket] - rank[b.bucket]) || ((a.deadline || '9999').localeCompare(b.deadline || '9999')));
      res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(out)); return;
    } catch (e) { res.writeHead(500, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); return; }
  }

  // Email activity tracked by mc-email-tracker (read-only side store). ?item=<id> filters.
  if (req.url.startsWith('/api/email-activity') && req.method === 'GET') {
    try {
      const all = JSON.parse(fs.readFileSync(path.join(__dirname, 'data', 'email-activity.json'), 'utf-8'));
      const urlObj = new URL(req.url, 'http://localhost');
      const item = urlObj.searchParams.get('item');
      const out = item ? all.filter(r => (r.matched_items || [r.matched_item]).includes(item)) : all;
      res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(out)); return;
    } catch (e) { res.writeHead(200, { 'Content-Type': 'application/json' }); res.end('[]'); return; }
  }

  // Task ledger: recorded task events + live launchd job health (Jobs panel).
  if (req.url.startsWith('/api/task-ledger') && req.method === 'GET') {
    const out = { events: [], jobs: [] };
    try {
      const raw = fs.readFileSync('/Users/exomac/.openclaw/workspace/logs/task-ledger.jsonl', 'utf-8').trim().split('\n');
      out.events = raw.filter(Boolean).map(l => { try { return JSON.parse(l); } catch { return null; } })
        .filter(Boolean).slice(-200).reverse();
    } catch (e) {}
    // Job health comes from a user-domain snapshot file (the server is a daemon and
    // cannot see user LaunchAgents via its own launchctl domain).
    try {
      const snap = JSON.parse(fs.readFileSync('/Users/exomac/.openclaw/workspace/logs/launchd-snapshot.json', 'utf-8'));
      out.jobs = snap.jobs || [];
      out.jobs_generated = snap.generated || null;
    } catch (e) {}
    res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(out)); return;
  }

  // ── DOSSIERS: edit a relationship dossier / mark Failed Due Diligence ──
  if (req.url === '/api/dossiers' && req.method === 'PATCH') {
    const sess = getSession(req);
    if (!sess) { res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not logged in' })); return; }
    if (sess.role === 'early_adopter') { res.writeHead(403, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Not permitted' })); return; }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body);
        const store = loadDossiersFile();
        const arr = store.dossiers || (store.dossiers = []);
        const idx = arr.findIndex(x => x.id === p.id);
        if (idx === -1) { res.writeHead(404, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'Dossier not found' })); return; }
        const editable = ['name', 'headline', 'stage', 'stage_color', 'status', 'next_step', 'last_touch', 'contacts', 'deals', 'agreements', 'flags'];
        for (const k of editable) if (k in p) arr[idx][k] = p[k];
        if ('dd_status' in p) {
          const failed = p.dd_status === 'failed';
          arr[idx].dd_status = failed ? 'failed' : '';
          arr[idx].dd_status_by = failed ? (sess.name || sess.email) : '';
          arr[idx].dd_status_at = failed ? new Date().toISOString() : '';
        }
        arr[idx].updated_at = new Date().toISOString();
        arr[idx].updated_by = sess.name || sess.email;
        saveDossiersFile(store);
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(arr[idx]));
      } catch (e) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: e.message })); }
    });
    return;
  }

  if (req.method === 'GET') {
    // Strip the query string before building the file path — otherwise a deep link like
    // /opportunities.html?focus=OPP-032 is treated as a literal filename and 404s.
    const pathname = decodeURIComponent(req.url.split('?')[0]);
    let filePath = path.join(__dirname, pathname === '/' ? 'index.html' : pathname);
    if (!filePath.startsWith(__dirname)) { res.writeHead(403); res.end('Forbidden'); return; }
    const extMap = { '.html': 'text/html', '.js': 'application/javascript', '.css': 'text/css', '.json': 'application/json' };
    if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
      const ext = path.extname(filePath);
      // Auto-inject the global Exobot chat widget into every real MC page (except the
      // public/sandbox pages) so the conversation persists across navigation.
      const NO_WIDGET = ['login.html', 'set-password.html', 'sign.html', 'docusign.html', 'welcome.html', 'exobot-widget.js'];
      const base = path.basename(filePath);
      // App pages + scripts must never be served stale: a code deploy has to take effect on the
      // next load, not after a manual hard-refresh. (This is what left Phil on the old "Save Note"
      // behavior after it was already fixed.) Data/static assets can still be revalidated normally.
      const noStore = (ext === '.html' || ext === '.js');
      if (ext === '.html' && !NO_WIDGET.includes(base)) {
        let html = fs.readFileSync(filePath, 'utf-8');
        if (html.indexOf('/exobot-widget.js') === -1) {
          const tag = '<script src="/exobot-widget.js" defer></script>';
          html = html.indexOf('</body>') !== -1 ? html.replace('</body>', tag + '\n</body>') : html + tag;
        }
        res.writeHead(200, { 'Content-Type': 'text/html', 'Cache-Control': 'no-store, must-revalidate' });
        res.end(html);
      } else {
        const headers = { 'Content-Type': extMap[ext] || 'text/plain' };
        if (noStore) headers['Cache-Control'] = 'no-store, must-revalidate';
        res.writeHead(200, headers);
        res.end(fs.readFileSync(filePath));
      }
    } else {
      res.writeHead(404);
      res.end('Not Found');
    }
    return;
  }
});

// ── Authoritative port ownership (durable fix, 2026-08-13) ──
// The launchd-managed service (com.exos.missioncontrol) is the ONE true instance. If a
// hand-started server is squatting PORT, the old code crashed on EADDRINUSE and — under
// launchd KeepAlive — crash-looped SILENTLY while the stale process kept serving old code
// (root cause of Neil's "My Tasks blank" glitch: it squatted the port for ~1.7 days).
// Now: on EADDRINUSE we identify the squatter and reclaim the port instead of dying, so a
// manual instance can never block the managed service for more than a few seconds.
function _pidsOnPort(port) {
  try {
    const out = execSync(`lsof -nP -iTCP:${port} -sTCP:LISTEN -t`, { encoding: 'utf8' }).trim();
    return out ? out.split('\n').map(s => parseInt(s, 10)).filter(Boolean) : [];
  } catch { return []; }  // lsof exits non-zero when nothing is listening
}
function _cmdOfPid(pid) {
  try { return execSync(`ps -o command= -p ${pid}`, { encoding: 'utf8' }).trim(); }
  catch { return ''; }
}
// Match on the last two path segments ("mission-control/server.js") rather than the full
// home-dir absolute path: macOS `ps -o command=` can truncate long paths, which would make
// a legit launchd peer look "hand-started" and get killed. This short tail survives
// truncation, still identifies any proper invocation as a peer, and a stale relative
// `node server.js` (the real squatter case) does NOT contain it — so it's still reclaimed.
const _SELF = __filename.split('/').slice(-2).join('/');  // "mission-control/server.js"
const _ts = () => new Date().toISOString();
let _reclaimAttempts = 0;
function startListen() {
  server.listen(PORT, '0.0.0.0', () => {
    console.log(`[${_ts()}] Mission Control server running on port ${PORT} (pid ${process.pid})`);
  });
}
server.on('error', (err) => {
  if (err && err.code === 'EADDRINUSE') {
    const mypid = process.pid;
    const holders = _pidsOnPort(PORT).filter(p => p !== mypid);
    // CRITICAL: never kill another instance already running THIS same server.js — that
    // creates a mutual-kill flap under launchd KeepAlive. If a peer already serves the
    // port, stand down cleanly (exit 0 → KeepAlive:{SuccessfulExit:false} won't respawn us).
    const peer = holders.find(p => _cmdOfPid(p).includes(_SELF));
    if (peer) {
      console.error(`[${_ts()}] PORT ${PORT} already served by a peer server.js (pid ${peer}); standing down (pid ${mypid} exits 0, no mutual-kill).`);
      process.exit(0);
    }
    // Otherwise the holder is a HAND-STARTED squatter (e.g. a relative `node server.js`).
    // The launchd-managed service is authoritative — reclaim the port from it.
    _reclaimAttempts++;
    if (_reclaimAttempts <= 5 && holders.length) {
      console.error(`[${_ts()}] PORT ${PORT} squatted by hand-started pid(s) [${holders.join(',')}]. Reclaiming (attempt ${_reclaimAttempts}/5).`);
      for (const p of holders) { try { process.kill(p, 'SIGTERM'); } catch {} }
      setTimeout(() => {
        for (const p of _pidsOnPort(PORT).filter(p => p !== mypid)) { try { process.kill(p, 'SIGKILL'); } catch {} }
        setTimeout(startListen, 500);
      }, 1500);
    } else {
      console.error(`[${_ts()}] Could not reclaim port ${PORT} after ${_reclaimAttempts} attempts — exiting so launchd restarts cleanly.`);
      process.exit(1);
    }
  } else {
    console.error(`[${_ts()}] Fatal server error:`, err);
    process.exit(1);
  }
});

// Resilience guard: a throw inside a single request handler (e.g. a bad header value from one
// document's filename) must NOT crash the whole server for everyone and trigger a launchd
// crash-loop. Log it loudly and stay up; the one offending request fails, the service survives.
process.on('uncaughtException', (err) => {
  console.error(`[${_ts()}] uncaughtException (server stays up):`, err && err.stack || err);
});
process.on('unhandledRejection', (reason) => {
  console.error(`[${_ts()}] unhandledRejection (server stays up):`, reason);
});

startListen();