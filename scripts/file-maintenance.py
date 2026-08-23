#!/usr/bin/env python3
"""
FILE MAINTENANCE — deterministic weekly workspace housekeeping (replaces the LLM cron,
which had no local filesystem access). Checks stale logs, verifies key files exist and
are non-empty, and pings Discord ONLY if something needs attention (else stays quiet).
Run by launchd (com.exos.file-maintenance), Sundays 04:30.
"""
import os, time, subprocess, glob
import durable_send_shim  # noqa: F401  (durable delivery: spool-then-send)

WS = os.path.expanduser("~/.openclaw/workspace")
LOGS = os.path.join(WS, "logs")
REPORT = os.path.join(LOGS, "file-maintenance-report.txt")
OPENCLAW = "/Users/exomac/.local/share/mise/installs/node/24.14.0/bin/openclaw"
CHANNEL = "channel:1501636814849577050"
KEY_FILES = ["exos-mission-control.md", "opportunities-tracker.md", "AGENTS.md", "MEMORY.md"]
STALE_DAYS = 7
STALE_MB = 25  # only bother flagging stale logs that are also large

now = time.time()
issues, notes = [], []

# 1) key files exist and are non-empty
for f in KEY_FILES:
    p = os.path.join(WS, f)
    if not os.path.isfile(p):
        issues.append(f"MISSING key file: {f}")
    elif os.path.getsize(p) == 0:
        issues.append(f"EMPTY key file: {f}")

# 2) stale + large logs (candidates for archiving)
stale_large = []
for p in glob.glob(os.path.join(LOGS, "*")):
    try:
        if os.path.isfile(p):
            age_d = (now - os.path.getmtime(p)) / 86400
            mb = os.path.getsize(p) / 1024 / 1024
            if age_d > STALE_DAYS and mb > STALE_MB:
                stale_large.append((os.path.basename(p), round(age_d), round(mb, 1)))
    except OSError:
        pass
if stale_large:
    notes.append(f"{len(stale_large)} stale+large log(s) (>{STALE_DAYS}d, >{STALE_MB}MB) — archive candidates: "
                 + ", ".join(f"{n} ({d}d/{m}MB)" for n, d, m in stale_large[:8]))

# report (always written)
ts = time.strftime("%Y-%m-%d %H:%M")
with open(REPORT, "w") as f:
    f.write(f"File Maintenance — {ts}\nChecked: {', '.join(KEY_FILES)} + logs/\n")
    f.write("ISSUES:\n" + ("\n".join("  - " + i for i in issues) or "  none") + "\n")
    f.write("NOTES:\n" + ("\n".join("  - " + n for n in notes) or "  none") + "\n")

# ping Discord ONLY if there are real issues (stay quiet otherwise)
if issues:
    msg = f"🧹 File Maintenance ({ts}) — attention needed:\n" + "\n".join("• " + i for i in issues)
    if notes:
        msg += "\n" + "\n".join("• " + n for n in notes)
    try:
        subprocess.run([OPENCLAW, "message", "send", "--channel", "discord", "--target", CHANNEL, "-m", msg],
                       timeout=60, capture_output=True)
    except Exception:
        pass
    print("issues found:", issues)
else:
    print("MAINTENANCE_OK" + (f" ({len(stale_large)} archive candidates noted)" if stale_large else ""))
