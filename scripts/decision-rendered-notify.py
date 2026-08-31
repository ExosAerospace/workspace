#!/usr/bin/env python3
"""
decision-rendered-notify.py — notify the person waiting on a decision the moment it is rendered.

Called by server.js immediately after /api/decisions/answer saves. Args:
  --id        decision id (D-XXXX)
  --answer    the answer given (Yes / No / custom option)
  --note      optional note attached to the answer
  --by        who answered it (display name)

Resolves the "waiter" from the decision's owner field → users.json email lookup.
Only notifies @exosaero.com addresses (never external). Sends:
  1. Email via msmtp / ProtonMail Bridge
  2. Discord DM via openclaw CLI (if discord_id configured) OR skips Discord
"""

import json, os, re, shutil, subprocess, sys, argparse
from pathlib import Path

WS       = Path("/Users/exomac/.openclaw/workspace")
USERS    = WS / "mission-control" / "users.json"
DECS     = WS / "mission-control" / "data" / "decisions.json"
CFG      = WS / "config" / "decision-notify.json"
LOG      = WS / "logs" / "decision-notify.log"
MCURL    = "https://mc.exosaero.space"

OPENCLAW = shutil.which("openclaw") or \
    "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"

EMAIL_RX = re.compile(r"^[^@\s]+@exosaero\.com$", re.IGNORECASE)


# ---------- helpers ----------------------------------------------------------

def log(msg):
    try:
        with open(LOG, "a") as f:
            import time
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S %Z')}] {msg}\n")
    except Exception:
        pass


def load_json(p, default):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return default


def _subprocess_env():
    env = os.environ.copy()
    extra = [os.path.dirname(OPENCLAW),
             "/Users/exomac/.local/share/mise/shims",
             "/opt/homebrew/bin", "/usr/local/bin"]
    env["PATH"] = ":".join(extra + [env.get("PATH", "")])
    return env


# ---------- user index -------------------------------------------------------

def build_user_index():
    d = load_json(USERS, [])
    us = d if isinstance(d, list) else (d.get("users") or list(d.values()))
    by_email, by_name = {}, {}
    for u in us:
        if not isinstance(u, dict):
            continue
        e = (u.get("email") or "").strip().lower()
        n = (u.get("name") or "").strip().lower()
        if e:
            by_email[e] = u
        if n:
            by_name[n] = u
    return by_email, by_name


def resolve_waiter(owner_str, by_email, by_name):
    """
    Map the decision's owner field to an @exosaero.com email.
    Returns (email, display_name) or (None, None).
    """
    if not owner_str:
        return None, None
    o = owner_str.strip()
    # Already an internal email?
    if EMAIL_RX.match(o):
        u = by_email.get(o.lower())
        return o.lower(), (u.get("name") if u else o)
    # Name lookup
    u = by_name.get(o.lower())
    if not u:
        # Try first word / partial
        for key, val in by_name.items():
            if o.lower() in key or key in o.lower():
                u = val
                break
    if u and EMAIL_RX.match(u.get("email") or ""):
        return u["email"].strip().lower(), u.get("name") or o
    return None, None


# ---------- notification senders --------------------------------------------

def send_email(to_email, to_name, dec):
    title   = dec.get("title") or "Untitled decision"
    did     = dec.get("id") or ""
    answer  = dec.get("answer") or "(noted)"
    note    = dec.get("note") or ""
    by      = dec.get("answeredBy") or "Jon"
    context = dec.get("context") or ""
    related = dec.get("relatedItem") or ""

    body = (
        f"Hi {to_name or to_email.split('@')[0]},\n\n"
        f"A decision you were waiting on has been rendered.\n\n"
        f"Decision:  {title}\n"
        f"ID:        {did}\n"
        f"Answer:    {answer}\n"
        + (f"Note:      {note}\n" if note else "")
        + (f"Context:   {context}\n" if context else "")
        + (f"Related:   {related}\n" if related else "")
        + f"Rendered by: {by}\n\n"
        f"View in Mission Control: {MCURL}/decisions.html?focus={did}\n\n"
        f"— Exos Mission Control"
    )
    msg = (
        f"From: jquinnexo@pm.me\r\n"
        f"To: {to_email}\r\n"
        f"Subject: [Decision Rendered] {title[:80]}\r\n\r\n"
        + body.replace("\n", "\r\n")
    )
    try:
        p = subprocess.run(
            ["msmtp", "-a", "protonmail", to_email],
            input=msg.encode(), capture_output=True, timeout=60
        )
        if p.returncode == 0:
            log(f"EMAIL ok → {to_email} for {did}")
            return True
        log(f"EMAIL FAIL → {to_email} {did}: {p.stderr.decode()[:200]}")
        return False
    except Exception as e:
        log(f"EMAIL ERROR {to_email} {did}: {e}")
        return False


def send_discord(discord_id, dec):
    title  = dec.get("title") or "Untitled decision"
    did    = dec.get("id") or ""
    answer = dec.get("answer") or "(noted)"
    note   = dec.get("note") or ""
    by     = dec.get("answeredBy") or "Jon"

    text = (
        f"✅ **Decision rendered:** {title}\n"
        f"**Answer:** {answer}"
        + (f" — {note}" if note else "")
        + f"\n**Rendered by:** {by}\n"
        f"<{MCURL}/decisions.html?focus={did}>"
    )
    # Discord 2000-char cap
    if len(text) > 1900:
        text = text[:1897] + "…"
    try:
        r = subprocess.run(
            [OPENCLAW, "message", "send", "--channel", "discord",
             "--target", f"user:{discord_id}", "-m", text],
            capture_output=True, text=True, timeout=60, env=_subprocess_env()
        )
        if r.returncode == 0:
            log(f"DISCORD ok → user:{discord_id} for {did}")
            return True
        log(f"DISCORD FAIL user:{discord_id} {did}: {r.stderr[:200]}")
        return False
    except Exception as e:
        log(f"DISCORD ERROR user:{discord_id} {did}: {e}")
        return False


# ---------- main -------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", required=True)
    ap.add_argument("--answer", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--by", default="Jon")
    args = ap.parse_args()

    # Load the decision record (already answered at this point)
    decs = load_json(DECS, [])
    if isinstance(decs, dict):
        decs = decs.get("decisions", decs)
    dec = next((d for d in decs if str(d.get("id")) == str(args.id)), None)
    if not dec:
        log(f"SKIP: decision {args.id} not found")
        return

    # Merge CLI args into record snapshot so we have the rendered values
    dec = dict(dec)
    if args.answer:
        dec["answer"] = args.answer
    if args.note:
        dec["note"] = args.note
    dec["answeredBy"] = args.by

    # Resolve the waiter from the owner field
    by_email, by_name = build_user_index()
    owner_str = dec.get("owner") or ""
    to_email, to_name = resolve_waiter(owner_str, by_email, by_name)

    # Skip if no internal email or if they are the same person who answered
    answered_by_email = ""
    for k, u in by_email.items():
        if (u.get("name") or "").lower() == args.by.lower():
            answered_by_email = k
            break
    if not to_email:
        log(f"SKIP {args.id}: no internal waiter resolved (owner={owner_str!r})")
        return
    if to_email == answered_by_email:
        log(f"SKIP {args.id}: waiter is the same as answerer ({to_email})")
        return

    log(f"NOTIFY {args.id} → {to_email} (owner={owner_str!r}, answer={dec.get('answer')!r})")

    cfg      = load_json(CFG, {})
    disc_map = cfg.get("discord_ids", {})
    disc_id  = disc_map.get(to_email)

    email_ok   = send_email(to_email, to_name, dec)
    discord_ok = send_discord(disc_id, dec) if disc_id else False

    if not discord_ok and not disc_id:
        log(f"DISCORD SKIP {args.id}: no discord_id configured for {to_email}")

    log(f"DONE {args.id}: email={'ok' if email_ok else 'FAIL'} discord={'ok' if discord_ok else ('SKIP' if not disc_id else 'FAIL')}")


if __name__ == "__main__":
    main()
