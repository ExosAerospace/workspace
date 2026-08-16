# Deploy

The SPACEavailable…™ microsite is a **static site** — plain HTML, inline CSS, and a
JSON content file. There is **no server-side code to run**, which keeps the attack
surface minimal.

## Intended hosting

- **Static hosting behind Cloudflare.** Serve the files as-is from a static host
  fronted by Cloudflare (CDN + TLS + WAF). No application server, no runtime, no
  database.
- **No server-side execution.** The host serves files only. The `/api/lead`
  endpoint in the contact form is a placeholder; lead-capture wiring is TODO and, if
  added, should be an isolated serverless/edge function or a third-party form
  service — not a general server.
- **Immutable deploys.** Each deploy is a distinct, immutable build/version. Nothing
  is edited in place on production.
- **Instant rollback.** Because deploys are immutable and versioned, reverting to a
  previous good version is immediate if a change causes a problem.

## Flow

1. Students open a PR (see `README.md`).
2. Exos reviewer (**Lizi**) approves for accuracy, positioning, and export safety.
3. Approved change deploys as a new immutable version.
4. If needed, roll back instantly to the prior version.

## Staging

- **Stage privately first.** Deploy new versions to a private/preview URL for Exos
  review before anything goes public.
- **Then publish to a public subdomain of `exosaero.com`** (e.g. a
  `spaceavailable.` or campaign subdomain). **Final host and subdomain are TBD by
  Jon.**

## Guardrails at deploy time

- Only publish content that cleared Exos review (see the Public-claim guardrail in
  `README.md`).
- Public, non-export-restricted content only.
- Keep the brand mark exact: **SPACEavailable…™** (one word, trailing ellipsis, ™).
