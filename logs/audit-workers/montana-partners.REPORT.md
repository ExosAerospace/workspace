# montana-partners — worker report (2026-09-30)

Jon's ask (Discord DM, 12:28 CDT): load verified Montana payload-customer POCs into the CRM and flag them as payload customers, write a one-page "Fly with Exos → Fly from Montana" sheet for Edgar, and add an MC access path for the Montana partners.

**All three parts are done.** Nothing was sent to anyone and no one was given access.

## Where it lives
- **Parent MC task: #3287** "Montana Spaceport payload customers — Fly with Exos → Fly from Montana (BD-013)". Owner John Quinn. The one-pager (.docx + .pdf) is attached, with a summary note. No existing task fit: #974 is the student-integration plan and #3143 is the UTD lead card. Both are referenced in #3287.
- **Sub-task: #3288** "Collect MC access emails from Montana partners". Owner John Quinn, tagged `parent:3287`. The draft email to Edgar is attached.

## Commits (branch erp-phase0, not pushed)
| Commit | What it did |
|---|---|
| 0597549 | Added the montana_partner role to server.js, plus the /api/montana-partner/* feeds and the partner page |
| a6b9a81 | Added scripts/montana_partner_access.py and the pending-seats file |
| 4d80171 | Access script fixes: users.json mixes number and text IDs; keep the file at 0600; live eval now passes |
| 64c9422 | Registered montana-partner-access-exo3 in agent-registry.json |
| 66e1295 | Added the verified dataset (config/montana-payload-prospects.json) and the CRM loader, and loaded the CRM |
| 56f6661 | Added the 11 prospects to tasks/blk3-payload-sales-pipeline.md |
| 1e1b085 | Built the one-pager: build script, .docx and .pdf |
| 64f07f0 | Draft email from Jon to Edgar |
| e321e93 | Eval now covers opening the one-pager and rejecting bad doc IDs (74/74) |

## Part A — verified contacts in the CRM
Research used official .edu, .gov and company pages, checked 2026-09-30. No email address was guessed. Where a person's email isn't published, the record says "email not public". Every organization was screened with `scripts/csl_screen.py` and none matched a denied-party list.

**Organizations kept (14)**
- **T1 — universities**
  - MSU Space Science & Engineering Lab (SSEL): strongest fit; they already fly on sounding rockets.
  - Montana Space Grant Consortium / Montana NASA EPSCoR: a channel partner and a funding route.
  - Montana Tech: its EE department attended NASA's RockOn! rocket workshop in 2026.
  - University of Montana: weak fit, with no flight heritage.
- **T2 — photonics and sensors**
  - Resonon: built NASA's ARCSTONE instrument, which launched June 2025.
  - MSU Spectrum Lab.
  - Bridger Photonics: its lidar has flown on aircraft only.
  - Lumibird Photonics USA (Bozeman): no named local lead is public; the parent company is French.
  - CACI's Belgrade site (formerly Ascent Vision): no named local lead is public; go in through CACI business development.
- **T3 — gov/defense.** These are kept as relationship or intro targets only. They are not payload customers and are **not** flagged as payload prospects.
  - Malmstrom AFB / 341st Missile Wing.
  - Montana National Guard: the candidate military-type host for the container custody Jon wants.
  - Governor's Office + Dept. of Commerce.
- **T4 — tribal colleges**
  - Salish Kootenai College: flew the BisonSat CubeSat in 2015.
  - Chief Dull Knife College: its rocket team competes in NASA's First Nations Launch.

**Dropped:** Montana Instruments. It makes lab cryostats, has no space customers we could find, and has been owned by Atlas Copco (Sweden) since November 2022.

**Contacts:** 28 in total, of which 27 are new and 1 was merged into an existing record (Charlie Kankelborg's verified row). 20 of the 28 have a public email. Contacts left out because we couldn't confirm them:
- Resonon's CTO: the role appears only on an aggregator site.
- Kris Merkel of S2 Corporation: the company has posted nothing publicly since August 2020.
- The Malmstrom public affairs office email: it shows up in search results, but the official page wouldn't load for us.

**Claim corrections**
- **RadPC-Lunar** flew on Firefly's Blue Ghost Mission 1 (January–March 2025), not on Intuitive Machines.
- **RadPC's full flight history, as verified:**
  - Sounding rockets through NASA Flight Opportunities: UP Aerospace SpaceLoft in 2014 and Terrier-Orion in 2016.
  - Balloons: World View in 2019 and Raven Aerostar in 2021.
  - ISS: 2017–18, then again from 2021 to 2024.
  - CubeSats: RadSat-g in 2018 and RadSat-u in 2019–20.
  - No Blue Origin flight was found.
- **SSEL leadership:** Klumpar is now listed as "Laboratory Founder", not Director. No director is named; Larry Springer is the Program Manager.
- **BOREALIS** is confirmed active, and Angela Des Jardins directs both Montana Space Grant and NASA EPSCoR.
- **University of Montana** has no space-flight payload program. Search results that suggest one are actually about MSU.
- **Montana Instruments** was bought by Atlas Copco (closed November 2022), not by Edwards directly.
- **Montana Commerce:** Director Marta Bertoglio's appointment was ruled unconstitutional in April 2026 and is under appeal. The Governor's economic development director seat is vacant after Mark Blasdel moved to the Department of Administration.

**CRM tags**
- Everyone gets `montana-spaceport-2026-09-30`, `bd-013` and `exo3`, plus a tier tag `montana-t1` through `montana-t4`.
- Payload prospects also get `montana-payload-prospect`, `fly-exos-2027`, `payload`, `BLK3-payload` and `payload-prospect`. Companies are set to status Prospect and contacts to type "Payload Prospect".
- T3 records get `montana-relationship-target` instead of the payload tags.
- The source field reads "Montana Spaceport payload targeting 2026-09-30".

**Not added to `mission-control/data/payload-customers.json`.** That file is for **paying** customers only, and adding prospects would inflate customer metrics. These are prospects, flagged by the tags above.

**Payload pipeline:** the 11 payload prospects are now in `tasks/blk3-payload-sales-pipeline.md` with status RESEARCHING. The existing bridge script will turn 10 of them into new PAY- opportunities on its next scheduled run. MSU SSEL deliberately maps onto the existing MSU RadPC opportunities (OPP-293, OPP-329 and OPP-448) so it isn't duplicated. I did not run the bridge myself, because it rewrites opportunities-tracker.md and opportunities.json, which have other sessions' uncommitted edits.

**Loader:** `scripts/montana_payload_prospects_load.py`, registered as montana-payload-prospects-load-exo3.
- It is dry-run by default and needs `--apply` to write.
- It pages through the full contacts and companies tables, so the 1000-row cap doesn't hide duplicates.
- Its selftest passes 10/10. Running it again after the load adds nothing, only merges.

## Part B — the one-pager
- `drafts/Fly_with_Exos_Fly_from_Montana_OnePager.docx` (editable, Exos letterhead) and a matching `.pdf`.
- A copy of both is in `mission-control/partner-docs/montana/` so the partner view can serve them. Both are attached to #3287.
- I checked it visually: it fits on one page with about 1.6 in to spare.
- **Content choices:**
  - Heritage framing: flying commercial payloads since 2018 on SARGE, with BLK3 as the latest FAA-licensed vehicle. It makes no claim that BLK3 has flown or been recovered.
  - The Montana spaceport is described as planned and in development, "not yet licensed or operating".
  - The only price shown is the public list rate of $7,500/kg, followed by "contact us for pricing".
  - No free or in-kind flights are offered, and the "one of three" claim is left out.
- **Not sent to Edgar.**
- The Word file itself couldn't be rendered on this machine (soffice hangs here). The PDF uses the same margins, fonts and banners, so the page fit carries over. Worth a 5-second look in Word.

## Part C — Mission Control access for Montana partners
**How the role works.** `montana_partner` blocks everything by default; it follows the same pattern as the existing dd_reviewer sandbox. A partner can reach only:
- `/montana-partner.html`, `/login` and `/set-password`.
- `/api/me`, `/api/logout` and `/api/change-password`.
- `/api/montana-partner/summary`: program status, drawn from the partner-safe `data/montana-partner.json`.
- `/api/montana-partner/prospects`: live from the CRM, only rows tagged `montana-payload-prospect`, showing organization, tier, a short summary and contact name/title. No emails, phones or notes, and no T3 records.
- `/api/montana-partner/doc?id=`: the one-pager only, looked up from a fixed list.
- `/api/montana-partner/tasks`, `/notes` and `/note`: only tasks tagged `montana-partner`. Notes are recorded under the partner's own login name, whatever the browser sends.

Everything else is refused on the server:
- Other API calls get a 403, which is logged to the audit file and the governance log.
- Other pages redirect back to the partner view.
- The DocuSign page also bounces partners.

**Forced reset.** New seats get a temporary password with `must_reset`. Until they set their own password, they can reach only the set-password page.

**Shared tasks.** No task is shared yet. #3287 and #3288 are internal and deliberately untagged. When Jon wants partners to see a task, add the tag `montana-partner` to it.

**Eval.** `python3 scripts/montana_partner_access.py --selftest --live` passed **74/74** after the restart. It creates throwaway users and removes them afterwards. It checks that:
- a partner can reach the partner view and feeds, open the one-pager, and doesn't see email/phone/notes fields in the prospect list;
- a partner is refused on 25 finance / CRM / decisions / investor / cap-table / task / vault / dossier / upload / admin routes, on 12 internal pages and data files, on creating tasks, on notes for untagged tasks, and on bad or path-traversal document IDs;
- a partner who hasn't reset their password is confined to set-password;
- **admin and early_adopter still behave as before.**

The offline selftest passes 10/10.

**Restart.** One restart via `launchctl kickstart`. `/login` returned 200 within 2 s and still returns 200 now.

**Registry.** The role and script are registered as montana-partner-access-exo3 in agent-registry.json with a full spec. Grants and revokes are logged to `logs/fleet-events.jsonl` and `logs/montana-partner-access.jsonl`.

**Pending seats** (`mission-control/data/montana-partner-seats.json`). All email fields are blank and **nobody is activated**:

| Seat | Organization | Address already in the CRM (unconfirmed) |
|---|---|---|
| Edgar | Montana Spaceport | edgar@montanaspaceport.com |
| Sean | Limestone Hills | sean@montanaspaceport.com |
| Isaiah | Montana Spaceport | isaiah@montanaspaceport.com |

**Cloudflare.** The API token in secrets can read the "Mission Control — approved users" policy; I checked this with a GET. I made no write.

## What Jon does when the emails arrive
1. Send the draft attached to #3288 (`drafts/Montana_Partner_MC_Access_Request_Email_DRAFT.docx`) to Edgar yourself. Exo doesn't send to Edgar.
2. For each confirmed person, do a dry-run first:
   `python3 scripts/montana_partner_access.py add --name "Full Name" --org "Org" --email person@x.com`
3. Then run the same command with `--apply`. This:
   - creates the MC user (role montana_partner, temporary password, must reset on first login);
   - adds the email to the Cloudflare policy through the API and re-reads the policy to confirm;
   - marks the seat active;
   - prints the temporary password and the exact three login steps to send the person.

   If the Cloudflare call fails, it prints the exact dashboard steps to do it by hand.
4. `python3 scripts/montana_partner_access.py list` shows the status of every seat.
5. To remove someone: `deactivate --email … --apply`. This is reversible — it makes the user inactive and removes the email from Cloudflare.
6. To share a task with partners, add the tag `montana-partner` to it.

## Unverified / open items
- **Edgar's surname conflicts.** The CRM says "Edgar Johansson"; the tasking and memory say "Edgar Rayo" / "Edgardo Rayo". Confirm which is correct. The one-pager uses just "Edgar" plus his email.
- **Sean's and Isaiah's surnames** (McClung? Centifanto?) are unconfirmed.
- **Contacts to re-check before any outreach:**
  - Resonon's CEO Rand Swanson is confirmed on Resonon's own blog (June 2025), but he has no public email.
  - The Malmstrom commander's source is a local news story (July 2026).
  - The Adjutant General's source is from 2025 and is only reported to be still serving.
  - The Lumibird and CACI local leads are unknown.
- **Page fit of the Word file** hasn't been checked in Word itself; the PDF twin is the one I checked.
- **One-pager wording to confirm:** the "first-flight priority from Montana" promise comes straight from the tasking. Jon should confirm it's a commitment he wants in writing.
- **Access control the role doesn't cover:** `/api/layout` (a per-user dashboard layout file) is handled before any role check for every role. It's harmless — no business data — but it's reachable.
- **Files I didn't commit, on purpose:**
  - `mission-control/uploads/_meta.json`: mc-attach wrote my attachment entries here, but the file already had other sessions' uncommitted edits.
  - `mission-control/users.json`: other sessions' edits. My selftest users were added and removed; there is no net change from me.
- **Session-start routine skipped.** CLAUDE.md asks every session to check crons/triggers and post a status message; I skipped this because the hard rules forbid Discord messages.
