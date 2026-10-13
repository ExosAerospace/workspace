// Document families for task attachments (Jon 2026-10-13: "I cannot tell what are the canonical documents
// on any given task that had iterations").
//
// doc_key versioning (scripts/mc-attach.py) only chains revisions that reuse the same key, and in practice the
// same document gets attached under many keys (…-pdf, …-2026-10-10-r2, SSLC-B8-pptx, SSLC-B9-pptx …). So on
// read we also group by FAMILY = filename stem with dates / r# / rev# / v# / FINAL / DRAFT / "(1)" stripped,
// plus the file format. Within a family the newest iteration (latest date in the name, then highest revision
// number, then upload time) is the current document; the rest are shown as superseded. Computed per request,
// nothing is rewritten on disk. A document someone restored by hand (restored_at) is never auto-superseded.

// The real file name: stored_name minus its upload-timestamp prefix (filename is sometimes a display title).
const realName = m => String(m.stored_name || m.filename || '').replace(/^\d{10,}_/, '') || String(m.filename || '');

function extOf(m) {
  const fromName = (realName(m).match(/\.[a-z0-9]{2,5}$/i) || [''])[0];
  return (fromName || m.extension || '').toLowerCase();
}

function familyOf(m) {
  let s = realName(m);
  const ext = extOf(m);
  if (ext && s.toLowerCase().endsWith(ext)) s = s.slice(0, -ext.length);
  s = s.toLowerCase()
    .replace(/---[0-9a-f-]{20,}$/, '')                        // upload uuid suffix
    .replace(/\(?\d{4}-\d{2}-\d{2}\)?/g, ' ')                  // ISO dates
    .replace(/\(\d+\)/g, ' ');                                  // browser duplicate "(1)"
  // version / status tokens must be separator-delimited, so BLK3, RDRE, M101 are never touched
  const TOK = /(^|[\s_.\-])((r|rev|v)\s?\d+(\.\d+)*|rev|final|draft|updated|latest|copy|clean)(?=$|[\s_.\-])/g;
  let prev;
  do { prev = s; s = s.replace(TOK, ' '); } while (s !== prev);
  s = s.replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return (s || 'document') + ext;
}

function rankOf(m) {
  const name = realName(m);
  const dates = name.match(/\d{4}-\d{2}-\d{2}/g);
  const revs = [...name.toLowerCase().matchAll(/(?:^|[\s_.\-])(?:r|rev|v)\s?(\d+)(?=$|[\s_.\-])/g)].map(x => Number(x[1]));
  return { date: dates ? dates[dates.length - 1] : '', rev: revs.length ? Math.max(...revs) : 0, t: String(m.uploaded_at || '') };
}

function newerFirst(a, b) {
  const x = rankOf(a), y = rankOf(b);
  if (x.date !== y.date) return x.date < y.date ? 1 : -1;
  if (x.rev !== y.rev) return y.rev - x.rev;
  return x.t < y.t ? 1 : x.t > y.t ? -1 : 0;
}

// Mutates copies: returns a new array where older iterations carry current:false + auto_superseded.
function applyFamilies(list) {
  const out = list.map(m => ({ ...m }));
  const supersede = (g, why) => {
    if (g.length < 2) return;
    g.sort(newerFirst);
    const top = g[0];
    for (const m of g.slice(1)) {
      if (m.restored_at || m.current === false) continue;
      m.current = false; m.auto_superseded = why;
      m.superseded_by_name = top.filename; m.superseded_at = m.superseded_at || top.uploaded_at;
    }
  };
  const live = () => out.filter(m => m.current !== false);
  const byKey = {};
  for (const m of live()) if (m.doc_key) { const k = m.doc_key + extOf(m); (byKey[k] = byKey[k] || []).push(m); }
  Object.values(byKey).forEach(g => supersede(g, 'same document key'));
  const byFam = {};
  for (const m of live()) { const f = familyOf(m); m.family = f; (byFam[f] = byFam[f] || []).push(m); }
  Object.values(byFam).forEach(g => supersede(g, 'newer iteration'));
  // one DOCUMENT = all formats (pptx / pdf / docx / print copy) of the same family -> shown as one row
  for (const m of out) m.doc_group = familyOf(m).replace(/\.[a-z0-9]+$/, '').replace(/-print$/, '');
  // REFERENCE records (source docs received, executed/charter documents) sit in their own section, not in the
  // working set: explicit doc_role:'reference', or the name says executed / articles / bylaws / statement of info.
  const REF = /(fully[\s_-]*executed|[\s_-]executed|articles[\s_-]*(of|amendment)|bylaws|statement[\s_-]*of[\s_-]*information)/i;
  for (const m of out) if (!m.doc_role && REF.test(realName(m) + ' ' + (m.filename || ''))) m.doc_role = 'reference';
  return out;
}

module.exports = { familyOf, rankOf, applyFamilies };
