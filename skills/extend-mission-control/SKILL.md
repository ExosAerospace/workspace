---
name: "extend-mission-control"
description: "Safely extend Mission Control pages — add edit panels, filters/sorts, close-out — with edits that survive the markdown/Supabase→JSON regeneration."
---

# Extend Mission Control (safely)

Playbook for adding capability to the Exos Mission Control web app (edit panels, filters, sorts,
close-out actions) **without losing edits** when the data regenerates.

## The one thing that will bite you
MC pages are static HTML served by `mission-control/server.js`, rendering from
`mission-control/data/*.json`. Those JSON files are **regenerated** by
`scripts/dashboard-data-generator.py` (launchd `com.exos.dashboard-data-refresh`) from source
markdown (`opportunities-tracker.md`, `SERIES_A_SCORED_CRM.md`) or Supabase. **Editing a
`data/*.json` file directly gets clobbered on the next run.** All persistence goes through an
**overrides layer** the generator applies on top.

Also: **Supabase/PostgREST caps every REST response at 1000 rows** regardless of `limit=`.
Always paginate with `&order=id&limit=1000&offset=N` until a short page.

## Pattern A — add a click-to-open detail/edit panel to a page
1. **Rows clickable:** add `style="cursor:pointer" onclick="if(!event.target.closest('a'))openXDetail('${id}')"`
   to the row template (encode ids with special chars via `encodeURIComponent`).
2. **Panel:** slide-in `<div>` + backdrop; reuse the `.opp-panel` CSS classes already in
   `opportunities.html`. Fields = the columns you want editable.
3. **Server endpoint** in `server.js` (near the other `/api/...` handlers): `POST /api/x/update`,
   **session-gated** (`const s=getSession(req); if(!s) return 401`). It (a) merges the fields into
   `mission-control/data/x-overrides.json` keyed by a **stable id** (OPP id, firm name, task id),
   and (b) patches the live `x.json` so the edit reflects immediately. Restart server after:
   `launchctl kickstart -k gui/$(id -u)/com.exos.missioncontrol`.
4. **Generator:** after it builds the list (post-parse, pre-`write_json`), load `x-overrides.json`
   and apply each patch onto the matching record (skip keys starting with `_`).
5. **Save JS:** `POST` the fields, on success `Object.assign(current, fields); renderActive();` and
   show a save message.

## Pattern B — add filters / sorts to the board
1. Add `<select>`/`<button>` controls to the toolbar.
2. Extend `getFilteredTasks()` (each filter reads its control and `.filter(...)`).
3. For a new sort, add a `sortByX` flag + toggle (make sort toggles mutually exclusive) and a
   branch in `render()`'s `.sort(...)`. Thresholds must match the card badges (e.g. priority
   HIGH >=80, MED 50-79).
4. HTML changes are live on reload (no restart). **Always syntax-check the inline JS** — a JS error
   blanks the whole board:
   ```
   python3 -c "import re;h=open('mission-control/index.html').read();open('/tmp/b.js','w').write('\n;\n'.join(re.findall(r'<script>(.*?)</script>',h,re.S)))"
   node --check /tmp/b.js
   ```

## Pattern C — close-out + side effects (e.g. failed-DD)
A "Close out — outcome" control sets `status='CLOSED — <outcome>'` + `closed:true` (via override),
appends a dated comment to notes; the board hides closed by default with a "Show closed" toggle.
Outcome "Failed DD" also calls `scripts/failed_dd.py add --firm ... --email ... --domain ...`
(via `execFileSync` in the endpoint) so the party is recognized do-not-engage across Exos.

## Always verify persistence end-to-end (the real test)
```
# write a sentinel override, regenerate, confirm it survives, then clean up
echo '{"OPP-050":{"status":"SENTINEL"}}' > mission-control/data/opportunity-overrides.json
python3 scripts/dashboard-data-generator.py | grep overrides
python3 -c "import json;print([o['status'] for o in json.load(open('mission-control/data/opportunities.json'))['opportunities'] if o['id']=='OPP-050'])"
rm mission-control/data/opportunity-overrides.json && python3 scripts/dashboard-data-generator.py
```

## Delivery / recurring jobs
Deterministic recurring work → **launchd** plist under `~/Library/LaunchAgents/com.exos.*`
(`StartInterval` or `StartCalendarInterval`), not LLM crons. DM Jon via
`openclaw message send --channel discord --target <JON_ID> -m "..."`.

## Gotchas checklist
- Never edit `data/*.json` directly — use the overrides file.
- Key overrides by a **stable** id (firm name for CRM; OPP/FUND/BD id for opps; task id for tasks).
- Paginate Supabase (1000-row cap) — silent data loss otherwise.
- Endpoint changes need a server restart; HTML/JS changes need only a reload.
- After a fetch that was blind to a backlog, a state-driven job can flood — baseline its state first.
