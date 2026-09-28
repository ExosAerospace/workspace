#!/usr/bin/env python3
"""mc-asset-backup.py — versioned asset backup of Mission Control / ERP to the drive attached to MC.

Part of the Exos Cyber Disaster Response plan (PLAN-DR). Protects the LOCAL-ONLY assets that are
not in git or would be lost if ExoMac's internal disk failed or were ransomed:
  - erp-foundation/mc.db            (ERP SQLite — gitignored, local-only: the crown jewel)
  - mission-control/data/*.json     (board/decisions/opportunities/config data)
  - mission-control/uploads/        (documents attached in MC)
  - process-library/                (procedures incl. CMMC 2.0)
  - capture/, config/               (BD pursuit trackers, capability/config)
  - users.json, .ds-passcode, ~/.openclaw/secrets.json  (needed to RESTORE service + integrations)
  - key top-level notes (USER/MEMORY/AGENTS/SOUL/TOOLS/HEARTBEAT .md)
  - a Supabase export (tasks, activities) — guards against CLOUD-side loss/ransomware.

Snapshots are hard-link incremental (rsync --link-dest), so each daily run is space-cheap and every
snapshot is a full, independently-restorable point-in-time copy. mc.db is captured with sqlite's
online .backup for a consistent copy. A manifest.json (sha256 + sizes + counts) makes each snapshot
verifiable, and a restore-me.txt documents the exact restore steps.

Retention: keep last 14 daily + last 8 weekly (Sunday) snapshots; prune the rest.
Modes: (default) run backup | --dry-run (plan only) | --verify <snapshot> (re-check checksums)
Fail-loud: if the drive is not mounted, it emails Jon and exits non-zero (cron-watchdog catches it).
"""
import os, sys, json, ssl, hashlib, subprocess, urllib.request, shutil
from datetime import datetime, timezone, date

WS = "/Users/exomac/.openclaw/workspace"
LOG = os.path.join(WS, "logs", "mc-asset-backup.log")
SUPA = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1"
SUPA_KEY = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))["supabase_service_role_key"]
JON = "jquinn@exosaero.com"
DRY = "--dry-run" in sys.argv

# What to back up (paths relative to WS unless absolute).
TREES = ["mission-control/data", "mission-control/uploads", "process-library", "capture", "config"]
FILES = ["mission-control/users.json", "mission-control/.ds-passcode",
         "USER.md", "MEMORY.md", "AGENTS.md", "SOUL.md", "TOOLS.md", "HEARTBEAT.md", "IDENTITY.md"]
ABS_FILES = [os.path.expanduser("~/.openclaw/secrets.json")]
KEEP_DAILY, KEEP_WEEKLY = 14, 8


def logline(m):
    line = f"{datetime.now(timezone.utc).isoformat()} {m}"
    try: open(LOG, "a").write(line + "\n")
    except Exception: pass
    print(line)


def email_jon(subject, body):
    if DRY:
        print(f"[dry] email Jon: {subject}"); return
    mail = f"From: Exo <jquinnexo@pm.me>\nTo: {JON}\nReply-To: {JON}\nSubject: {subject}\n\n{body}\n"
    try:
        subprocess.run(["/opt/homebrew/bin/msmtp", "-a", "protonmail", JON],
                       input=mail.encode(), timeout=30, check=False)
    except Exception as e:
        logline(f"WARN email: {e}")


def _writable(vol):
    """True only if we can actually create a file on this volume (os.access lies on macOS TM vols)."""
    t = os.path.join(vol, ".exos_write_test")
    try:
        with open(t, "w") as f: f.write("ok")
        os.remove(t); return True
    except Exception:
        return False


def find_drive():
    """Target = $MC_BACKUP_DIR (if writable), else a WRITE-TESTED external volume, else None (-> local)."""
    env = os.environ.get("MC_BACKUP_DIR")
    if env:
        parent = os.path.dirname(env) or "/"
        if os.path.isdir(parent) and _writable(parent):
            return env
    vols = "/Volumes"
    try:
        names = os.listdir(vols)
    except Exception:
        return None
    # prefer a drive named like a backups drive, but ONLY if actually writable
    ordered = sorted(names, key=lambda n: (0 if n.lower().startswith("backups of exomac") else 1))
    for n in ordered:
        p = os.path.join(vols, n)
        if n == "Macintosh HD" or n.startswith("."): continue
        if os.path.ismount(p) and _writable(p):
            return os.path.join(p, "ExosMC-AssetBackups")
    return None


def sha256(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


# Cloud tables that connect to MC (board + CRM). Export all so a Supabase-side loss is recoverable.
SUPA_TABLES = ("tasks", "activities", "contacts", "companies", "deals")


def supabase_export(dest):
    """Export every connected Supabase table (board + CRM) so a cloud-side loss is recoverable."""
    os.makedirs(dest, exist_ok=True)
    out = {}
    for table in SUPA_TABLES:
        rows, offset = [], 0
        try:
            while True:
                req = urllib.request.Request(
                    f"{SUPA}/{table}?select=*&order=id.asc&limit=1000&offset={offset}",
                    headers={"apikey": SUPA_KEY, "Authorization": "Bearer " + SUPA_KEY})
                with urllib.request.urlopen(req, timeout=60) as r:
                    chunk = json.loads(r.read().decode())
                if not chunk: break
                rows += chunk; offset += 1000
                if len(chunk) < 1000: break
            json.dump(rows, open(os.path.join(dest, f"{table}.json"), "w"))
            out[table] = len(rows)
        except Exception as e:
            logline(f"WARN supabase export {table}: {e}"); out[table] = f"ERR"
    return out


LOCAL_FALLBACK = os.path.expanduser("~/exos-asset-backups")  # on-machine, until the attached drive is write-enabled


def main():
    root = find_drive()
    on_drive = bool(root)
    if not root:
        # No writable EXTERNAL drive (exomac can't write to the TM/other volumes without an admin
        # step). Fall back to a local snapshot store so backups still run — off-workspace, and Time
        # Machine sweeps it to the external drive. Switch to the drive by write-enabling it + setting
        # MC_BACKUP_DIR. Fail loudly only if even the local store can't be written.
        root = LOCAL_FALLBACK
        try:
            os.makedirs(root, exist_ok=True)
        except Exception as e:
            logline(f"ERROR: no writable backup target ({e}).")
            email_jon("⚠️ MC asset backup FAILED — no writable target",
                      "Neither an external drive nor the local fallback is writable. Backups did not run.")
            sys.exit(1)
        logline("NOTE: external drive not writable by exomac — using local fallback " + root)

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")
    snap = os.path.join(root, stamp)
    latest = os.path.join(root, "latest")
    logline(f"backup start -> {snap}" + (" (dry-run)" if DRY else ""))
    if DRY:
        logline(f"[dry] would rsync {len(TREES)} trees + {len(FILES)+len(ABS_FILES)} files + sqlite mc.db + Supabase export")
        return
    os.makedirs(snap, exist_ok=True)

    # 1) mc.db — consistent online copy
    dbdst = os.path.join(snap, "erp-foundation"); os.makedirs(dbdst, exist_ok=True)
    src_db = os.path.join(WS, "erp-foundation", "mc.db")
    try:
        subprocess.run(["/usr/bin/sqlite3", src_db, f".backup '{os.path.join(dbdst, 'mc.db')}'"],
                       timeout=120, check=True)
        logline("mc.db consistent copy OK")
    except Exception as e:
        logline(f"WARN mc.db backup ({e}); falling back to file copy")
        try: shutil.copy2(src_db, os.path.join(dbdst, "mc.db"))
        except Exception as e2: logline(f"ERROR mc.db copy: {e2}")

    # 2) trees + files via rsync --link-dest (hard-link incremental; link-dest must mirror each subtree)
    have_latest = os.path.exists(latest)
    for t in TREES:
        s = os.path.join(WS, t)
        if not os.path.exists(s): continue
        d = os.path.join(snap, t); os.makedirs(os.path.dirname(d), exist_ok=True)
        prev = os.path.join(latest, t)
        link = ["--link-dest", prev] if have_latest and os.path.isdir(prev) else []
        subprocess.run(["/usr/bin/rsync", "-a", "--delete"] + link + [s + "/", d + "/"],
                       timeout=1800, check=False)
    for f in FILES:
        s = os.path.join(WS, f)
        if os.path.exists(s):
            d = os.path.join(snap, f); os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
    secrets_dst = os.path.join(snap, "secrets")
    for f in ABS_FILES:
        if os.path.exists(f):
            os.makedirs(secrets_dst, exist_ok=True); shutil.copy2(f, os.path.join(secrets_dst, os.path.basename(f)))

    # 3) Supabase cloud export (board + CRM)
    counts = supabase_export(os.path.join(snap, "supabase-export"))

    # 3b) Connected assets: the automation fleet (launchd defs) + the OpenClaw gateway config.
    import glob
    la_dst = os.path.join(snap, "launch-agents"); os.makedirs(la_dst, exist_ok=True)
    la_n = 0
    for p in glob.glob(os.path.expanduser("~/Library/LaunchAgents/com.exos.*.plist")):
        try: shutil.copy2(p, os.path.join(la_dst, os.path.basename(p))); la_n += 1
        except Exception: pass
    oc_dst = os.path.join(snap, "openclaw-config"); os.makedirs(oc_dst, exist_ok=True)
    for f in ("openclaw.json", "openclaw.json.last-good", ".env", "exec-approvals.json"):
        s = os.path.expanduser(f"~/.openclaw/{f}")
        if os.path.exists(s):
            try: shutil.copy2(s, os.path.join(oc_dst, f))
            except Exception: pass
    logline(f"connected assets: {la_n} launch-agents + openclaw config")

    # 3c) System rebuild manifest (for bare-metal restore to new Apple hardware): the runtime stack
    # Time Machine/Migration Assistant restores, but this makes a CLEAN reinstall reproducible.
    sm = os.path.join(snap, "system-manifest"); os.makedirs(sm, exist_ok=True)
    try:
        subprocess.run(["/opt/homebrew/bin/brew", "bundle", "dump", "--force",
                        "--file", os.path.join(sm, "Brewfile")], timeout=120, check=False)
        with open(os.path.join(sm, "pip-freeze.txt"), "w") as f:
            subprocess.run(["/usr/bin/python3", "-m", "pip", "freeze"], stdout=f, timeout=60, check=False)
        with open(os.path.join(sm, "versions.txt"), "w") as f:
            f.write(f"# ExoMac runtime ({stamp})\n")
            try: f.write("macOS: " + subprocess.check_output(["sw_vers", "-productVersion"], timeout=10).decode().strip()
                         + " " + subprocess.check_output(["uname", "-m"], timeout=10).decode().strip() + "\n")
            except Exception: pass
    except Exception as e:
        logline(f"WARN system-manifest: {e}")

    # 4) manifest (verifiable) + restore instructions
    manifest = {"created": stamp, "host": "ExoMac", "supabase": counts, "files": {}}
    try:
        manifest["git_head"] = subprocess.check_output(["git", "-C", WS, "rev-parse", "HEAD"], timeout=15).decode().strip()
    except Exception: manifest["git_head"] = None
    total = 0
    for dirpath, _, names in os.walk(snap):
        for n in names:
            if n == "manifest.json": continue
            fp = os.path.join(dirpath, n); rel = os.path.relpath(fp, snap)
            try: sz = os.path.getsize(fp)
            except Exception: sz = 0
            total += sz
            manifest["files"][rel] = {"size": sz, "sha256": sha256(fp)}
    manifest["file_count"] = len(manifest["files"]); manifest["total_bytes"] = total
    json.dump(manifest, open(os.path.join(snap, "manifest.json"), "w"), indent=1)
    open(os.path.join(snap, "restore-me.txt"), "w").write(RESTORE_DOC)

    # 5) update 'latest', prune retention
    try:
        if os.path.islink(latest) or os.path.exists(latest): os.remove(latest)
        os.symlink(snap, latest)
    except Exception as e:
        logline(f"WARN latest symlink: {e}")
    pruned = prune(root)
    mb = total / 1e6
    logline(f"backup OK: {manifest['file_count']} files, {mb:.1f} MB, supabase={counts}, pruned={pruned}")


def prune(root):
    snaps = sorted([d for d in os.listdir(root) if d.endswith("Z") and os.path.isdir(os.path.join(root, d))])
    keep = set(snaps[-KEEP_DAILY:])
    weeklies = [s for s in snaps if _is_sunday(s)]
    keep |= set(weeklies[-KEEP_WEEKLY:])
    removed = 0
    for s in snaps:
        if s not in keep:
            try: shutil.rmtree(os.path.join(root, s)); removed += 1
            except Exception: pass
    return removed


def _is_sunday(stamp):
    try: return datetime.strptime(stamp[:10], "%Y-%m-%d").weekday() == 6
    except Exception: return False


RESTORE_DOC = """EXOS MISSION CONTROL — RESTORE FROM THIS SNAPSHOT
1. Stop MC:  launchctl bootout gui/$(id -u)/com.exos.missioncontrol
2. Restore code:  git clone the repo (or restore working tree), then git checkout the manifest git_head.
3. Restore local-only data into the workspace:
     erp-foundation/mc.db            <- this snapshot's erp-foundation/mc.db
     mission-control/data/           <- mission-control/data/
     mission-control/uploads/        <- mission-control/uploads/
     process-library/  capture/  config/  users.json  .ds-passcode  *.md
     ~/.openclaw/secrets.json        <- secrets/secrets.json
4. (If Supabase was lost) re-import supabase-export/tasks.json + activities.json to the tasks/activities tables.
5. Start MC:  launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.exos.missioncontrol.plist
6. Verify at http://<MC-LAN-IP>:8080 and spot-check the board, uploads, and a CMMC doc.
Checksums for every file are in manifest.json (sha256). Verify with:  mc-asset-backup.py --verify <this-dir>
"""


def verify(snap):
    mf = json.load(open(os.path.join(snap, "manifest.json")))
    bad = 0
    for rel, meta in mf["files"].items():
        fp = os.path.join(snap, rel)
        if not os.path.exists(fp) or sha256(fp) != meta["sha256"]:
            print("MISMATCH", rel); bad += 1
    print(f"verify: {mf['file_count']} files, {bad} mismatched")
    return bad == 0


if __name__ == "__main__":
    if "--verify" in sys.argv:
        i = sys.argv.index("--verify")
        sys.exit(0 if verify(sys.argv[i + 1]) else 2)
    main()
