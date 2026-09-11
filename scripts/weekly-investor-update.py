#!/usr/bin/env python3
"""WEEKLY INVESTOR UPDATE prep for Lizi.

Every Wednesday (launchd, 08:00 CT) this:
  1. Compiles a DRAFT weekly investor update from the investor milestone-capture feed
     (reports/monthly-report-capture-YYYY-MM.md — the same feed the monthly report uses),
     pulling entries from the last 7 days.
  2. Saves the draft to reports/weekly-investor-update-YYYY-MM-DD.md.
  3. Emails the draft to Lizi (lquinn@exosaero.com) for review.
  4. Posts an MC task assigned to Lizi ("Weekly Investor Update — review & send to David")
     so it shows up in her Mission Control.

Lizi reviews/edits, then forwards to David to email out to investors.

Run:  python3 scripts/weekly-investor-update.py            # gated: only fires on Wednesday
      python3 scripts/weekly-investor-update.py --force    # run now regardless of weekday
      python3 scripts/weekly-investor-update.py --force --dry  # build + print, no email/task
"""
import os, sys, re, json, datetime, subprocess, urllib.request

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
B = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"
LIZI = "lquinn@exosaero.com"
FORCE = "--force" in sys.argv
DRY = "--dry" in sys.argv


def _k():
    return json.load(open(SECRETS))["supabase_service_role_key"]


def sb_post(table, row):
    k = _k()
    r = urllib.request.Request(
        B + table, data=json.dumps(row).encode(),
        headers={"apikey": k, "Authorization": "Bearer " + k,
                 "Content-Type": "application/json", "Prefer": "return=representation"},
        method="POST")
    return json.loads(urllib.request.urlopen(r, timeout=30).read())


def recent_milestones(days=7):
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=days)
    months = {today.strftime("%Y-%m"),
              (today.replace(day=1) - datetime.timedelta(days=1)).strftime("%Y-%m")}
    entries = []
    for month in months:
        path = os.path.join(WS, "reports", f"monthly-report-capture-{month}.md")
        if not os.path.exists(path):
            continue
        text = open(path, encoding="utf-8").read()
        matches = list(re.finditer(r'(?m)^#{2,}\s+(\d{4}-\d{2}-\d{2})\b(.*)$', text))
        for i, m in enumerate(matches):
            try:
                d = datetime.date.fromisoformat(m.group(1))
            except ValueError:
                continue
            if d < cutoff:
                continue
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end].strip()
            title = m.group(2).strip(" —-–").strip()
            entries.append((d, title, body))
    entries.sort(key=lambda x: x[0], reverse=True)
    return entries


def _parse_iso(s):
    try:
        return datetime.date.fromisoformat((s or "")[:10])
    except Exception:
        return None


def recent_pipeline(days=7):
    """Real momentum in the last N days, from durable sources:
       (A) Supabase CRM contacts advanced to Engaged/Won/etc. and touched this week, and
       (B) opportunities.json entries in a strong deal/proposal status (submitted/won/contract).
       The MC opp board is regenerated nightly, so CRM contacts are the reliable source for
       engaged relationships; the opp scan only picks up strong proposal/deal statuses."""
    today = datetime.date.today()
    cutoff = today - datetime.timedelta(days=days)
    items = []

    # (A) Supabase CRM — engaged/advancing contacts touched this week
    try:
        k = _k()
        q = ("contacts?select=name,organization,stage,last_contacted,next_action"
             "&stage=in.(Engaged,Won,Contracted,Verbal)"
             f"&last_contacted=gte.{cutoff.isoformat()}"
             "&order=last_contacted.desc&limit=15")
        req = urllib.request.Request(B + q, headers={"apikey": k, "Authorization": "Bearer " + k})
        rows = json.loads(urllib.request.urlopen(req, timeout=30).read())
        for r in rows:
            dd = _parse_iso(r.get("last_contacted")) or today
            org, name = (r.get("organization") or "").strip(), (r.get("name") or "").strip()
            label = f"{org} — {name}" if org and name else (org or name)
            detail = re.sub(r'\*\*|__|`', '', (r.get("next_action") or "")).split(". ")[0][:180]
            items.append((dd, f"{label} [{r.get('stage')}]", detail))
    except Exception as e:
        print("pipeline CRM source failed:", e)

    # (B) opportunities.json — strong proposal/deal statuses only (e.g. gov proposals)
    STRONG = ("submitted", "won", "contract", "verbal", "booked", "signed", "closed won")
    try:
        opps = json.load(open(os.path.join(WS, "mission-control", "data", "opportunities.json"),
                               encoding="utf-8")).get("opportunities", [])
    except Exception:
        opps = []
    for o in opps:
        st = (o.get("status", "") or "").lower()
        if not any(g in st for g in STRONG):
            continue
        blob = f"{o.get('next_action','')} {o.get('description','')}"
        dts = [d for d in (_parse_iso(x) for x in re.findall(r'\b\d{4}-\d{2}-\d{2}\b', blob)) if d]
        recent = max((d for d in dts if d >= cutoff), default=None)
        if not recent:
            continue
        title = re.sub(r'\s+—\s+(ENGAGED|WON|SUBMITTED|DRAFT).*$', '', o.get("title", "")).strip()
        na = re.sub(r'^\d{4}-\d{2}-\d{2}:\s*', '', (o.get("next_action", "") or ""))
        na = re.sub(r'\*\*|__|`', '', na).split(". ")[0][:180]
        items.append((recent, f"{title} [{o.get('status', '').strip()}]", na))

    seen, out = set(), []
    for d, label, detail in sorted(items, key=lambda x: x[0], reverse=True):
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append((d, label, detail))
    return out[:10]


def build_draft(today):
    ms = recent_milestones(7)
    L = [f"Exos Aerospace — Weekly Investor Update", f"{today:%B %d, %Y}", "",
         "DRAFT for review. Verify all figures and framing before forwarding to David to send.",
         "", "Hello all,", "",
         "Here is this week's update on progress at Exos Aerospace.", "",
         "Highlights this week:"]
    if ms:
        def clean(s):
            return re.sub(r'\*\*|__|`|\*', '', s).strip()
        for d, title, body in ms:
            head = clean(title) if title else "Update"
            L.append(f"\n• {head} ({d:%b %d})")
            for ln in body.splitlines():
                ln = ln.strip()
                if not ln.startswith(("-", "*", "•")):
                    continue
                ln = clean(ln.lstrip("-*• ").strip())
                if not ln or ln.lower().startswith(("source:", "[")):
                    continue
                L.append("   - " + ln)
    else:
        L.append("\n• No major new milestones logged in the capture feed this week. "
                 "Steady execution on the Series A raise, the BLK3 build toward the "
                 "Q1/Q2 2027 flights, and payload/partnership pipeline development. "
                 "[Lizi: add anything from this week before sending.]")
    # Pipeline movement intentionally excluded — investor update carries only solidified
    # items (logged milestones / closed or committed events), not in-progress conversations.
    # (recent_pipeline() retained below if a "signed/closed" section is ever wanted.)

    L += ["", "Standing status (confirm/update as needed before sending):",
          "• Series A: raise open (Scorpius ROFR, RDRE development, BLK4).",
          "• BLK3: first two flights targeted Q1/Q2 2027; NASA IDIQ on-ramp anticipated mid-2027.",
          "• Pipeline: active payload and partnership discussions in progress.",
          "",
          "Thank you, and please reach out with any questions.", "",
          "— The Exos Team", ""]
    return "\n".join(L)


def main():
    today = datetime.date.today()
    if not (FORCE or today.weekday() == 2):   # 2 = Wednesday
        print(f"{today} is not Wednesday — skipping."); return
    draft = build_draft(today)

    # 1) save
    out = os.path.join(WS, "reports", f"weekly-investor-update-{today.isoformat()}.md")
    if not DRY:
        open(out, "w", encoding="utf-8").write(draft)
        print("saved", out)

    # 2) email to Lizi
    from email.message import EmailMessage
    body = (f"Hi Lizi,\n\nHere is this week's DRAFT investor update, ready for your review. "
            f"Edit as needed, then forward to David to email out to investors.\n\n"
            f"{'-'*60}\n{draft}\n{'-'*60}\n\nA copy of this task is in your Mission Control.\n\n— Exo\n")
    m = EmailMessage()
    m["From"] = "Exo <jquinnexo@pm.me>"
    m["To"] = LIZI
    m["Subject"] = f"Weekly Investor Update — ready for review ({today:%b %d})"
    m.set_content(body)
    if not DRY:
        try:
            subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", LIZI],
                           input=m.as_bytes(), check=True, timeout=60)
            print("emailed", LIZI)
        except Exception as e:
            print("email failed:", e)

    # 3) MC task assigned to Lizi
    # issue counter -> each week's task auto-closes on ITS OWN send (match-subject:issue #N),
    # so a prior week's send can never prematurely close the current one.
    _issue_f = os.path.expanduser("~/.openclaw/workspace/logs/investor-update-issue.txt")
    try: _last = int(open(_issue_f).read().strip())
    except Exception: _last = 8
    issue_no = _last + 1
    if not DRY:
        try: open(_issue_f, "w").write(str(issue_no))
        except Exception: pass
    task = {
        "title": f"Weekly Investor Update (Issue #{issue_no}) — review & send to David ({today:%b %d})",
        "owner": "Lizi Quinn", "assigned_to": "Lizi Quinn", "assigned_email": LIZI,
        "state": "To Do", "priority": 80,
        "due_date": today.isoformat() + "T00:00:00+00:00",
        "category": "Investor Relations",
        "source": "weekly-investor-update.py (Wed auto-prep)",
        "tags": ["investor-update", "weekly", "capital", "exo3", "autoclose-on-send", f"match-subject:issue #{issue_no}"],
        "description": ("Weekly investor update prepared and emailed to you for review.\n"
                        "Review/edit, then forward to David to email out to investors.\n\n"
                        "----- DRAFT -----\n" + draft),
    }
    if not DRY:
        try:
            created = sb_post("tasks", task)
            print("MC task created #", created[0].get("id"))
        except Exception as e:
            print("task post failed:", e)

    if DRY:
        print("\n===== DRAFT PREVIEW (dry run) =====\n")
        print(draft)


if __name__ == "__main__":
    main()
