'use strict';
// ── ENTITY BRAND + FIRST-RUN SETUP (containerized MC cells only; Jon 2026-10-22) ─────────────
// "The new user should first name their company and load any logo they want as well as naming
// their bot." A cell's display brand lives in data/brand.json (on the /data volume in cells):
//   { companyName, legalName, shortName, badge, botName, logoFile, setupComplete, updated_at, updated_by }
// The logo lives in data/brand/ (PNG, JPG, SVG, WebP; max 2 MB; SVG with script/foreignObject/
// on* handlers/javascript: is rejected, not served).
// Routes (cells only; create() returns null for Exos so the Exos MC never sees any of this):
//   GET  /brand/logo                    public (login page shows it); 404 when no logo
//   GET  /api/settings/brand            any session: brand + defaults + canEdit
//   POST /api/settings/brand            admin/manager: save names (+ complete:true finishes setup)
//   POST /api/settings/brand/logo       admin/manager: raw image body (Content-Type = image type)
//   POST /api/settings/brand/logo/remove admin/manager
// gate(): until setupComplete, an admin/manager's HTML page loads redirect to /setup.html and
// everyone else sees a "your admin is finishing setup" notice. APIs and static assets pass.
const fs = require('fs');
const path = require('path');

const MAX_LOGO = 2 * 1024 * 1024;
const TYPES = { png: 'image/png', jpg: 'image/jpeg', svg: 'image/svg+xml', webp: 'image/webp' };
// Display names only: letters, digits, spaces and light punctuation. No quotes, angle brackets,
// backslashes, backticks or $ — the values are spliced into served HTML and JS text.
const NAME_RE = /^[\p{L}\p{N} &.,()\-+/#]+$/u;
const EDITORS = new Set(['admin', 'manager']);

function sniff(buf) {
  if (buf.length >= 8 && buf.slice(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) return 'png';
  if (buf.length >= 3 && buf[0] === 0xff && buf[1] === 0xd8 && buf[2] === 0xff) return 'jpg';
  if (buf.length >= 12 && buf.slice(0, 4).toString('latin1') === 'RIFF' && buf.slice(8, 12).toString('latin1') === 'WEBP') return 'webp';
  const head = buf.slice(0, 4096).toString('utf8').replace(/^﻿/, '').trimStart();
  if (/^(<\?xml[\s\S]*?\?>\s*)?(<!--[\s\S]*?-->\s*)*<svg[\s>]/i.test(head)) return 'svg';
  return null;
}

// Returns an error string if the SVG carries anything active, else null.
function svgProblem(text) {
  const s = String(text);
  if (/<script[\s>/]/i.test(s)) return 'SVG contains a <script> element';
  if (/<foreignObject[\s>/]/i.test(s)) return 'SVG contains a <foreignObject> element';
  if (/<(iframe|embed|object)[\s>/]/i.test(s)) return 'SVG embeds other content';
  if (/[\s"'/]on[a-z]+\s*=/i.test(s)) return 'SVG contains an on* event attribute';
  if (/javascript:|vbscript:|data:text\/html/i.test(s)) return 'SVG contains a script link';
  if (/<!DOCTYPE|<!ENTITY/i.test(s)) return 'SVG contains a DOCTYPE/ENTITY declaration';
  if (/(?:xlink:)?href\s*=\s*["']\s*(?:https?:)?\/\//i.test(s)) return 'SVG links to an external resource';
  return null;
}

function deriveShort(name) {
  const words = String(name || '').split(/\s+/).filter(Boolean);
  if (!words.length) return '';
  if (words.length === 1) return words[0].slice(0, 12);
  const caps = words.filter(w => /^\p{L}/u.test(w) && !/^(of|and|the|&)$/i.test(w)).map(w => w[0].toUpperCase()).join('');
  return caps.slice(0, 6) || words[0].slice(0, 12);
}
function deriveBadge(name) {
  const words = String(name || '').split(/\s+/).filter(w => /^[\p{L}\p{N}]/u.test(w) && !/^(of|and|the)$/i.test(w));
  if (!words.length) return '';
  const b = words.length >= 2 ? words[0][0] + words[1][0] : words[0].slice(0, 2);
  return b.toUpperCase();
}

function create(entity, dataDir, opts) {
  if (!entity || entity === 'exos') return null;
  opts = opts || {};
  const brandFile = path.join(dataDir, 'brand.json');
  const logoDir = path.join(dataDir, 'brand');
  const defaults = Object.assign({ legal: '', name: '', short: '', badge: '' }, opts.defaults || {});
  let cache = { mtime: -1, value: {} };

  function read() {
    let m = 0;
    try { m = fs.statSync(brandFile).mtimeMs; } catch { m = 0; }
    if (m !== cache.mtime) {
      let v = {};
      if (m) { try { v = JSON.parse(fs.readFileSync(brandFile, 'utf8')) || {}; } catch { v = cache.value || {}; } }
      cache = { mtime: m, value: v };
    }
    return cache.value;
  }
  function write(v) {
    const tmp = brandFile + '.tmp';
    fs.writeFileSync(tmp, JSON.stringify(v, null, 1));
    fs.renameSync(tmp, brandFile);
    cache.mtime = -1;
    try { opts.onSave && opts.onSave(v); } catch (e) { console.warn('[MC brand] onSave failed:', e.message); }
  }
  function logoPath() {
    const f = read().logoFile;
    if (!f || !/^logo\.(png|jpg|svg|webp)$/.test(f)) return null;
    const p = path.join(logoDir, f);
    return fs.existsSync(p) ? p : null;
  }
  // Effective display brand (brand.json over built-in defaults) for lib/entity-brand.js.
  function effective() {
    const b = read();
    const lp = logoPath();
    let v = 0; if (lp) { try { v = Math.round(fs.statSync(lp).mtimeMs); } catch {} }
    return {
      name: b.companyName || defaults.name,
      legal: b.legalName || b.companyName || defaults.legal,
      short: b.shortName || defaults.short,
      badge: b.badge || defaults.badge,
      botName: b.botName || 'Exobot',
      logoUrl: lp ? '/brand/logo?v=' + v : null,
      setupComplete: !!b.setupComplete,
    };
  }
  const setupComplete = () => !!read().setupComplete;

  const json = (res, code, v) => { res.writeHead(code, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(v)); };
  const canEdit = s => !!(s && EDITORS.has(s.role));
  const who = s => (s && (s.email || s.name)) || 'user';

  function view(session) {
    const b = read();
    return {
      brand: {
        companyName: b.companyName || '', legalName: b.legalName || '', shortName: b.shortName || '', badge: b.badge || '',
        botName: b.botName || '', logoFile: logoPath() ? b.logoFile : null, setupComplete: !!b.setupComplete,
        updated_at: b.updated_at || null, updated_by: b.updated_by || null,
      },
      defaults: { companyName: defaults.name, legalName: defaults.legal, shortName: defaults.short, badge: defaults.badge, botName: 'Exobot' },
      effective: effective(),
      canEdit: canEdit(session),
      limits: { maxLogoBytes: MAX_LOGO, types: Object.values(TYPES) },
    };
  }

  function clean(field, v, max) {
    const s = String(v == null ? '' : v).replace(/\s+/g, ' ').trim();
    if (!s) return { ok: true, v: '' };
    if (s.length > max) return { ok: false, error: `${field} must be ${max} characters or fewer` };
    if (!NAME_RE.test(s)) return { ok: false, error: `${field} may use letters, numbers, spaces and & . , ( ) - + / # only` };
    return { ok: true, v: s };
  }

  function saveNames(j, session, res) {
    const cur = read();
    const out = Object.assign({}, cur);
    const rules = [['companyName', 'Company name', 80], ['legalName', 'Legal name', 120], ['shortName', 'Short name', 16], ['botName', 'Bot name', 24]];
    for (const [k, label, max] of rules) {
      if (!(k in j)) continue;
      const r = clean(label, j[k], max);
      if (!r.ok) return json(res, 400, { error: r.error });
      out[k] = r.v;
    }
    if ('badge' in j) {
      const bdg = String(j.badge || '').trim().toUpperCase();
      if (bdg && !/^[\p{Lu}\p{N}]{1,3}$/u.test(bdg)) return json(res, 400, { error: 'Badge must be 1 to 3 letters or digits' });
      out.badge = bdg;
    }
    if (!out.companyName) return json(res, 400, { error: 'Company name is required' });
    if (!out.shortName) out.shortName = deriveShort(out.companyName);
    if (!out.badge) out.badge = deriveBadge(out.shortName.length <= 3 ? out.shortName : out.companyName) || 'MC';
    if (!out.botName) out.botName = 'Exobot';
    if (j.complete === true) out.setupComplete = true;
    if (!('logoFile' in out)) out.logoFile = null;
    if (!('setupComplete' in out)) out.setupComplete = false;
    out.updated_at = new Date().toISOString(); out.updated_by = who(session);
    write(out);
    json(res, 200, Object.assign({ ok: true }, view(session)));
  }

  function saveLogo(req, res, session) {
    const chunks = []; let n = 0; let over = false;
    req.on('data', c => { if (over) return; n += c.length; if (n > MAX_LOGO) { over = true; json(res, 413, { error: 'Logo must be 2 MB or smaller' }); req.destroy(); return; } chunks.push(c); });
    req.on('end', () => {
      if (over) return;
      const buf = Buffer.concat(chunks);
      if (!buf.length) return json(res, 400, { error: 'No file received' });
      const kind = sniff(buf);
      if (!kind) return json(res, 415, { error: 'Logo must be a PNG, JPG, SVG or WebP image' });
      if (kind === 'svg') { const p = svgProblem(buf.toString('utf8')); if (p) return json(res, 415, { error: p + '. Save the logo without scripts or embedded content and try again.' }); }
      try {
        fs.mkdirSync(logoDir, { recursive: true });
        for (const f of fs.readdirSync(logoDir)) if (/^logo\./.test(f)) fs.unlinkSync(path.join(logoDir, f));
        const file = 'logo.' + kind;
        fs.writeFileSync(path.join(logoDir, file), buf);
        const cur = read();
        write(Object.assign({}, cur, { logoFile: file, updated_at: new Date().toISOString(), updated_by: who(session) }));
        json(res, 200, Object.assign({ ok: true }, view(session)));
      } catch (e) { json(res, 500, { error: 'Could not save logo: ' + e.message }); }
    });
  }

  function removeLogo(res, session) {
    try { if (fs.existsSync(logoDir)) for (const f of fs.readdirSync(logoDir)) if (/^logo\./.test(f)) fs.unlinkSync(path.join(logoDir, f)); } catch {}
    write(Object.assign({}, read(), { logoFile: null, updated_at: new Date().toISOString(), updated_by: who(session) }));
    json(res, 200, Object.assign({ ok: true }, view(session)));
  }

  // Public route (before the auth gate): the logo is display branding, not data.
  function handlePublic(req, res) {
    const p = String(req.url || '').split('?')[0];
    if (p !== '/brand/logo' || req.method !== 'GET') return false;
    const lp = logoPath();
    if (!lp) { res.writeHead(404, { 'Content-Type': 'text/plain' }); res.end('No logo'); return true; }
    const ext = path.extname(lp).slice(1);
    const h = { 'Content-Type': TYPES[ext] || 'application/octet-stream', 'Cache-Control': 'no-cache', 'X-Content-Type-Options': 'nosniff' };
    if (ext === 'svg') h['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox";
    res.writeHead(200, h);
    res.end(fs.readFileSync(lp));
    return true;
  }

  function handle(req, res, session) {
    const p = String(req.url || '').split('?')[0];
    if (!p.startsWith('/api/settings/brand')) return false;
    if (!session) { json(res, 401, { error: 'Unauthorized' }); return true; }
    if (p === '/api/settings/brand' && req.method === 'GET') { json(res, 200, view(session)); return true; }
    if (req.method !== 'POST') { json(res, 405, { error: 'Method not allowed' }); return true; }
    if (!canEdit(session)) { json(res, 403, { error: 'Only an admin or manager can change the company brand' }); return true; }
    if (p === '/api/settings/brand') {
      let b = ''; let big = false;
      req.on('data', c => { b += c; if (b.length > 20000) { big = true; req.destroy(); } });
      req.on('end', () => { if (big) return json(res, 413, { error: 'Too large' }); let j; try { j = JSON.parse(b || '{}'); } catch { return json(res, 400, { error: 'bad json' }); } saveNames(j, session, res); });
      return true;
    }
    if (p === '/api/settings/brand/logo') { saveLogo(req, res, session); return true; }
    if (p === '/api/settings/brand/logo/remove') { removeLogo(res, session); return true; }
    json(res, 404, { error: 'not found' }); return true;
  }

  function noticePage() {
    const e = effective();
    const esc = s => String(s || '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
    return `<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Setting up · Mission Control</title>
<style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;background:#0a1628;color:#e8edf5;min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0}
.c{background:#0f1e38;border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:32px 36px;max-width:460px;text-align:center}
h1{font-size:1.3rem;margin:0 0 10px}p{color:#a0aec0;font-size:.92rem;line-height:1.5;margin:0 0 18px}a{color:#0080ff;text-decoration:none;font-size:.85rem}</style></head>
<body><div class="c"><h1>Your admin is finishing setup</h1><p>${esc(e.name) || 'Your organization'}'s Mission Control is almost ready. Your administrator is naming the workspace and adding its logo. Check back in a few minutes.</p><a href="#" onclick="fetch('/api/logout',{method:'POST'}).finally(()=>location.href='/login');return false">Sign out</a></div></body></html>`;
  }

  // First-run gate. Call after the session is known. Returns true when it answered the request.
  function gate(req, res, session) {
    if (!session || setupComplete()) return false;
    if (req.method !== 'GET') return false;
    const p = String(req.url || '').split('?')[0];
    if (p.startsWith('/api/') || p.startsWith('/brand/') || p.startsWith('/brand-assets/') || p.startsWith('/data/')) return false;
    const base = p.split('/').pop();
    const isPage = p === '/' || /\.html$/.test(base) || !/\./.test(base);
    if (!isPage) return false;
    if (['setup.html', 'setup', 'login', 'login.html', 'set-password', 'set-password.html', 'logout'].includes(base)) return false;
    if (canEdit(session)) { res.writeHead(302, { 'Location': '/setup.html', 'Cache-Control': 'no-store' }); res.end(); return true; }
    res.writeHead(200, { 'Content-Type': 'text/html', 'Cache-Control': 'no-store' });
    res.end(noticePage());
    return true;
  }

  return { read, effective, setupComplete, handle, handlePublic, gate, logoPath };
}

module.exports = { create, sniff, svgProblem, deriveShort, deriveBadge, MAX_LOGO };
