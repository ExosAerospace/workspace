#!/usr/bin/env python3
"""
forwarded_mail.py — surface inbound mail Jon FORWARDS from his M365/Outlook to Proton.

Jon's real inbound (gov approvals like eRA Commons, PI replies from @purdue.edu/@uw.edu/@nih.gov,
etc.) lands in his M365 inbox, invisible to Proton IMAP. When he forwards it to jquinnexo@proton.me,
the forward's From is jquinn@exosaero.com — so inbox scanners that skip "our own address" miss it
(this hid the eRA Commons approval and Park's reply). This tool finds those forwards and extracts
the embedded original sender + subject + snippet, so a capture agent can treat them as real inbound.

Usage: python3 scripts/forwarded_mail.py [--since-days 5] [--json]
"""
import imaplib, email, re, sys, json, os
from email.header import decode_header
from datetime import datetime, timedelta

HOST, PORT, USER = "127.0.0.1", 1143, "jquinnexo@pm.me"
def _pw():
    try:
        return json.load(open(os.path.expanduser("~/.openclaw/secrets.json"))).get("protonmail_bridge_smtp_password") or "SPqYBivj98-jyF3RujLKxA"
    except Exception:
        return "SPqYBivj98-jyF3RujLKxA"
INTERNAL = ("exosaero.com", "pm.me", "proton.me")
FWD_FROM = re.compile(r'From:\s*(.+?)\s*<\s*([^>\s]+@[^>\s]+)\s*>', re.I)
JON = "jquinn@exosaero.com"

def dec(s):
    if not s: return ""
    return "".join(t.decode(e or "utf-8", "ignore") if isinstance(t, bytes) else t for t, e in decode_header(s))

def full_text(msg):
    plain = html = ""
    for p in msg.walk():
        ct = p.get_content_type()
        try: payload = p.get_payload(decode=True).decode(errors="replace")
        except Exception: continue
        if ct == "text/plain": plain += payload
        elif ct == "text/html": html += payload
    t = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</tr>", "\n", t)
    t = re.sub(r"<[^>]+>", " ", t)
    import html as _h
    t = re.sub(r"[ \t]+", " ", _h.unescape(t))
    return (plain + "\n" + t) if plain.strip() else t

def embedded_sender(body):
    for m in FWD_FROM.finditer(body):
        name, addr = m.group(1).strip().strip('"'), m.group(2).strip().lower()
        dom = addr.split("@")[-1]
        if dom not in INTERNAL and re.match(r"[^@\s]+@[^@\s]+\.[a-z]{2,}$", addr):
            # first non-internal embedded sender = the original party
            tail = body[m.end():].splitlines()
            j = 0
            while j < len(tail) and (not tail[j].strip() or re.match(r"^\s*(Sent|To|Cc|Subject|Date)\s*:", tail[j], re.I)):
                j += 1
            snip = re.sub(r"\s+", " ", " ".join(tail[j:j+6]))[:200]
            return name, addr, snip
    return None, None, re.sub(r"\s+", " ", body)[:200]

def scan(since_days=5):
    since = (datetime.utcnow() - timedelta(days=since_days)).strftime("%d-%b-%Y")
    m = imaplib.IMAP4(HOST, PORT); m.login(USER, _pw())
    out, seen = [], set()
    for folder in ['"All Mail"', "INBOX"]:
        try: m.select(folder, readonly=True)
        except Exception: continue
        typ, d = m.search(None, f'(SINCE {since} FROM "{JON}")')
        if typ != "OK" or not d or not d[0]: continue
        for uid in d[0].split():
            msg = email.message_from_bytes(m.fetch(uid, "(RFC822)")[1][0][1])
            subj = dec(msg.get("Subject"))
            if not re.match(r"^\s*(fw|fwd)\s*:", subj, re.I):  # only forwards
                continue
            mid = msg.get("Message-ID") or subj + msg.get("Date", "")
            if mid in seen: continue
            seen.add(mid)
            name, addr, snip = embedded_sender(full_text(msg))
            out.append({"id": (msg.get("Message-ID") or mid).strip(),
                        "date": msg.get("Date", ""), "subject": subj,
                        "forwarded_from": addr or "(unparsed — read manually)",
                        "forwarded_name": name or "", "snippet": snip})
    m.logout()
    out.sort(key=lambda r: r["date"], reverse=True)
    return out

def main():
    days = int(sys.argv[sys.argv.index("--since-days")+1]) if "--since-days" in sys.argv else 5
    rows = scan(days)
    if "--match" in sys.argv:
        pat = re.compile(sys.argv[sys.argv.index("--match")+1], re.I)
        rows = [r for r in rows if pat.search(r["subject"]+" "+r["forwarded_from"]+" "+r["forwarded_name"]+" "+r["snippet"])]
    if "--json" in sys.argv:
        print(json.dumps(rows, indent=2)); return
    if not rows:
        print(f"No Jon-forwarded inbound in the last {days}d."); return
    print(f"JON-FORWARDED INBOUND (last {days}d) — treat these as real inbound, not 'our own outbound':")
    for r in rows:
        print(f"\n• {r['date'][:31]}  [{r['subject'][:70]}]")
        print(f"    original sender: {r['forwarded_name']} <{r['forwarded_from']}>")
        print(f"    snippet: {r['snippet'][:160]}")

if __name__ == "__main__":
    main()
