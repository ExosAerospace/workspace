'use strict';
// ── ENTITY PAGE GATE (containerized MC cells, ENTITY != 'exos'; Jon 2026-10-22) ─────────────
// A rollout cell must never show Exos data, and should only show the modules switched on for
// it in Settings > Features. This module:
//   1. allowed(page)    — page is served only if its feature is enabled for this tenant (or it
//                          is an always-on shell page) AND it is not on the NEVER list.
//   2. sanitize(html)   — strips nav links to pages that aren't allowed, plus Exos-only strings
//                          baked into shared pages (staff alias map, BLK3/HVRR labels, vault link).
//   3. writeCatalog()   — writes an entity-safe feature catalog (no Exos-only items/wording).
// Exos itself never loads this module (install() returns null for 'exos').
const fs = require('fs');
const path = require('path');

// Pages with Exos programs, people, contracts or legal templates hard-coded in them.
// Never served in an entity cell, whatever the feature selection says.
const NEVER = new Set([
  'erp-rollout.html', 'process-library.html', 'help.html', 'blk3-bom.html', 'blk3-deal-flow.html',
  'montana-partner.html', 'capstone-tracker.html', 'apac-opportunities.html', 'ctd-dd.html',
  'mtp.html', 'exos-prototype.html', 'sslc-board.html', 'program.html', 'readiness.html', 'read.html',
  'sent-review.html', 'fleet.html', 'research.html', 'capability-gaps.html', 'dossier.html',
  'consortium.html', 'docusign.html', 'sign.html', 'payload-orders.html', 'schedule.html',
  'gantt.html', 'people.html', 'dataroom.html', 'vault.html', 'gov-readiness.html',
  'ai-tool-use-policy.html', 'commissions.html', 'compliance-screening.html',
  'backup.html', // client-side hard-coded Exos password check
  'finance.html', // Exos capital-bridge / operational finance
]);
// Shell pages every logged-in user needs.
const ALWAYS = new Set(['index.html', 'login.html', 'set-password.html', 'settings.html', 'search.html']);
// Extra pages that belong to a feature beyond the catalog's primary page.
const EXTRA = { receiving: ['shop-inventory.html', 'inventory.html'], tasks: ['index.html'] };

// Display strings in shared pages that name Exos programs/people. Entity cells only.
const SCRUB = [
  [/const PERSON_ALIAS = \{[\s\S]*?\n\};/, 'const PERSON_ALIAS = {};'],
  [/<a href="https:\/\/vault\.exosaero\.space"[\s\S]*?<\/a>/g, ''],
  [/Labor by BOM section — BLK3 \/ HVRR weekly tasks/g, 'Labor by BOM section — weekly tasks'],
  [/vehicle BOMs \(BLK3, HVRR\)/g, 'product BOMs'],
  [/Parts shared by BLK3 and HVRR/g, 'Parts shared by several builds'],
  [/BLK3 inventory-view codes/g, 'Inventory-view codes'],
  [/BLK3 Schedule/g, 'Schedule'],
  [/Series A CRM/g, 'Investor CRM'],
  [/'jquinn@exosaero\.com'/g, "''"],
  [/\/uploads\/Exos_Investor_Master_List_FULL_EXPORT\.xlsx/g, '/uploads/Investor_Master_List_FULL_EXPORT.xlsx'],
  [/<!--[\s\S]*?-->/g, ''],                                   // HTML comments (dev notes)
  [/\/\*[^*]*?(?:Jon|John|Lizi|Exos|BLK3|HVRR|#\d{3,})[^*]*?\*\//g, ''], // block comments naming Exos people/programs
  [/([;{}),\s])\/\/[^\n'"`]*$/gm, '$1'],                    // trailing // line comments (no quotes → not a URL in a string)
  [/^\s*'[a-z .+]+'\s*:\s*'(?:John Quinn|Jon|Lizi Quinn|Neil Milburn|Steve Norsworthy|Phil Eaton|Kyle Ballard|Russ Blink|Mike Talley|Toshihisa Kumazawa|Andrew Overman|Victor Castilleja)'\s*,?[^\n]*$/gm, ''],
  [/'(?:[a-z .+]+)':'(?:John Quinn|Jon|Lizi Quinn|Neil Milburn|Steve Norsworthy|Phil Eaton|Kyle Ballard|Russ Blink|Mike Talley|Toshihisa Kumazawa|Andrew Overman|Victor Castilleja)',?/g, ''],
  [/<option value="Jon">Jon<\/option>/g, ''],
  [/\|\|\s*'(?:Jon|John Quinn)'/g, "|| ''"],
  [/value="John Quinn"/g, 'value=""'],
  [/e\.g\. Lizi Quinn/g, 'e.g. Jane Smith'],
  [/e\.g\. Montana Spaceport, HVRR-RDRE/g, 'e.g. Project name'],
  [/<code>@exo reassign to Neil<\/code>[^<]*/g, '<code>@exo reassign to &lt;name&gt;</code> — hand it off'],
  [/No com\.exos\.\* jobs found/g, 'No scheduled jobs found'],
  [/^[ \t]*\/\/[^\n]*$/gm, ''],
  [/, \{ value: 'Jon\+Exo', label: 'Both' \}/g, ''],
  [/Hot Tasks — Series A &amp; Revenue Priority|Hot Tasks — Series A & Revenue Priority/g, 'Hot Tasks — Priority'],                              // whole-line // comments (dev notes)
  [/Needs Jon/g, 'Needs Approval'],
  [/Jon's Decision card/g, "the approver's Decision card"],
  [/Jon \(Decisions board\)/g, 'the approver (Decisions board)'],
  [/Jon \(Decision\)/g, 'Approver (Decision)'],
  [/→ Jon\)/g, '→ approver)'],
  [/→ Jon approves/g, '→ the approver approves'],
  [/Jon approves/g, 'the approver approves'],
  [/goes to Jon with/g, 'goes to the approver with'],
  [/<option value="Jon\+Exo">Both<\/option>/g, ''],
  [/\{ name: 'Jon\+Exo', label: 'Jon \+ Exo \(Both\)' \},?/g, ''],
  [/owner: 'Jon' \}/g, "owner: '' }"],
  [/BLK3 Build Shortfall/g, 'Build Shortfall'],
  [/what the BLK3 needs/g, 'what the build needs'],
  [/BLK3_Inventory_Report/g, 'Inventory_Report'],
  [/blank = Greenville/g, 'blank = company address'],
  [/@exosaerospace\.com/g, '@example.com'],
  [/e\.g\. lquinn@exosaero\.com/g, 'e.g. jane@example.com'],
  [/'Series A'/g, "'Investors'"], [/"Series A"/g, '"Investors"'], [/>Series A</g, '>Investors<'],
];

function create(entity, dataDir) {
  if (!entity || entity === 'exos') return null;
  const catalogFile = path.join(dataDir, 'mc-feature-catalog.json');
  const selectionsFile = path.join(dataDir, 'mc-feature-selections.json');
  const readJson = f => { try { return JSON.parse(fs.readFileSync(f, 'utf8')); } catch { return null; } };

  function enabledIds(cat) {
    const t = ((readJson(selectionsFile) || {}).tenants || {})[entity];
    if (t && Array.isArray(t.enabled)) return new Set(t.enabled);
    const core = new Set();
    for (const sec of ['native', 'integrations']) for (const g of (cat[sec] || [])) for (const it of g.items) if (it.tier === 'core') core.add(it.id);
    return core;
  }

  // Recomputed per request (cheap: two small JSON reads) so a Settings save takes effect at once.
  function allowedPages() {
    const cat = readJson(catalogFile) || { native: [] };
    const on = enabledIds(cat);
    const pages = new Set(ALWAYS);
    for (const g of (cat.native || [])) for (const it of g.items) {
      if (!on.has(it.id)) continue;
      if (it.page) pages.add(it.page);
      for (const p of (EXTRA[it.id] || [])) pages.add(p);
    }
    for (const p of NEVER) pages.delete(p);
    return pages;
  }

  function allowed(page) {
    if (!/\.html$/.test(page)) return true; // assets/APIs are gated elsewhere
    return allowedPages().has(page);
  }

  function sanitize(html) {
    let s = String(html);
    for (const [re, rep] of SCRUB) s = s.replace(re, rep);
    const ok = allowedPages();
    // Drop single-line nav anchors that point at pages this cell doesn't serve.
    s = s.replace(/<a\s[^>]*href="\/?([a-z0-9-]+\.html)(?:[?#][^"]*)?"[^>]*>[^\n]*?<\/a>/g,
      (m, p) => (ok.has(p) || p === 'login.html') ? m : '');
    // Settings page: this cell edits only its own tenant.
    s = s.replace(/load\('exos'\)/g, `load('${entity}')`).replace(/a\.download = `exos-/g, 'a.download = `' + entity + '-');
    s = s.replace(/TENANT='exos'/g, `TENANT='${entity}'`).replace(/'\["exos"\]'/g, `'["${entity}"]'`);
    return s;
  }

  // Entity-safe catalog: drop Exos-only items, strip Exos wording from the menu text.
  function writeCatalog(srcFile) {
    const cat = readJson(srcFile);
    if (!cat) return false;
    const clean = t => String(t || '').replace(/\s*\((?:built for|Exos example)[^)]*\)/g, '').replace(/\bat Exos\b/g, 'in production').replace(/\bExos\b/g, 'the platform owner');
    for (const sec of ['native', 'integrations']) {
      cat[sec] = (cat[sec] || []).map(g => ({ ...g, items: g.items.filter(it => it.tier !== 'exos' && it.status !== 'exos_only' && !NEVER.has(it.page)).map(it => ({ ...it, desc: clean(it.desc) })) })).filter(g => g.items.length);
    }
    delete cat.owner; delete cat.purpose;
    if (cat.tiers) delete cat.tiers.exos;
    if (cat.status_legend) { delete cat.status_legend.exos_only; for (const k of Object.keys(cat.status_legend)) cat.status_legend[k] = clean(cat.status_legend[k]); }
    fs.writeFileSync(catalogFile, JSON.stringify(cat, null, 2));
    return true;
  }

  return { allowed, sanitize, writeCatalog, allowedPages, NEVER };
}

module.exports = { create, NEVER };
