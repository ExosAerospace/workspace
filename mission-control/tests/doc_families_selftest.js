// exo3 eval for lib/doc-families.js — replays the task #2414 failure (Jon 2026-10-13: 80 docs shown as current,
// "I cannot tell what are the canonical documents"). Run: node mission-control/tests/doc_families_selftest.js
const assert = require('assert');
const path = require('path');
const fs = require('fs');
const f = require('../lib/doc-families');
let n = 0; const ok = (c, msg) => { assert.ok(c, 'FAIL: ' + msg); n++; };
const D = (id, stored, extra = {}) => ({ id, stored_name: stored.replace(/^(\d+)_/, (x, k) => (1791900000000 + Number(k)) + '_'), filename: extra.filename || stored.replace(/^\d+_/, ''), extension: path.extname(stored), uploaded_at: extra.t || '2026-10-12T00:00:00Z', task_id: 'T', ...extra });

// 1. same deck under drifting keys -> only the newest iteration per format is current
const deck = [
  D('a', '1_Exos_SSLC_Board_Offer_Overview_2026-10-10_r2.pptx', { doc_key: 'exos-sslc-board-offer-overview', t: '2026-10-13T19:00:00Z' }),  // re-uploaded later, older rev
  D('b', '2_Exos_SSLC_Board_Offer_Overview_2026-10-12_r5.pptx', { doc_key: 'SSLC-B9-pptx', t: '2026-10-13T18:00:00Z' }),
  D('c', '3_Exos_SSLC_Board_Offer_Overview_2026-10-12_r5.pdf', { doc_key: 'SSLC-B9-pdf' }),
  D('d', '4_Exos_SSLC_Board_Offer_Overview_2026-10-12_r5_PRINT.pdf', { doc_key: 'SSLC-B9-print-pdf' }),
  D('e', '5_Exos_SSLC_Board_Offer_Overview_2026-10-11_r3_FINAL.pptx', { doc_key: 'x-r3-final' }),
];
let out = f.applyFamilies(deck);
const cur = out.filter(m => m.current !== false).map(m => m.id).sort();
ok(JSON.stringify(cur) === JSON.stringify(['b', 'c', 'd']), 'r5 (pptx, pdf, print pdf) current; r2 re-upload + r3 FINAL superseded');
ok(out.find(m => m.id === 'a').superseded_by_name === 'Exos_SSLC_Board_Offer_Overview_2026-10-12_r5.pptx', 'superseded row names its replacement by real filename');
ok(new Set(out.filter(m => m.current !== false).map(m => m.doc_group)).size === 1, 'all formats + print copy = ONE document row');
// 2. display title stored as filename -> grouped by real stored name
out = f.applyFamilies([D('t1', '9_Term_Sheet_2026-10-13_r1.docx', { filename: 'Term Sheet r1 (Word)', doc_key: 'k1' }), D('t2', '8_Term_Sheet_2026-10-12_r0.docx', { filename: 'old', doc_key: 'k2' })]);
ok(out.find(m => m.id === 't1').current !== false && out.find(m => m.id === 't2').current === false, 'title-named record grouped by real filename');
// 3. a hand-restored doc is never auto-superseded; a hand-superseded one stays superseded
out = f.applyFamilies([D('r1', '1_Memo_2026-10-01.docx', { restored_at: 'x' }), D('r2', '2_Memo_2026-10-05.docx'), D('s1', '3_Plan_2026-10-09.docx', { current: false })]);
ok(out.find(m => m.id === 'r1').current !== false && out.find(m => m.id === 's1').current === false, 'manual Restore / Superseded win');
// 3b. newest iteration superseded by hand -> older iterations must not resurface (10/13 #2414 Option B bug)
out = f.applyFamilies([D('o1', '1_Offer_Summary_2026-10-07.pdf'), D('o2', '2_Offer_Summary_2026-10-12_r4.pdf', { current: false, superseded_note: 'restated' })]);
ok(out.every(m => m.current === false), 'retiring the newest iteration retires the older ones');
// 4. executed / charter docs -> reference section; Exo "_SIGN" drafts are NOT reference
out = f.applyFamilies([D('x1', '1_SSLC signed Asset Acquisition 2025 FULLY EXECUTED.pdf'), D('x2', '2_SSLC_Bylaws.pdf'), D('x3', '3_SSLC_Board_Resolutions_2026-10-02_SIGN.pdf')]);
ok(out.find(m => m.id === 'x1').doc_role === 'reference' && out.find(m => m.id === 'x2').doc_role === 'reference' && !out.find(m => m.id === 'x3').doc_role, 'reference detection');
// 5. BLK3 / M101 names never mangled
ok(f.familyOf({ stored_name: '1791900000001_BLK3_M101_Sizing_v2.docx' }) === 'blk3-m101-sizing.docx', 'BLK3/M101 safe');
// 6. live replay on #2414 (if the store is present): no family has two current files of the same format
const META = path.join(__dirname, '..', 'uploads', '_meta.json');
if (fs.existsSync(META)) {
  const live = f.applyFamilies(JSON.parse(fs.readFileSync(META, 'utf8')).filter(m => String(m.task_id) === '2414')).filter(m => m.current !== false);
  const fams = live.map(m => m.family); ok(fams.length === new Set(fams).size, '#2414 live: one current file per document per format');
  ok(live.some(m => /RESTATED_2026-10-13_r1\.docx$/.test(m.stored_name)), '#2414 live: the 10/13 restated term sheet is current');
  const working = new Set(live.filter(m => !m.doc_role).map(m => m.doc_group));
  ok(working.size <= 8 && !working.has('exos-sslc-optionb-offer-summary'), `#2414 live: working set is the real deliverables only (${working.size}); Option B summary superseded by the restated term sheet`);
}
console.log(`doc-families selftest: ${n}/${n} pass`);
