# Assets

Brand assets — logo, imagery, favicons — are dropped **here by Exos**. Students
should not add or replace brand imagery without Exos direction.

## Rules

- **Keep filenames stable.** `index.html` and future components reference assets by
  filename. Renaming a file breaks references, so replace-in-place rather than
  rename.
- **Public, export-safe imagery only.** No controlled/ITAR-restricted photos, no
  CUI, no unreleased hardware imagery. When unsure, ask Exos in the PR.
- **Optimize before committing.** Prefer compressed, web-sized images (SVG for the
  logo where possible; sized/compressed JPG or WebP for photos).

## Expected files (populated by Exos)

- `logo.svg` — primary SPACEavailable…™ / Exos wordmark or logo
- `favicon.ico` (or `favicon.svg`)
- `hero.jpg` / `hero.webp` — optional hero background imagery
- Additional segment or environment imagery as Exos provides it

Reference assets from `index.html` with stable relative paths, e.g.
`assets/logo.svg`.
