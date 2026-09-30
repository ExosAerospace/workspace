// Inventory photos — multiple photos per BLK3 BOM line, plus human-confirmed delete.
// Jon 2026-09-29: "allow multiple pictures for the same part" + "a way to delete photos with a confirmation".
//
// Store: data/inventory-photos.json, keyed by the BOM line key ("section#item", same key as bom-edits.json)
// so it survives any bom-index / inventory.json rebuild.
//   { added:   { "<key>": [ {id, file, by, at, caption} ] },    ← photos added from the page
//     removed: { "<key>": { "<photoId>": {by, at, recycle_id} } } } ← photos a person deleted
// Ledger photos (from inventory.json / task uploads) are never edited in place: deleting one hides it
// via `removed`, and the original task upload stays on its task. Page-added photo files are moved into
// the recycle bin (lib/recycle.js), so every delete is recoverable for 90 days.
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const recycle = require('./recycle');

const MC_DIR = path.join(__dirname, '..');
const STORE = path.join(MC_DIR, 'data', 'inventory-photos.json');
const UPLOADS = path.join(MC_DIR, 'uploads');
const PHOTO_DIR = path.join(UPLOADS, 'inventory-photos');
const IMG_EXTS = ['.png', '.jpg', '.jpeg', '.heic', '.webp', '.gif'];

function load() {
  try { const d = JSON.parse(fs.readFileSync(STORE, 'utf8')); return { added: d.added || {}, removed: d.removed || {} }; }
  catch { return { added: {}, removed: {} }; }
}
function save(d) {
  const tmp = STORE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(d, null, 1));
  fs.renameSync(tmp, STORE);
}

// Stable id for a ledger photo (task upload id, else stored filename).
function ledgerId(p) { return 'led_' + String(p.upload || p.file || ''); }

// Merge ledger photos + page-added photos for one line, minus the removed ones. Newest last.
function photosFor(key, ledgerPhotos, store) {
  const d = store || load();
  const gone = d.removed[key] || {};
  const out = [];
  for (const p of (ledgerPhotos || [])) {
    const id = ledgerId(p);
    if (gone[id] || !p.file) continue;
    out.push({ id, url: '/uploads/' + encodeURIComponent(p.file), by: p.by || '', at: p.at || '', source: 'task', task: p.task || '' });
  }
  for (const p of (d.added[key] || [])) {
    if (gone[p.id]) continue;
    out.push({ id: p.id, url: '/uploads/inventory-photos/' + encodeURIComponent(p.file), by: p.by || '', at: p.at || '', caption: p.caption || '', source: 'page' });
  }
  out.sort((a, b) => String(a.at).localeCompare(String(b.at)));
  return out;
}

// files: [{filename, data(Buffer)}]. Returns the added photo entries.
function add(key, files, who, caption) {
  if (!key) throw new Error('key required');
  const imgs = (files || []).filter(f => f && f.filename && f.data && f.data.length);
  if (!imgs.length) throw new Error('No image provided');
  for (const f of imgs) {
    const ext = path.extname(f.filename).toLowerCase();
    if (!IMG_EXTS.includes(ext)) throw new Error(`${f.filename}: only images allowed (${IMG_EXTS.join(', ')})`);
  }
  fs.mkdirSync(PHOTO_DIR, { recursive: true });
  const d = load();
  const list = d.added[key] || (d.added[key] = []);
  const now = new Date().toISOString();
  const added = [];
  for (const f of imgs) {
    const id = 'ip_' + crypto.randomBytes(6).toString('hex');
    const stored = `${Date.now()}_${id}_${f.filename.replace(/[^a-zA-Z0-9._-]/g, '_')}`;
    fs.writeFileSync(path.join(PHOTO_DIR, stored), f.data);
    const e = { id, file: stored, by: who || 'MC user', at: now, caption: caption || '' };
    list.push(e); added.push(e);
  }
  save(d);
  return added;
}

// Delete one photo (the page asks the person to confirm first). Snapshots to the recycle bin.
function remove(key, photoId, ledgerPhotos, who, route) {
  if (!key || !photoId) throw new Error('key and photo id required');
  const d = load();
  const gone = d.removed[key] || (d.removed[key] = {});
  if (gone[photoId]) return { ok: true, already: true };
  const page = (d.added[key] || []).find(p => p.id === photoId);
  const led = (ledgerPhotos || []).find(p => ledgerId(p) === photoId);
  if (!page && !led) throw new Error('photo not found on this line');
  const rid = recycle.newId();
  let parked = null;
  if (page) parked = recycle.parkedPath(path.join(PHOTO_DIR, page.file), rid);
  // Record first (durable), then move the file — same order as the other MC deletes.
  recycle.record({ recycle_id: rid, type: 'inventory-photo', id: photoId, who, route,
    record: page || led, extra: { key, source: page ? 'page' : 'task', parked_file: parked },
    source: { kind: 'json', file: 'data/inventory-photos.json', path: ['removed', key], key: 'id' } });
  if (page) recycle.parkFile(path.join(PHOTO_DIR, page.file), rid);
  gone[photoId] = { by: who, at: new Date().toISOString(), recycle_id: rid };
  save(d);
  return { ok: true, recycle_id: rid };
}

module.exports = { STORE, PHOTO_DIR, IMG_EXTS, load, save, ledgerId, photosFor, add, remove };
