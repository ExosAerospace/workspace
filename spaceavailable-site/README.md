# SPACEavailable…™ — Payload-Sales Microsite

A static marketing microsite for Exos Aerospace's **SPACEavailable…™** payload-sales
campaign, maintained by UTD capstone students under a review-before-deploy (PR-gated)
workflow.

## The model

- **Static site.** Plain HTML + inline CSS. No server-side code, no database, no
  CMS, no admin panel. Minimal attack surface.
- **Content-as-data.** All copy lives in [`content/site.json`](content/site.json).
  The page renders from that file. To change words, edit the JSON — not the markup.
- **Components** (page structure/styling) live in [`index.html`](index.html).
- **Every change is a reviewable diff.** Students edit versioned files and open a
  pull request. Nothing is edited live in production.
- **Exos reviews and deploys.** An Exos reviewer (**Lizi**) approves the PR and
  triggers the deploy. Students never write to production directly.

```
spaceavailable-site/
├── README.md            ← this file
├── DEPLOY.md            ← how it ships (Cloudflare static hosting)
├── index.html           ← the page (components + inline CSS)
├── content/
│   └── site.json        ← all copy (content-as-data) — edit this
└── assets/
    └── README.md        ← where Exos drops brand assets
```

## How to propose a change

1. **Branch.** Create a feature branch off the current default branch.
2. **Edit files.**
   - Copy changes → edit `content/site.json`.
   - Layout/style/new sections → edit `index.html`.
   - Imagery/logo → coordinate with Exos; assets land in `assets/` (see
     `assets/README.md`).
3. **Preview locally.** Serve the folder over HTTP so the `fetch` of `site.json`
   works, e.g. `python3 -m http.server` from this directory, then open the shown
   URL. (Opening `index.html` directly via `file://` still renders, using the
   hardcoded fallback copy, but won't reflect `site.json` edits.)
4. **Open a pull request.** Describe what changed and why. Keep PRs small and
   focused so the diff is easy to review.
5. **Exos review.** Lizi reviews for accuracy, positioning, and export safety,
   then approves and deploys. Address requested changes in the same PR.
6. **No direct production writes.** Merges to the deploy branch happen only after
   Exos approval.

## Public-claim guardrail

Any copy that names or characterizes Exos capabilities **must pass Exos review**
before it can ship. Positioning rules (non-negotiable):

- **Heritage:** Exos has been **flying since 2018**. Never say or imply "first
  commercial flight" or that a first flight is still ahead.
- **Identity:** Include, where capability is described, that Exos is **"one of only
  three FAA-licensed reusable rocket launch providers in the US."**
- **No overstatement.** Don't claim relationships, customers, or results that
  aren't confirmed. Don't use unprovable absolutes ("world's first," "only," "never
  before"). Hedge to what's documented.
- **Flight status:** BLK3 holds an FAA license but has **not flown commercially** —
  never claim it is flying commercially. Flight 2 payload capacity is an **upcoming**
  opportunity (targeted early 2027), not a completed flight.
- **Brand mark:** The campaign name is **SPACEavailable…™** — one word, with a
  trailing ellipsis and the ™ symbol. Never split it, never drop the ellipsis or ™,
  never spell-correct or "fix" it.
- **Export/data safety:** Public, non-export-restricted information only. No CUI,
  no controlled technical data, no customer PII beyond a voluntary contact form.
  Specs on this site come from the **published Payload User Guide**; do not add
  specs beyond what Exos has published.

When in doubt, leave the claim out and ask Exos in the PR.
