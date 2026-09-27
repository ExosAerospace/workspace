#!/usr/bin/env python3
"""
utd_capstone_lead_cards.py — put each UTD capstone lead on the owning student's
Mission Control board as its own card (Supabase `tasks`, category "Payload Sales").

Why: leads lived only in tasks/blk3-payload-sales-pipeline.md, which students can't
open (they see a read-only ranked list on the capstone tracker). The AI's research and
draft outreach for each lead was invisible to them, so "move leads to READY" had no
workable path. Each card now carries what we already know, the AI's draft, and the
exact steps. The board column IS the stage: In Progress = RESEARCHING, Done = READY
(payload_sales_engine.py reads cards tagged utd-lead and overlays them on the funnel).

Idempotent: a card is keyed by its "lead:<heading prefix>" tag; existing cards are
skipped. Run: python3 scripts/utd_capstone_lead_cards.py [--dry-run] [--show N]
"""
import os, re, sys, json, argparse, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
PIPELINE = os.path.join(WS, "tasks/blk3-payload-sales-pipeline.md")
DRAFTS_FILE = os.path.join(WS, "drafts/payload-outreach-drafts.md")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
H = {"apikey": KEY, "Authorization": "Bearer " + KEY, "Content-Type": "application/json"}

STUDENTS = {
    "Roel":    ("Roel Saenz", "RCS220001@utdallas.edu"),
    "Laura":   ("Laura Granados Lopez", "LEG240001@utdallas.edu"),
    "Karan":   ("Karan Vijaya Sankar", "KXV220043@utdallas.edu"),
    "Adrian":  ("Adrian Haro", "AXH230026@utdallas.edu"),
    "Sunidhi": ("Sunidhi Mathew", "SXM220350@utdallas.edu"),
}

# (student, pipeline heading prefix, draft label or None, due, extra note)
# First two per researcher are due Thu 10/1 (the meeting); the rest Thu 10/8.
WK1, WK2 = "2026-10-01T16:59:00+00:00", "2026-10-08T16:59:00+00:00"
ASSIGN = [
    ("Laura", "LASP (Laboratory for Atmospheric", "AH", WK1, ""),
    ("Laura", "Texas A&M — Aerospace Engineering", "file:Texas A&M", WK1,
     "Two possible POCs are listed (Taminger / Karpetis) and the AI draft targets laser-diagnostics work. Decide which one person is the right contact and say why."),
    ("Laura", "Montana State University SSEL", "Q", WK2, ""),
    ("Laura", "UAH Propulsion Research Center", "AJ", WK2, ""),
    ("Laura", "University of Michigan PEPL", "AT", WK2, ""),
    ("Karan", "NASA Glenn Research Center", "S", WK1,
     "The AI flagged a possible role change for Dr. Hartwig. Confirm his current title and branch first."),
    ("Karan", "Sandia National Laboratories", "P", WK1, ""),
    ("Karan", "NRL Space Science Division (Code 7600)", "M", WK2,
     "No named person yet; the AI draft goes to Public Affairs. Your main job is to find a named branch head or PI whose work fits a suborbital flight."),
    ("Karan", "NCAR / ACOM", "AK", WK2, ""),
    ("Karan", "Space Dynamics Laboratory (SDL / USU)", "AR", WK2, ""),
    ("Adrian", "Varda Space Industries", "W", WK1,
     "Varda is a possible multiplier (partner/integrator). Note whether it could fill more than one payload slot."),
    ("Adrian", "Rhodium Scientific", "AC", WK1,
     "Rhodium is a possible multiplier: it runs experiments for biotech clients. Note how many clients it could bring."),
    ("Adrian", "Starlab Space / Voyager", "AN", WK2,
     "DUPLICATE: the pipeline also has 'Voyager Technologies (NYSE: VOYG) — Matt Magaña' with a separate draft (BC). Decide which contact is right for payload buying and say which entry should be kept."),
    ("Adrian", "BioOrbit / Dr. Katie King", "BD", WK2,
     "BioOrbit is UK-based. Public research only, same as every lead."),
    ("Adrian", "Astrobotic Technology", "AA", WK2, ""),
    ("Roel", "Firehawk Aerospace", "AM", WK2, ""),
    ("Roel", "X-Bow Launch Systems", "AX", WK2, ""),
    ("Roel", "Phase Four", "AS", WK2, ""),
]
# Sunidhi: leads the AI already marked READY that no person has checked.
QC = [
    ("UCF / Stephen W. Hawking Center", "R", WK1,
     "Check especially: 'the only one currently selling payload slots', 'fastest recover-and-refly of any U.S. option', and the launch-site claim. Can each be backed by a public source? If not, flag it."),
    ("Axiom Space — Dr. Lucie Low — TITLE CORRECTED", "K", WK1,
     "The AI has already corrected her title once. Confirm the current title."),
    ("SpaceTango (Twyman Clements) — Deepened", "F", WK2,
     "DUPLICATE: there is an older 'SpaceTango (Lexington, KY)' entry. Say which one to keep (it goes on your duplicates list, task 3140)."),
    ("Merck Research Labs — UPDATED", "J", WK2, ""),
    ("BioServe Space Technologies", "G", WK2, ""),
]

STEPS_RESEARCH = """YOUR STEPS
1. Drag this card to In Progress. That moves the lead to RESEARCHING on the tracker.
2. Check the contact. Is the person above still in that role? Check the organization's website and LinkedIn. If they have left, find who replaced them. Record name, title, and the link you used.
3. Check the program and the money. Find one current (2025-2026) public source showing the program is active, and one way they could pay for a flight: NASA Flight Opportunities, SBIR/STTR, an NIH/NSF grant, a DoD test program, or company R&D/venture money. Link both.
4. Check the draft. Compare it with the Payload User's Guide (in the EduSourced project files). No prices. Flag any claim we can't back up with a source (words like "only", "first", "fastest"). BLK3 facts to use: 135 kg payload bay, about 100-110 km altitude, a few minutes of microgravity, hardware recovered and returned in 2-3 days, Flight 2 about March 2027.
5. Post ONE note on this card with: (a) contact confirmed yes/no + link, (b) program and funding sources, (c) fit score 1-5 and why, (d) every error you found in the AI research or draft, (e) your corrected draft.
6. Drag the card to Done. That counts it as READY. Sunidhi spot-checks it within 24 hours. If she moves it back to In Progress, fix what her note says.

RULES: You do not contact anyone. Public information only. Lizi reviews and sends. Once Adrian posts the READY checklist (Tue 9/29), use it for step 6.
Why the errors matter: the errors you log in step 5(d) are the data for Karan's human-vs-AI audit, the core research question of the project. Be specific."""

STEPS_QC = """THIS LEAD IS ALREADY MARKED READY by the AI, but no person has checked it. You are the first human check.

YOUR STEPS
1. Drag this card to In Progress.
2. Check the contact: still in that role (organization site + LinkedIn)? Is the email in a public source, or did the AI guess it? Record the link.
3. Check every factual claim in the research and the draft: the program is real and current, the funding is real, and the draft's BLK3 claims match the Payload User's Guide (EduSourced files). No prices. Flag any "only / first / fastest" claim that has no source.
4. Post ONE note: PASS or FAIL, then a numbered list of every error (what the AI said, what is true, your source), then a corrected draft if anything was wrong.
5. PASS → drag to Done. FAIL → leave it In Progress and say what would fix it.
Add your error count to the running tally for Karan's AI audit (task 3133).

RULES: You do not contact anyone. Public information only. Lizi reviews and sends."""


def pipeline_text():
    return open(PIPELINE, encoding="utf-8").read()


def _blocks(t):
    for m in re.finditer(r"\n#### \d+\.\s*(.+)", t):
        end = t.find("\n#### ", m.end())
        yield m.group(1).strip(), t[m.end(): end if end > 0 else len(t)]


def find_block(t, prefix):
    """Return (heading, [blocks for the same org, oldest first]). Update entries are
    appended as new blocks with thinner fields, so fields are merged across them."""
    hits = [(h, b) for h, b in _blocks(t) if h.startswith(prefix)]
    if not hits:
        raise SystemExit(f"no pipeline block for: {prefix}")
    heading = hits[-1][0]
    root = re.split(r" — | \(", heading)[0].strip()
    same = [b for h, b in _blocks(t) if h.startswith(root)]
    return heading, same


def field(blocks, name, n=450):
    v = None
    for block in blocks:  # latest non-empty value wins
        got = _field(block, name, n)
        v = got or v
    return v


def _field(block, name, n=450):
    m = re.search(r"^- \*\*" + name + r"[^*]*:\*\*\s*(.+)", block, re.M)
    if not m:
        return None
    v = re.sub(r"\*\*", "", m.group(1)).strip()
    return v if len(v) <= n else v[:n].rsplit(" ", 1)[0] + " …"


def get_draft(t, label):
    if label is None:
        return None
    if label.startswith("file:"):
        d = open(DRAFTS_FILE, encoding="utf-8").read()
        m = re.search(r"^## " + re.escape(label[5:]) + r".*?\n(.*?)(?=\n## |\Z)", d, re.S | re.M)
        body = m.group(1) if m else None
    else:
        m = re.search(r"\*\*DRAFT " + label + r" —[^\n]*\n(.*?)(?=\n---|\n\*\*DRAFT |\n### |\Z)", t, re.S)
        body = m.group(1) if m else None
    if not body:
        return None
    lines = []
    for ln in body.splitlines():
        ln = ln.strip()
        if ln.startswith("*[") or ln.startswith("[NOTE"):  # internal routing notes
            continue
        if ln.startswith("> — ") or ln.startswith(">— ") or ln.startswith("*Status") \
                or ln == "---" or ln.startswith("John Quinn, Cofounder"):  # signature/status lines
            continue
        lines.append(re.sub(r"^> ?", "", ln))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def known(block):
    out = []
    for label, key in (("Segment", "Segment"), ("Contact", "POC"), ("Active programs", "Active programs"),
                       ("Why BLK3 fits", "Why BLK3 fits"), ("Funding", "Funding")):
        v = field(block, key)
        if v:
            out.append(f"- {label}: {v}")
    return "\n".join(out) or "- (thin record; start from the organization's website)"


def build(t, heading_prefix, label, note, qc=False):
    heading, block = find_block(t, heading_prefix)
    name = re.sub(r"\s*[⭐✅].*$", "", heading)
    name = re.sub(r"\s*— (NEW PROSPECT|UPDATED.*|TITLE CORRECTED.*|LEADERSHIP CORRECTION.*|Deepened Enrichment)$", "", name)
    name = re.sub(r"\s*— Dr\. Lucie Low$", " — Dr. Lucie Low", name).strip(" —")
    draft = get_draft(t, label)
    parts = [f"LEAD: {name}", ""]
    if note:
        parts += ["NOTE FOR THIS LEAD: " + note, ""]
    parts += ["WHAT EXO'S RESEARCH SAYS (not verified by a person yet):", known(block), ""]
    parts += ["THE AI'S DRAFT OUTREACH (never sent, not checked):",
              draft if draft else "(No draft yet. Write one in step 5.)", ""]
    parts.append(STEPS_QC if qc else STEPS_RESEARCH)
    return name, "\n".join(parts)


def existing_keys():
    req = urllib.request.Request(SB + "/tasks?select=id,tags&tags=cs.%7Butd-lead%7D", headers=H)
    rows = json.load(urllib.request.urlopen(req))
    return {t[5:]: r["id"] for r in rows for t in (r.get("tags") or []) if t.startswith("lead:")}


def insert(row):
    req = urllib.request.Request(SB + "/tasks", data=json.dumps(row).encode(), method="POST",
                                 headers={**H, "Prefer": "return=representation"})
    return json.load(urllib.request.urlopen(req))[0]["id"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=0, help="print N full card bodies")
    a = ap.parse_args()
    t = pipeline_text()
    have = existing_keys()
    jobs = [(s, p, l, d, n, False) for s, p, l, d, n in ASSIGN] + \
           [("Sunidhi", p, l, d, n, True) for p, l, d, n in QC]
    shown = 0
    for stu, prefix, label, due, note, qc in jobs:
        name, desc = build(t, prefix, label, note, qc)
        title = (f"[Lead · verify AI-READY] {name}" if qc else f"[Lead] {name} — verify + get to READY")[:200]
        if shown < a.show:
            print("=" * 80, "\n", title, "\n", desc); shown += 1
        if prefix in have:
            print(f"skip (exists #{have[prefix]}): {title}"); continue
        owner, email = STUDENTS[stu]
        row = {"title": title, "description": desc, "owner": owner, "assigned_to": owner,
               "assigned_email": email, "state": "To Do", "category": "Payload Sales",
               "due_date": due, "priority": 90 if due == WK1 else 80, "source": "exo-capstone-lead",
               "tags": ["utd-capstone", "utd-lead", "lead:" + prefix]}
        if a.dry_run:
            print(f"DRY {stu:8} {due[:10]} {title}  (draft={'yes' if 'never sent, not checked):' in desc and '(No draft yet' not in desc else 'NO'})")
        else:
            print(f"#{insert(row)} {stu:8} {due[:10]} {title}")


if __name__ == "__main__":
    sys.exit(main())
