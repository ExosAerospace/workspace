// Per-entity branding for containerized MC cells (ENTITY != 'exos').
// The Exos instance is untouched: install() is a no-op when ENTITY is 'exos'.
// For other entities every text/html and JS response is rewritten so that display
// branding (titles, headers, logo badges, company names) shows the entity, not Exos.
// Only human-facing text patterns are replaced; code identifiers, CSS vars (--exos-*),
// hostnames/emails (exosaero.com) and procedure IDs (EXOS-FIN-...) are left alone so
// nothing functional breaks. JSON/API data is never rewritten (SSLC books legitimately
// name Exos as a counterparty).

const BRANDS = {
  sslc: {
    legal: 'Scorpius Space Launch Company',
    name: 'Scorpius Space Launch Company',
    short: 'SSLC',
    badge: 'SS',
    mtp: null, // Exos MTP banner is hidden for SSLC
  },
};

function brandFor(entity, override) {
  const up = String(entity || '').toUpperCase();
  const base = BRANDS[entity] || { legal: up, name: up, short: up, badge: up.slice(0, 2), mtp: null };
  if (!override) return base;
  // data/brand.json (first-run setup, lib/brand-settings.js) wins over the built-in defaults.
  const o = override;
  return Object.assign({}, base, {
    name: o.name || base.name, legal: o.legal || o.name || base.legal, short: o.short || base.short,
    badge: o.badge || base.badge, botName: o.botName || null, logoUrl: o.logoUrl || null,
  });
}

// Order matters: longest/most specific first.
function rules(b) {
  return [
    [/(?:EXOS|Exos) Aerospace Systems (?:&amp;|&) Technologies,? Inc\.?/g, b.legal],
    [/EXOS AEROSPACE/g, b.name.toUpperCase()],
    [/(?:EXOS|Exos|eXOS|ExOS) Aerospace/g, b.name],
    [/(?:EXOS|Exos|eXOS) Mission(&nbsp;|\s)Control/g, b.short + ' Mission$1Control'],
    [/(<div class="brand-logo">)EX(<\/div>)/g, '$1' + b.badge + '$2'],
    // Standalone brand words in display text. Not preceded by an identifier/path/dash char,
    // not followed by one (keeps EXOS-FIN-001, exos-logo, --exos-blue, isExosSigner, etc.).
    [/(^|[^A-Za-z0-9_\-\/.@$])(?:EXOS|eXOS)(?![A-Za-z0-9_\-.@])/g, '$1' + b.short],
    [/(^|[^A-Za-z0-9_\-\/.@$])Exos(?![A-Za-z0-9_\-@]|\.[a-z])/g, '$1' + b.short],
  ];
}

// Assistant name in display text: "Exobot" and a standalone "Exo" become the cell's bot name.
// Skipped: identifiers/paths (exobot-widget.js, __mcExobot, ExO3, Exo3), compound owner values
// such as 'Jon+Exo', and a whole quoted
// value like 'Exo' or value="Exo" (data values the code compares against, e.g. owner names).
const BOT_RES = [
  /(^|[^A-Za-z0-9_\-\/.@$+])Exobot(?![A-Za-z0-9_\-@+]|\.[A-Za-z])/g,
  /(^|[^A-Za-z0-9_\-\/.@$+])Exo(?![A-Za-z0-9_\-@+]|\.[A-Za-z])/g,
];
function renameBot(s, bot) {
  if (!bot) return s;
  // Dropdown labels are display text even when quoted whole: { value: 'Exo', label: 'Exo' }.
  s = s.replace(/(\blabel\s*:\s*(['"]))Exo(?:bot)?\2/g, (m, pre, q) => pre + bot + q);
  for (const re of BOT_RES) {
    s = s.replace(re, (m, pre, off, all) => {
      const after = all[off + m.length];
      if ((pre === "'" || pre === '"' || pre === '`') && after === pre) return m;
      return pre + bot;
    });
  }
  return s;
}

// Uploaded logo replaces the text badge; the wrapper div keeps each page's size and radius.
function logoTag(b) {
  return '<div class="brand-logo" style="background:none;padding:0;overflow:hidden"><img src="' + b.logoUrl
    + '" alt="' + b.short + '" style="width:100%;height:100%;object-fit:contain;display:block"></div>';
}

// Pages that carry Exos legal templates (offer letters, NDAs with Exos's address and
// benefits). Swapping the name there would create a false SSLC document, so only the
// page chrome (title / header) is rebranded and templates stay as-is.
const CHROME_ONLY = new Set(['docusign.html']);

function rebrand(text, b, chromeOnly, page) {
  let s = String(text);
  if (chromeOnly) {
    return s.replace(/<title>[\s\S]*?<\/title>/i, m => applyRules(m, b));
  }
  s = applyRules(s, b);
  if (b.logoUrl) s = s.replace(/<div class="brand-logo">[^<]{0,4}<\/div>/g, () => logoTag(b));
  if (!b.mtp) s = s.replace(/<a href="mtp\.html" id="mtpBanner"[\s\S]*?<\/a>/, '');
  // Settings: the company/logo/bot setup stays editable after first run.
  if (page === 'settings.html' && s.indexOf('href="setup.html"') === -1) {
    s = s.replace(/(<a href="index\.html">[^<]*<\/a>)/, '$1<a href="setup.html">Company, logo &amp; bot</a>');
  }
  return s;
}
function applyRules(s, b) {
  for (const [re, rep] of rules(b)) s = s.replace(re, rep);
  return s;
}

function install(entity, extra, brandSource) {
  if (!entity || entity === 'exos') return null;
  // extra(html): optional entity sanitizer (lib/entity-pages.js) applied after rebranding.
  // brandSource(): optional live override from data/brand.json (re-read on mtime, no restart).
  return function wrap(req, res) {
    let ov = null; try { ov = brandSource ? brandSource() : null; } catch (e) { ov = null; }
    const b = brandFor(entity, ov);
    const base = (String(req.url || '').split('?')[0].split('/').pop()) || 'index.html';
    const chromeOnly = CHROME_ONLY.has(base);
    const origWriteHead = res.writeHead;
    const origEnd = res.end;
    let ctype = '';
    res.writeHead = function (code, a, h) {
      const hdrs = (a && typeof a === 'object') ? a : h;
      if (hdrs) for (const k of Object.keys(hdrs)) if (k.toLowerCase() === 'content-type') ctype = String(hdrs[k]);
      // Rewritten bodies change length — drop any precomputed Content-Length.
      if (hdrs && /text\/html|javascript/.test(ctype)) for (const k of Object.keys(hdrs)) if (k.toLowerCase() === 'content-length') delete hdrs[k];
      return origWriteHead.apply(this, arguments);
    };
    res.end = function (chunk, ...rest) {
      try {
        const ct = ctype || String(res.getHeader('Content-Type') || '');
        if (chunk != null && /text\/html|javascript/.test(ct)) {
          let out = rebrand(Buffer.isBuffer(chunk) ? chunk.toString('utf-8') : chunk, b, chromeOnly, base);
          if (extra) out = extra(out);
          // Bot name last, so the entity sanitizer's Exo-specific scrubs still match first.
          if (!chromeOnly) out = renameBot(out, b.botName);
          if (!res.headersSent) res.removeHeader('Content-Length');
          return origEnd.call(this, out, ...rest);
        }
      } catch (e) { /* never break a response over branding */ }
      return origEnd.call(this, chunk, ...rest);
    };
  };
}

module.exports = { install, rebrand, brandFor, renameBot };
