#!/usr/bin/env python3
"""
weekly_blocked_senders_update.py — Weekly blocked-senders list refresh.

Run by launchd every Monday morning. Calls gen_blocked_senders.py to rebuild
Blocked_Senders_Current.txt from the latest failed-DD registry, then DMs Jon
on Discord with a summary. No external sends; no auto-deployment to the tenant
(that apply step routes through John per the standing gov-tenant admin rule).
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "email-blocklist", "blocked_senders_manifest.json")
BLOCKLIST = os.path.join(ROOT, "email-blocklist", "Blocked_Senders_Current.txt")
GENERATOR = os.path.join(ROOT, "scripts", "gen_blocked_senders.py")

JON_USER_ID = "1501632195163590739"


def dm_jon(msg: str):
    """Send a Discord DM to Jon via openclaw CLI. Non-fatal if unavailable."""
    ocw = shutil.which("openclaw")
    candidates = ([ocw] if ocw else []) + [
        "/Users/exomac/.local/share/mise/installs/node/lts/bin/openclaw",
        "/Users/exomac/.local/share/mise/installs/node/lts-krypton/bin/openclaw",
    ]
    for cand in candidates:
        if cand and os.path.exists(cand):
            try:
                env = dict(os.environ)
                env["PATH"] = os.path.dirname(cand) + ":/opt/homebrew/bin:/usr/local/bin:" + env.get("PATH", "")
                r = subprocess.run(
                    [cand, "message", "send", "--channel", "discord", "--target", JON_USER_ID, "-m", msg],
                    capture_output=True, text=True, timeout=60, env=env
                )
                if r.returncode == 0:
                    return
            except Exception as e:
                print(f"[warn] Discord DM failed via {cand}: {e}")
    print("[warn] Discord DM: no openclaw binary found; message not delivered")


def main():
    print(f"[weekly_blocked_senders_update] start {datetime.now().isoformat()}")

    # Regenerate
    result = subprocess.run(
        [sys.executable, GENERATOR],
        capture_output=True, text=True, cwd=ROOT
    )
    if result.returncode != 0:
        err = (result.stderr or result.stdout or "unknown error")[:400]
        dm_jon(f"⚠️ **Blocked-senders weekly update FAILED.**\n```\n{err}\n```")
        print("[error]", err)
        return 1

    # Read manifest
    manifest = {}
    if os.path.exists(MANIFEST):
        try:
            manifest = json.load(open(MANIFEST))
        except Exception:
            pass

    active = manifest.get("active_count", "?")
    held   = manifest.get("held_count", 0)
    held_domains = manifest.get("held", [])
    stamp  = manifest.get("generated", datetime.now().strftime("%Y-%m-%d"))

    summary = (
        f"**Blocked-Senders List Updated** — {stamp}\n"
        f"• **{active}** domains/addresses active (blocking company-wide)\n"
        f"• **{held}** held for your review before org-wide block"
        + (f": {', '.join(f'`{d}`' for d in held_domains)}" if held_domains else "")
        + f"\n\nFile ready: `email-blocklist/Blocked_Senders_Current.txt`\n"
        f"• **peaton's Outlook updater:** point it at that file — works as-is.\n"
        f"• **Company-wide (GCC High tenant):** run `Deploy-Exos-Blocked-Senders-Tenant.ps1` "
        f"on a Windows PC with Exchange Online Management module. One-time run applies to all mailboxes."
    )

    dm_jon(summary)
    print("[weekly_blocked_senders_update] done.", result.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
