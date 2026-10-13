#!/usr/bin/env python3
"""
dd_blocklist_monthly.py — regenerate the Exos DD-Blocked Senders list from the DD engine
and email the refreshed list + Outlook-rule instructions to all employees. Backs procedure
IT-002 (Monthly DD-Blocked Senders — Outlook Rule Update).

Sources (status==fail): mission-control/data/dd-registry.json, config/failed-dd-registry.json,
mission-control/data/supplier-dd-registry.json.
Excludes: shared free-email providers (blocking the domain would kill legit mail) + the
explicit config/dd-block-exclusions.json list (active contacts John chose not to block).

Run:  python3 scripts/dd_blocklist_monthly.py           # generate + send to all employees
      python3 scripts/dd_blocklist_monthly.py --dry     # preview only, no send
Scheduled monthly via launchd com.exos.dd-blocklist-monthly.
"""
import json, os, sys, subprocess, datetime, shutil
from email.message import EmailMessage
from email.utils import formatdate

WS = os.path.expanduser("~/.openclaw/workspace")
DRY = "--dry" in sys.argv
# launchd PATH lacks /opt/homebrew/bin — resolve msmtp absolutely (10/1 run died: FileNotFoundError msmtp).
MSMTP = shutil.which("msmtp") or next((x for x in ("/opt/homebrew/bin/msmtp", "/usr/local/bin/msmtp") if os.path.exists(x)), "msmtp")
FROM = "jquinnexo@pm.me"
FREE = {"protonmail.com","proton.me","pm.me","sbcglobal.net","gmail.com","yahoo.com","ymail.com",
 "outlook.com","hotmail.com","live.com","msn.com","aol.com","icloud.com","me.com","mac.com",
 "gmx.com","mail.com","zoho.com","att.net","comcast.net","verizon.net","cox.net"}

def load(p):
    try: return json.load(open(os.path.join(WS, p)))
    except Exception: return {}

def failed_domains():
    fails = set()
    for f in ["mission-control/data/dd-registry.json","mission-control/data/supplier-dd-registry.json"]:
        d = load(f)
        items = d.items() if isinstance(d, dict) else [((x.get("domain") or x.get("email")), x) for x in d]
        for k, v in items:
            st = (v.get("status") if isinstance(v, dict) else "") or ""
            if str(st).lower() in ("fail","failed","blocked","do-not-engage","blackball") and isinstance(k, str) and "." in k:
                fails.add(k.lower())
    # config/failed-dd-registry.json is {"entities":[{firm, domains[], verdict}]} — the generic loop above
    # silently skipped it, so ~45 do-not-engage domains never reached the company list (10/13, Phil).
    for e in load("config/failed-dd-registry.json").get("entities", []):
        if e.get("verdict") == "do-not-engage":
            fails.update(str(x).lower() for x in (e.get("domains") or []))
    # Same safety as the canonical list: never block a bare gov/edu/mil domain or a REVIEW_HOLD firm.
    sys.path.insert(0, os.path.join(WS, "scripts"))
    from gen_blocked_senders import norm, is_protected_gov_edu, REVIEW_HOLD
    return {n for n in map(norm, fails) if n and "@" not in n and not is_protected_gov_edu(n) and n not in REVIEW_HOLD}

def employees():
    d = load("mission-control/users.json")
    users = d if isinstance(d, list) else d.get("users", [])
    return sorted({(u.get("email") or "").lower() for u in users
                   if (u.get("email") or "").lower().endswith("@exosaero.com") and u.get("role") != "early_adopter"})

def main():
    excl = set(load("config/dd-block-exclusions.json").get("exclude_domains", []))
    fails = failed_domains()
    block = sorted(d for d in fails if d not in FREE and d not in excl)
    today = datetime.date.today().isoformat()
    open(os.path.join(WS, f"drafts/DD_Blocked_Senders_{today}.txt"), "w").write("\n".join(block) + "\n")
    dom = ";".join(block)
    copilot = ('Create an Outlook inbox rule named "Exos DD-Blocked Senders". Apply it to incoming mail: '
        'if the sender\'s email address contains ANY of the domains listed below, permanently delete the message '
        '(or move it to Junk Email). Turn the rule on after creating it and confirm it is done. If a rule with that '
        'name already exists, add any missing domains to it instead of creating a duplicate. If you cannot create the '
        'rule directly, give me the exact click-by-click steps for both new Outlook (web) and classic Outlook desktop.\n\n'
        'Domains: ' + dom)
    open(os.path.join(WS, f"drafts/DD_Copilot_Prompt_{today}.txt"), "w").write(copilot + "\n")
    recips = employees()
    body = f"""Team,

Monthly refresh of the Exos DD-Blocked Senders list. These are senders that FAILED our automated due-diligence screen — scam "investors," OFAC/SAM/SEC-flagged and debarred entities, and spoofed domains. Please keep your Outlook rule current so this mail is auto-removed from your inbox.

FULL PROCEDURE: IT-002 "Monthly DD-Blocked Senders — Outlook Rule Update" in the Mission Control Process Library (Security / CUI).

EASIEST — LET COPILOT DO IT: open Microsoft 365 Copilot (or Copilot in Outlook) and paste the prompt below. It creates/updates the rule for you. First time and every monthly refresh, just paste the latest version of this prompt.

----- COPILOT PROMPT (paste this) -----
{copilot}
----- END COPILOT PROMPT -----

OR DO IT MANUALLY —
FIRST TIME (create the rule):
- Windows desktop Outlook: Home > Rules > Manage Rules & Alerts > New Rule > "Apply rule on messages I receive" > check "with specific words in the sender's address" > add the domains below > action "delete it" (or move to Junk) > name it "Exos DD-Blocked Senders."
- Outlook on the web / New Outlook: Settings (gear) > Mail > Rules > Add new rule > condition "Sender address includes" > add the domains below > action Delete (or Move to Junk) > Save.

MONTHLY (update the rule): open the "Exos DD-Blocked Senders" rule and ADD the new domains below to the same condition. Don't remove existing entries.

BLOCKLIST ({len(block)} domains) — copy/paste:
{dom}

CAUTIONS:
- If you're expecting mail from a listed party, check Junk/Deleted before it clears, and tell Exo.
- Never block a free-provider domain (gmail.com, proton, sbcglobal.net, yahoo.com, etc.) wholesale — block the specific ADDRESS instead.

Questions - reply to me.
- Exo, for Exos Aerospace (at John's direction)
"""
    print(f"blocklist: {len(block)} domains | excluded (free): {sorted(fails & FREE)} | excluded (policy): {sorted(fails & excl)}")
    print(f"recipients: {len(recips)} -> {', '.join(recips)}")
    if DRY:
        print("--- DRY: not sending ---"); return
    m = EmailMessage(); m["From"] = FROM; m["To"] = ", ".join(recips); m["Date"] = formatdate(localtime=True)
    m["Subject"] = f"Exos DD-Blocked Senders — monthly update ({today}) — keep your Outlook rule current (IT-002)"
    m.set_content(body)
    att = os.path.join(WS, f"drafts/DD_Blocked_Senders_{today}.txt")
    with open(att, "rb") as f:
        m.add_attachment(f.read(), maintype="text", subtype="plain", filename=f"Exos_DD_Blocked_Senders_{today}.txt")
    p = subprocess.run([MSMTP, "--timeout=60", "-a", "default", *recips], input=m.as_bytes(), capture_output=True)
    print("send:", "rc " + str(p.returncode), (p.stderr.decode()[:200] or "OK"))

if __name__ == "__main__":
    main()
