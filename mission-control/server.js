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
function saveDecisions(arr) { fs.mkdirSync(path.dirname(DECISIONS_FILE), { recursive: true }); fs.writeFileSync(DECISIONS_FILE, JSON.stringify(arr, null, 2)); }

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
const OPENCLAW_BIN = '/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw';
const PDF_CONVERTIBLE = ['.docx', '.doc'];
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
    execFileSync('textutil', ['-convert', 'html', '-output', tmpHtml, src], { timeout: 30000, stdio: 'ignore' });
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

function supabaseRequest(method, pathAndQuery, body) {
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
        try { resolve({ status: res.statusCode, data: data ? JSON.parse(data) : null }); }
        catch { resolve({ status: res.statusCode, data }); }
      });
    });
    req.on('error', reject);
    if (body) req.write(JSON.stringify(body));
    req.end();
  });
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
const DS_PASSCODE = process.env.MC_DOCUSIGN_PASSCODE || 'exos2014';
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

  // ── AUTH GATE: protect all pages and APIs except login ──
  const publicPaths = ['/api/login', '/login', '/login.html', '/api/inbound-email', '/brand-assets/', '/sign', '/sign.html', '/api/esign/get', '/api/esign/sign', '/api/decisions/ingest', '/api/research/ingest'];
  const isPublic = publicPaths.some(p => req.url.startsWith(p));
  const fullSession = getSession(req);
  const dsSession = getDsSession(req);
  if (!fullSession) {
    if (dsSession) {
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
    const blockedForMember = ['/api/deals', '/api/templates', '/api/admin', '/api/dashboard', '/api/exosops'];
    if (blockedForMember.some(p => req.url.startsWith(p))) {
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Forbidden — upgrade your role to access this' }));
      return;
    }
  }

  // early_adopter role: strict sandbox — tasks board only, no CRM/deals/admin/docusign
  if (session && session.role === 'early_adopter') {
    const allowedAPIs = ['/api/tasks', '/api/uploads', '/api/me', '/api/logout'];
    const isAllowedAPI = allowedAPIs.some(p => req.url.startsWith(p));
    if (req.url.startsWith('/api/') && !isAllowedAPI) {
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'This feature is not available in the early adopter preview.' }));
      return;
    }
    // Block task deletion and task capture for early adopters
    if (req.url.startsWith('/api/tasks/delete') || req.url.startsWith('/api/tasks/capture')) {
      res.writeHead(403, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Not available in the early adopter preview.' }));
      return;
    }
    // Block internal pages — only allow tasks board and welcome
    const allowedPages = ['/', '/index.html', '/welcome', '/welcome.html', '/login', '/login.html'];
    const isAllowedPage = allowedPages.some(p => req.url === p || req.url.startsWith(p + '?'));
    if (req.method === 'GET' && !req.url.startsWith('/api/') && !isAllowedPage && !req.url.startsWith('/brand-assets') && !req.url.startsWith('/uploads/') && !req.url.startsWith('/viewpdf/')) {
      res.writeHead(302, { 'Location': '/' });
      res.end();
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
    res.writeHead(200, { 'Content-Type': ct, 'Content-Disposition': 'inline; filename="' + path.basename(full).replace(/"/g, '') + '"' });
    fs.createReadStream(full).pipe(res); return;
  }

  // ── TASKS API (Supabase-backed) ──
  if (req.url === '/api/tasks' && req.method === 'GET') {
    supabaseRequest('GET', 'tasks?order=priority.desc.nullslast,due_date.asc.nullslast&limit=5000')
      .then(({ status, data }) => {
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
      }).catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
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

        // Fetch current task to diff changes
        const current = await supabaseRequest('GET', `tasks?id=eq.${id}&limit=1`);
        const oldTask = Array.isArray(current.data) && current.data[0] ? current.data[0] : {};

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
  if (req.url === '/api/crm' && req.method === 'GET') {
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
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data.map(toFrontend)));
      })
      .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
    return;
  }

  if (req.url === '/api/crm' && req.method === 'PATCH') {
    let body = '';
    req.on('data', chunk => body += chunk.toString());
    req.on('end', () => {
      const update = JSON.parse(body);
      const sbFields = toSupabase(update.fields);
      // Try matching by crm_id first, fall back to uuid
      const filter = update.id.startsWith('EXOS-')
        ? `contacts?crm_id=eq.${encodeURIComponent(update.id)}`
        : `contacts?id=eq.${encodeURIComponent(update.id)}`;
      supabaseRequest('PATCH', filter, sbFields)
        .then(({ status, data }) => {
          if (status >= 400) { res.writeHead(status); res.end(JSON.stringify(data)); return; }
          const row = Array.isArray(data) && data[0] ? toFrontend(data[0]) : {};
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(row));
        })
        .catch(e => { res.writeHead(500); res.end(JSON.stringify({ error: e.message })); });
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
    supabaseRequest('GET', 'companies?order=name.asc&limit=5000')
      .then(({ status, data }) => {
        res.writeHead(status >= 400 ? status : 200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(data));
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

  // ── DEALS API ──
  if (req.url === '/api/deals' && req.method === 'GET') {
    supabaseRequest('GET', 'deals?order=created_at.desc&limit=5000')
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
      supabaseRequest('GET', `tasks?project_id=eq.${projId}&order=position.asc&limit=5000`),
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
      supabaseRequest('GET', 'tasks?select=id,state,project_id,priority,due_date&limit=5000'),
      supabaseRequest('GET', 'milestones?select=id,status,due_date&limit=500'),
      supabaseRequest('GET', 'time_entries?select=id,hours,date&limit=5000'),
      supabaseRequest('GET', 'users?select=id,name&limit=100'),
      supabaseRequest('GET', 'contacts?select=id&limit=1'),
      supabaseRequest('GET', 'deals?select=id,stage,amount&limit=5000'),
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
      supabaseRequest('GET', 'deals?select=id,stage,amount&limit=5000'),
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
        const existing = await supabaseRequest('GET', 'tasks?source=like.teamwork-*&limit=5000');
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
        const env = {
          id: esignToken().slice(0,12), title: title || 'Document', html: html || '',
          message: message || '', subject: subject || ('Signature requested: ' + (title||'Document')),
          createdAt: new Date().toISOString(), status: 'pending',
          signers: valid.map(s => ({ name: s.name||'Signer', email: s.email, role: s.role||'', token: esignToken(), signed:false, signedAt:null, ip:null, signatureType:null, signatureData:null }))
        };
        const all = loadEnvelopes(); all.push(env); saveEnvelopes(all);
        const t = esignTransport();
        const links = [];
        for (const s of env.signers) {
          const link = base + '/sign?token=' + s.token;
          links.push({ email: s.email, name: s.name, link });
          try { await t.sendMail({ from: '"John Quinn — Exos Aerospace" <jquinnexo@pm.me>', replyTo: 'jquinn@exosaero.com', to: s.email, subject: env.subject, html: esignRequestEmail(s, link, env) }); }
          catch (e) { console.error('[E-Sign] link email error to', s.email, e.message); }
        }
        console.log('[E-Sign] Envelope ' + env.id + ' created, ' + links.length + ' signing links sent');
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
    res.writeHead(200,{'Content-Type':'application/json'});
    res.end(JSON.stringify({
      title: env.title, html: env.html, message: env.message, status: env.status,
      signer: { name: signer.name, email: signer.email, role: signer.role, signed: signer.signed, signedAt: signer.signedAt },
      signers: env.signers.map(s => ({ name: s.name, role: s.role, signed: s.signed, signedAt: s.signedAt }))
    }));
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
        'Content-Disposition': `inline; filename="${origBase}.pdf"`,
      });
      res.end(fs.readFileSync(pdfPath));
    } else {
      // Conversion not possible — serve original inline as a fallback.
      res.writeHead(200, { 'Content-Type': 'application/octet-stream', 'Content-Disposition': `inline; filename="${fileName}"` });
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
      const origName = meta ? meta.filename : fileName;
      res.writeHead(200, {
        'Content-Type': mimeTypes[ext] || 'application/octet-stream',
        'Content-Disposition': `inline; filename="${origName}"`,
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

  // Ingest a new decision (token-protected; used by Exo / cron agents). Public path, validates X-Exo-Token.
  if (req.url === '/api/decisions/ingest' && req.method === 'POST') {
    if ((req.headers['x-exo-token'] || '') !== decisionsToken()) {
      res.writeHead(401, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'bad token' })); return;
    }
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      try {
        const p = JSON.parse(body || '{}');
        const arr = loadDecisions();
        // De-dupe: if an open decision with the same dedupeKey exists, update it instead of adding.
        let existing = p.dedupeKey ? arr.find(d => d.status === 'open' && d.dedupeKey === p.dedupeKey) : null;
        const now = new Date().toISOString();
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
    const scopeAll = urlObj.searchParams.get('scope') === 'all' && dsess && dsess.role === 'admin';
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
    // Attach uploaded documents linked to each decision (reuse uploads store).
    try {
      const upMeta = loadUploadsMeta();
      for (const d of arr) {
        d.attachments = upMeta
          .filter(m => String(m.decision_id) === String(d.id))
          .map(m => ({ id: m.id, filename: m.filename, url: '/uploads/' + encodeURIComponent(m.stored_name), size: m.size, uploaded_at: m.uploaded_at }));
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
        const who = (session && session.name) || 'Jon';
        for (const it of items) {
          const d = arr.find(x => x.id === it.id);
          if (!d) continue;
          if (it.answer === undefined && !it.note) continue;
          d.answer = it.answer ?? d.answer; d.note = it.note || ''; d.status = 'answered';
          d.answeredAt = now; d.answeredBy = who; d.updated = now;
          updated.push(d.id);
        }
        saveDecisions(arr);
        res.writeHead(200, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ updated })); return;
      } catch (e) { res.writeHead(400); res.end(JSON.stringify({ error: e.message })); }
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
    let body = ''; req.on('data', c => body += c); req.on('end', () => {
      let msg = '';
      try { msg = (JSON.parse(body || '{}').message || '').toString().trim(); } catch {}
      if (!msg) { res.writeHead(400, { 'Content-Type': 'application/json' }); res.end(JSON.stringify({ error: 'empty message' })); return; }
      if (msg.length > 4000) msg = msg.slice(0, 4000);
      const slug = (session.email || 'anon').replace(/[^a-z0-9]+/gi, '-').toLowerCase();
      const skey = 'agent:main:mcchat-' + slug;
      // Tag the message with who's asking so Exobot has the user context.
      const tagged = `[Mission Control chat · ${session.email || 'user'}] ${msg}`;
      const { execFile } = require('child_process');
      // openclaw is a `#!/usr/bin/env node` script and REQUIRES a compliant node (>=22.22.3 <23
      // or >=24.15). The server itself runs on node 24.14.0 (too old for openclaw), so prepend a
      // compliant node (homebrew v22.23.2) to PATH or the agent call fails silently (no JSON).
      const NODE_BIN = '/opt/homebrew/bin';
      const childEnv = { ...process.env, PATH: NODE_BIN + ':' + (process.env.PATH || '/usr/bin:/bin') };
      execFile(OPENCLAW_BIN, ['agent', '--session-key', skey, '-m', tagged, '--json', '--timeout', '150'],
        { timeout: 165000, maxBuffer: 16 * 1024 * 1024, env: childEnv }, (err, stdout) => {
          let reply = '';
          try {
            const j = JSON.parse(stdout);
            reply = (j.result && Array.isArray(j.result.payloads) ? j.result.payloads.map(p => p && p.text).filter(Boolean).join('\n') : '')
              || (j.result && j.result.meta && j.result.meta.finalAssistantVisibleText) || '';
          } catch {}
          if (!reply) reply = err ? 'Exobot timed out or errored on that one — try again or use the email lane.' : 'No reply.';
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ reply, session: skey }));
        });
    });
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
      res.writeHead(200, { 'Content-Type': extMap[ext] || 'text/plain' });
      res.end(fs.readFileSync(filePath));
    } else {
      res.writeHead(404);
      res.end('Not Found');
    }
    return;
  }
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`Mission Control server running on port ${PORT}`);
});