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

function brandFor(entity) {
  if (BRANDS[entity]) return BRANDS[entity];
  const up = String(entity || '').toUpperCase();
  return { legal: up, name: up, short: up, badge: up.slice(0, 2), mtp: null };
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

// Pages that carry Exos legal templates (offer letters, NDAs with Exos's address and
// benefits). Swapping the name there would create a false SSLC document, so only the
// page chrome (title / header) is rebranded and templates stay as-is.
const CHROME_ONLY = new Set(['docusign.html']);

function rebrand(text, b, chromeOnly) {
  let s = String(text);
  if (chromeOnly) {
    return s.replace(/<title>[\s\S]*?<\/title>/i, m => applyRules(m, b));
  }
  s = applyRules(s, b);
  if (!b.mtp) s = s.replace(/<a href="mtp\.html" id="mtpBanner"[\s\S]*?<\/a>/, '');
  return s;
}
function applyRules(s, b) {
  for (const [re, rep] of rules(b)) s = s.replace(re, rep);
  return s;
}

function install(entity, extra) {
  if (!entity || entity === 'exos') return null;
  const b = brandFor(entity);
  // extra(html): optional entity sanitizer (lib/entity-pages.js) applied after rebranding.
  return function wrap(req, res) {
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
          let out = rebrand(Buffer.isBuffer(chunk) ? chunk.toString('utf-8') : chunk, b, chromeOnly);
          if (extra) out = extra(out);
          if (!res.headersSent) res.removeHeader('Content-Length');
          return origEnd.call(this, out, ...rest);
        }
      } catch (e) { /* never break a response over branding */ }
      return origEnd.call(this, chunk, ...rest);
    };
  };
}

module.exports = { install, rebrand, brandFor };
