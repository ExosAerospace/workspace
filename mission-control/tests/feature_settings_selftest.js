'use strict';
// Selftest for lib/feature-settings.js (mc-feature-settings-exo3). Run: node mission-control/tests/feature_settings_selftest.js
// Uses the real catalog read-only; selections/requests/fleet go to a temp dir.
const fs = require('fs'), os = require('os'), path = require('path'), assert = require('assert');
const fsx = require('../lib/feature-settings');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mcfs-'));
fsx._setPaths({ selections: path.join(tmp, 'sel.json'), requests: path.join(tmp, 'req.jsonl'), fleet: path.join(tmp, 'fleet.jsonl') });
let n = 0; const t = (name, fn) => { fn(); n++; console.log('ok', n, name); };

const cat = fsx.loadCatalog();
const ids = fsx.catalogIds(cat);
t('catalog has native + integrations, unique ids, required fields', () => {
  let count = 0;
  for (const sec of ['native', 'integrations']) for (const g of cat[sec]) for (const it of g.items) {
    count++; assert(it.id && it.name && it.desc && it.tier && it.status, 'missing field on ' + it.id);
    assert(cat.tiers[it.tier], 'bad tier ' + it.id); assert(cat.status_legend[it.status], 'bad status ' + it.id);
  }
  assert.strictEqual(ids.size, count, 'duplicate ids');
  ['quickbooks', 'bamboohr', 'proton', 'teamwork'].forEach(x => assert(ids.has(x), 'Jon-named integration missing: ' + x));
});
t('native pages referenced exist', () => {
  for (const g of cat.native) for (const it of g.items) if (it.page) assert(fs.existsSync(path.join(__dirname, '..', it.page)), 'page missing ' + it.page);
});
t('unknown id rejected', () => { assert(!fsx.validateSelection(cat, ['tasks', 'nope']).ok); });
t('non-array rejected', () => { assert(!fsx.validateSelection(cat, 'tasks').ok); });
t('core forced on', () => { const v = fsx.validateSelection(cat, []); assert(v.ok); fsx.defaultEnabled(cat).forEach(c => assert(v.enabled.includes(c))); });
t('save + reload per tenant', () => {
  const r = fsx.saveSelection('space-grove', ['quickbooks'], 'test@x');
  assert(r.ok && r.enabled.includes('quickbooks') && r.enabled.includes('tasks'));
  const s = JSON.parse(fs.readFileSync(path.join(tmp, 'sel.json'), 'utf8'));
  assert(s.tenants['space-grove'].updated_by === 'test@x');
});
t('bad tenant id rejected', () => { assert(!fsx.saveSelection('../etc', [], 'x').ok); });
t('request validation', () => {
  assert(!fsx.addRequest({ kind: 'bogus', title: 'abc' }, 'x').ok);
  assert(!fsx.addRequest({ kind: 'integration', title: '' }, 'x').ok);
  const r = fsx.addRequest({ kind: 'integration', title: 'Connect Salesforce', system: 'Salesforce', priority: 'must', tenant: 'space-grove' }, 'u@x');
  assert(r.ok && r.request.id.startsWith('fr_'));
  assert.strictEqual(fsx.listRequests()[0].title, 'Connect Salesforce');
});
t('telemetry written', () => { const l = fs.readFileSync(path.join(tmp, 'fleet.jsonl'), 'utf8').trim().split('\n').map(JSON.parse); assert(l.every(e => e.agent === 'mc-feature-settings-exo3')); assert(l.length >= 2); });
t('handle(): 401 without session, ignores other routes', () => {
  let code; const res = { writeHead: c => { code = c; }, end: () => {} };
  assert(fsx.handle({ url: '/api/settings/features', method: 'GET' }, res, null) && code === 401);
  assert(!fsx.handle({ url: '/api/tasks', method: 'GET' }, res, { role: 'admin' }));
});
t('handle(): member cannot save selection (403)', () => {
  let code; const res = { writeHead: c => { code = c; }, end: () => {} };
  fsx.handle({ url: '/api/settings/features', method: 'POST', on: () => {} }, res, { role: 'member', email: 'm@x' }); assert.strictEqual(code, 403);
});
fs.rmSync(tmp, { recursive: true, force: true });
console.log(`PASS ${n}/${n}`);
