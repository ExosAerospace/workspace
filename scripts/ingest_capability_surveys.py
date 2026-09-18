#!/usr/bin/env python3
"""
Capability-survey auto-ingest. Scans the Proton inbox for team survey replies (they were landing
uncaptured — Phil's + Kyle's sat for days), parses the 1-5 domain ratings, and updates
config/capability-matrix.json so a completed survey flips to 'complete' automatically.

Conservative: only auto-completes a member when it parses >=8 of 13 domains; anything thinner is
flagged for manual review (Discord), never blindly written. Never overwrites an already-complete
member. Idempotent (tracks processed message-ids).

Run:  python3 scripts/ingest_capability_surveys.py            # dry-run (show parse)
      python3 scripts/ingest_capability_surveys.py --apply
"""
import imaplib, email, json, os, re, sys, subprocess
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)
from email.utils import getaddresses

WS = os.path.expanduser("~/.openclaw/workspace")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
MATRIX = os.path.join(WS, "config", "capability-matrix.json")
# Dashboard/RSI read this stale copy; keep it in lockstep with the canonical config file.
MIRROR = os.path.join(WS, "mission-control", "data", "capability-matrix.json")
STATE = os.path.join(WS, "logs", "survey-ingest-state.json")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
JON = "1501632195163590739"
APPLY = "--apply" in sys.argv

# domain key -> keyword regex (first standalone 1-5 after the keyword is the rating)
DOMAINS = [
    ("propulsion", r"propulsion|\brdre\b|engines?\b"),
    ("structures_tanks", r"structures?|composites?|\bips\b|tanks?"),
    ("avionics_gnc", r"avionics|\bgnc\b|sensors?"),
    ("flight_software", r"flight\s*software|embedded"),
    ("test_integration_launchops", r"test.{0,3}integration|range\s*&?\s*launch|launch\s*ops"),
    ("manufacturing_supply", r"manufactur|production|supply\s*chain"),
    ("business_development", r"business\s*development|capture|partnerships"),
    ("proposals_contracts", r"proposals?\s*(?:&|and)?\s*contracts?|sbir|sttr|tacfi"),
    ("finance_accounting", r"finance|accounting|quickbooks"),
    ("regulatory_faa_export", r"regulatory|faa\s*licens|itar|export"),
    ("program_management", r"program\s*/?\s*project\s*management|project\s*management"),
    ("investor_relations", r"investor\s*relations|capital\s*raise"),
    ("it_automation", r"\bit\b,?\s*data|data,?\s*systems|systems,?\s*automation|automation"),
]


def load(p, d):
    try: return json.load(open(p))
    except Exception: return d


def body_text(msg, cap=8000):
    plain, html = [], []
    for p in (msg.walk() if msg.is_multipart() else [msg]):
        try: payload = p.get_payload(decode=True).decode(errors="replace")
        except Exception: continue
        if p.get_content_type() == "text/plain": plain.append(payload)
        elif p.get_content_type() == "text/html": html.append(payload)
    t = "\n".join(plain).strip()
    if not t and html:
        t = re.sub(r"(?s)<[^>]+>", " ", "\n".join(html)); import html as H; t = H.unescape(t)
    return re.sub(r"[ \t]+", " ", t)[:cap]


def parse_ratings(body):
    """For each domain, find its keyword then the first standalone 1-5 within ~60 chars."""
    out = {}
    low = body.lower()
    for key, kw in DOMAINS:
        m = re.search(kw, low)
        if not m:
            continue
        window = low[m.end(): m.end() + 60]
        r = re.search(r"\b([1-5])\b", window)   # first single digit 1-5 (won't match 25, 30, etc.)
        if r:
            out[key] = int(r.group(1))
    return out


def alert(text):
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", JON, "-m", text],
                       timeout=60, capture_output=True)
    except Exception:
        pass


def main():
    pw = load(SECRETS, {}).get("protonmail_bridge_smtp_password")
    if not pw:
        print("no proton password"); return
    matrix = load(MATRIX, {})
    members = matrix.get("members", {})
    seen = set(load(STATE, {}).get("seen", []))
    m = imaplib.IMAP4("127.0.0.1", 1143); m.login("jquinnexo@pm.me", pw); m.select("INBOX")
    _s, data = m.search(None, "SINCE", "01-Jul-2026")
    ids = (data[0].split() if data and data[0] else [])
    captured, review = [], []
    for num in ids:
        _s, d = m.fetch(num, "(RFC822)")
        if not d or not d[0]:
            continue
        msg = email.message_from_bytes(d[0][1])
        mid = msg.get("Message-ID", "").strip()
        subj = str(email.header.make_header(email.header.decode_header(msg.get("Subject", ""))))
        frm = (getaddresses(msg.get_all("From", []) or [])[0][1] or "").lower()
        if not mid or mid in seen or not frm.endswith("@exosaero.com"):
            continue
        body = body_text(msg)
        if not re.search(r"capability survey|survey responses", subj + " " + body, re.I):
            continue
        seen.add(mid)
        # already complete? skip (don't clobber verified data)
        if members.get(frm, {}).get("status") == "complete":
            continue
        ratings = parse_ratings(body)
        if len(ratings) >= 8:
            captured.append((frm, subj, ratings))
            if APPLY:
                ent = members.setdefault(frm, {"name": frm.split("@")[0], "role": "", "special": [], "superpowers": []})
                ent["status"] = "complete"; ent["ratings"] = ratings
                ent["constraint"] = (ent.get("constraint", "") + " [auto-ingested from survey email; spot-check qualitative fields]").strip()
                matrix["missing_surveys"] = [x for x in matrix.get("missing_surveys", []) if x != frm]
        else:
            review.append((frm, subj, len(ratings)))
    m.logout()

    if APPLY and captured:
        matrix["updated"] = "auto"
        json.dump(matrix, open(MATRIX, "w"), indent=2)
    # Self-heal: mirror canonical matrix to the dashboard/RSI copy every apply run,
    # so the two paths can never silently diverge (root cause of the 'lost answers' scare).
    if APPLY:
        json.dump(matrix, open(MIRROR, "w"), indent=2)
    print(f"{'captured' if APPLY else 'would capture'}: {len(captured)} | needs manual review: {len(review)}")
    for f, s, r in captured:
        print(f"  ✓ {f}: {len(r)} domains — {s[:50]}")
    for f, s, n in review:
        print(f"  ⚠ {f}: only {n} domains parsed — {s[:50]}")
    if APPLY and (captured or review):
        json.dump({"seen": list(seen)[-3000:]}, open(STATE, "w"))
        msg = ""
        if captured: msg += f"📋 Auto-ingested {len(captured)} capability survey(s): " + ", ".join(f.split('@')[0] for f, _, _ in captured) + ". "
        if review: msg += f"⚠️ {len(review)} survey(s) need manual review (thin parse): " + ", ".join(f.split('@')[0] for f, _, _ in review) + "."
        alert(msg)


if __name__ == "__main__":
    main()
