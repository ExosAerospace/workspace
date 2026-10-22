'use strict';
// ── MC SETTINGS > FEATURES (mc-feature-settings-exo3, Jon 2026-10-22, MC-Industry rollout) ──────
// Feature-selection matrix for outside organizations: native modules + API integrations, each
// switchable per tenant, plus a request form for new integrations/features.
//   Catalog:    data/mc-feature-catalog.json        (source of truth for what MC offers; hand-edited)
//   Selections: data/mc-feature-selections.json     { tenants: { <tenant>: { enabled:[ids], updated_at, updated_by } } }
//   Requests:   data/mc-feature-requests.jsonl      (append-only, one request per line)
//   Telemetry:  ../logs/fleet-events.jsonl          (agent 'mc-feature-settings-exo3')
// Routes: GET  /api/settings/features            any session (catalog + selection for tenant)
//         POST /api/settings/features            admin/manager only (save selection)
//         POST /api/settings/feature-request     any session (log a request)
//         GET  /api/settings/feature-requests    admin/manager only
// Selections are a menu/config record today; per-tenant enforcement lands with the hosted build.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const MC_DIR = path.join(__dirname, '..');
let paths = {
  catalog: path.join(MC_DIR, 'data', 'mc-feature-catalog.json'),
  selections: path.join(MC_DIR, 'data', 'mc-feature-selections.json'),
  requests: path.join(MC_DIR, 'data', 'mc-feature-requests.jsonl'),
  fleet: path.join(MC_DIR, '..', 'logs', 'fleet-events.jsonl'),
};
const TENANT_RE = /^[a-z0-9][a-z0-9-]{0,39}$/;
const KINDS = ['integration', 'feature', 'change'];

function _setPaths(p) { paths = Object.assign({}, paths, p); } // selftest hook

function loadCatalog() { return JSON.parse(fs.readFileSync(paths.catalog, 'utf8')); }

function catalogIds(cat) {
  const ids = new Set();
  for (const sec of ['native', 'integrations']) for (const g of (cat[sec] || [])) for (const it of g.items) ids.add(it.id);
  return ids;
}

function loadSelections() {
  try { return JSON.parse(fs.readFileSync(paths.selections, 'utf8')); } catch { return { tenants: {} }; }
}

function defaultEnabled(cat) { // core tier always on
  const out = [];
  for (const sec of ['native', 'integrations']) for (const g of (cat[sec] || [])) for (const it of g.items) if (it.tier === 'core') out.push(it.id);
  return out;
}

function fleet(action, outcome, detail) {
  try { fs.appendFileSync(paths.fleet, JSON.stringify({ ts: new Date().toISOString(), corr: '', agent: 'mc-feature-settings-exo3', kind: 'govern', action, owner: 'John Quinn', outcome, level: 'info', detail }) + '\n'); } catch {}
}

// Validate + normalize a selection. Unknown ids rejected; core ids forced on. Returns {ok, enabled|error}.
function validateSelection(cat, enabled) {
  if (!Array.isArray(enabled)) return { ok: false, error: 'enabled must be an array of feature ids' };
  const ids = catalogIds(cat);
  const bad = enabled.filter(x => !ids.has(x));
  if (bad.length) return { ok: false, error: 'unknown feature id(s): ' + bad.slice(0, 5).join(', ') };
  const set = new Set(enabled.concat(defaultEnabled(cat)));
  return { ok: true, enabled: [...ids].filter(x => set.has(x)) };
}

function saveSelection(tenant, enabled, who) {
  if (!TENANT_RE.test(tenant || '')) return { ok: false, error: 'bad tenant id' };
  const cat = loadCatalog();
  const v = validateSelection(cat, enabled);
  if (!v.ok) return v;
  const sel = loadSelections();
  sel.tenants = sel.tenants || {};
  sel.tenants[tenant] = { enabled: v.enabled, updated_at: new Date().toISOString(), updated_by: who || 'unknown' };
  const tmp = paths.selections + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(sel, null, 2));
  fs.renameSync(tmp, paths.selections);
  fleet('selection_saved', 'ok', { tenant, count: v.enabled.length, by: who });
  return { ok: true, tenant, enabled: v.enabled };
}

function addRequest(body, who) {
  const kind = String(body.kind || '').toLowerCase();
  const title = String(body.title || '').trim().slice(0, 160);
  const detail = String(body.detail || '').trim().slice(0, 4000);
  if (!KINDS.includes(kind)) return { ok: false, error: 'kind must be integration, feature or change' };
  if (title.length < 3) return { ok: false, error: 'title required' };
  const tenant = TENANT_RE.test(body.tenant || '') ? body.tenant : 'exos';
  const entry = {
    id: 'fr_' + new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14) + '_' + crypto.randomBytes(3).toString('hex'),
    ts: new Date().toISOString(), tenant, kind, title, detail,
    system: String(body.system || '').trim().slice(0, 120), // e.g. "Salesforce", "Gusto"
    priority: ['must', 'nice'].includes(body.priority) ? body.priority : 'nice',
    who: who || 'unknown', status: 'new',
  };
  fs.appendFileSync(paths.requests, JSON.stringify(entry) + '\n');
  fleet('feature_request', 'ok', { id: entry.id, tenant, kind, title });
  return { ok: true, request: entry };
}

function listRequests() {
  try { return fs.readFileSync(paths.requests, 'utf8').split('\n').filter(Boolean).map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean).reverse(); } catch { return []; }
}

const canAdmin = s => !!s && (s.role === 'admin' || s.role === 'manager');

// Returns true if handled.
function handle(req, res, session) {
  const p = req.url.split('?')[0];
  if (!p.startsWith('/api/settings/feature')) return false;
  const send = (code, obj) => { res.writeHead(code, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(obj)); };
  if (!session) { send(401, { error: 'auth required' }); return true; }
  const who = session.email || session.name || 'unknown';
  const readBody = () => new Promise(resolve => { let b = ''; req.on('data', c => { b += c; if (b.length > 1e5) req.destroy(); }); req.on('end', () => { try { resolve(JSON.parse(b || '{}')); } catch { resolve({}); } }); });
  try {
    if (p === '/api/settings/features' && req.method === 'GET') {
      const tenant = new URL(req.url, 'http://x').searchParams.get('tenant') || 'exos';
      const cat = loadCatalog();
      const t = (loadSelections().tenants || {})[tenant];
      send(200, { catalog: cat, tenant, enabled: t ? t.enabled : defaultEnabled(cat), updated_at: t ? t.updated_at : null, updated_by: t ? t.updated_by : null, can_edit: canAdmin(session) });
      return true;
    }
    if (p === '/api/settings/features' && req.method === 'POST') {
      if (!canAdmin(session)) { send(403, { error: 'admin or manager only' }); return true; }
      readBody().then(b => { const r = saveSelection(b.tenant || 'exos', b.enabled, who); send(r.ok ? 200 : 400, r); });
      return true;
    }
    if (p === '/api/settings/feature-request' && req.method === 'POST') {
      readBody().then(b => { const r = addRequest(b, who); send(r.ok ? 200 : 400, r); });
      return true;
    }
    if (p === '/api/settings/feature-requests' && req.method === 'GET') {
      if (!canAdmin(session)) { send(403, { error: 'admin or manager only' }); return true; }
      send(200, { requests: listRequests() });
      return true;
    }
  } catch (e) {
    fleet('error', 'fail', { route: p, err: String(e).slice(0, 200) });
    send(500, { error: 'feature settings unavailable' });
    return true;
  }
  return false;
}

module.exports = { handle, validateSelection, saveSelection, addRequest, listRequests, loadCatalog, defaultEnabled, catalogIds, _setPaths };
