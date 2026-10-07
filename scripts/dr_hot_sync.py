#!/usr/bin/python3
"""
dr_hot_sync.py — 5-minute hot-state sync Studio -> Mini DR mirror (Jon 2026-10-02, item 2).

The hourly studio_dr_backup.sh copies the whole working tree. This job keeps the small,
fast-changing set that a failover needs to be near-seamless fresh every 5 minutes
(target RPO 5 min; MC logins survive a failover):

  mission-control/sessions.json, users.json, .public-url
  mission-control/data/*.json + *.jsonl  (decisions, tasks, ... — NOT the *-snapshot-* / .bak files)
  erp-foundation/mc.db                   (WAL db -> sqlite3 .backup to a temp file first = consistent copy)
  mission-control/uploads/               (delta only, never deletes on the mirror)

Lands in the same paths under <dest>/workspace/ so the mirror stays one coherent tree, then writes
<dest>/.hot-sync-stamp.json (epoch, duration, bytes) for failover_validate / failover_monitor.

Fenced = no-op: if this Studio has lost the control lease (Mini promoted) it must not push
stale state over the mirror. Single-flight lock. Telemetry: fleet_log + ~/.openclaw/state/hot-sync.json.
Python 3.9 compatible.

Usage: dr_hot_sync.py [--dry-run]
"""
import os, sys, json, time, glob, shutil, subprocess, tempfile, fcntl

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
HOME = os.path.expanduser("~")
STATE_DIR = os.path.join(HOME, ".openclaw", "state")
STATE = os.path.join(STATE_DIR, "hot-sync.json")
LOCK = os.path.join(STATE_DIR, "hot-sync.lock")
FENCE_FLAG = os.path.join(STATE_DIR, "server-fenced.flag")
LOG = os.path.join(WS, "logs", "dr-hot-sync.log")
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=20"]


def logline(s):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), s)
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def fleet(outcome, detail):
    try:
        import fleet_log
        fleet_log.event("dr-hot-sync", "govern", "sync", detail=detail, owner="John Quinn",
                        outcome=outcome, level="info" if outcome == "ok" else "warn")
    except Exception:
        pass


def fenced():
    if os.path.exists(FENCE_FLAG):
        return True, "server-fenced flag set"
    try:
        st = json.load(open(os.path.join(STATE_DIR, "control-lease-local.json")))
        if st.get("holder") == "mini":
            return True, "control lease held by the Mini (promoted)"
    except Exception:
        pass
    return False, ""


def hot_files():
    mc = os.path.join(WS, "mission-control")
    files = []
    for rel in ("sessions.json", "users.json", ".public-url"):
        if os.path.exists(os.path.join(mc, rel)):
            files.append("mission-control/" + rel)
    for pat in ("data/*.json", "data/*.jsonl"):
        for p in sorted(glob.glob(os.path.join(mc, pat))):
            b = os.path.basename(p)
            if "-snapshot-" in b or ".bak" in b:
                continue
            files.append("mission-control/data/" + b)
    return files


def main():
    dry = "--dry-run" in sys.argv[1:]
    cfg = json.load(open(os.path.join(WS, "config", "dr-backup.json")))
    dest = cfg["dest"]
    remote = str(cfg.get("dest_is_remote")).lower() == "true"
    os.makedirs(STATE_DIR, exist_ok=True)

    f, why = fenced()
    if f:
        logline("SKIP — fenced (%s)" % why); fleet("skipped", {"reason": why}); return 0

    lockf = open(LOCK, "w")
    try:
        fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        logline("another hot sync is running; exit"); return 0

    t0 = time.time()
    files = hot_files()
    tmpdir = tempfile.mkdtemp(prefix="hotsync-")
    rc_all = 0
    try:
        # consistent copy of the WAL-mode ERP db
        db = os.path.join(WS, "erp-foundation", "mc.db")
        stage_db = os.path.join(tmpdir, "workspace", "erp-foundation", "mc.db")
        os.makedirs(os.path.dirname(stage_db))
        r = subprocess.run(["/usr/bin/sqlite3", db, ".timeout 15000", ".backup '%s'" % stage_db],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            logline("WARN sqlite .backup failed rc=%s %s" % (r.returncode, r.stderr.strip()[:200])); rc_all = r.returncode

        if remote:
            host, base = dest.split(":", 1)
            target = dest + "workspace/"
            rsh = "ssh " + " ".join(SSH_OPTS)
        else:
            host, base = None, dest
            target = os.path.join(dest, "workspace") + "/"
        listfile = os.path.join(tmpdir, "files.txt")
        with open(listfile, "w") as lf:
            lf.write("\n".join(files) + "\n")

        cmds = [
            ["rsync", "-a", "--files-from=" + listfile, WS + "/", target],
            ["rsync", "-a", os.path.join(tmpdir, "workspace") + "/", target],
            ["rsync", "-a", "--exclude=.DS_Store", os.path.join(WS, "mission-control", "uploads") + "/",
             target + "mission-control/uploads/"],
        ]
        if r.returncode != 0:
            cmds.pop(1)
        stats = []
        for c in cmds:
            if remote:
                c = c[:1] + ["-e", rsh, "--stats"] + c[1:]
            else:
                c = c[:1] + ["--stats"] + c[1:]
                os.makedirs(c[-1], exist_ok=True)
            if dry:
                c.insert(1, "-n")
            p = subprocess.run(c, capture_output=True, text=True, timeout=600)
            if p.returncode == 255 and remote and not dry:   # SSH transport blip (banner timeout / closed): retry once
                logline("WARN rsync rc=255 (ssh): %s — retrying in 20s" % p.stderr.strip()[:160])
                time.sleep(20)
                p = subprocess.run(c, capture_output=True, text=True, timeout=600)
            sent = [ln for ln in p.stdout.splitlines() if ln.startswith("Total bytes sent") or ln.startswith("Total sent:")]
            stats.append(sent[0].split(":", 1)[1].strip() if sent else "?")
            if p.returncode not in (0, 23, 24):
                rc_all = p.returncode
                logline("WARN rsync rc=%s: %s" % (p.returncode, p.stderr.strip()[:300]))
        dur = round(time.time() - t0, 1)
        stamp = {"epoch": int(time.time()), "duration_s": dur, "files": len(files),
                 "bytes_sent": stats, "ok": rc_all == 0, "host": os.uname().nodename}
        if not dry:
            sp = os.path.join(tmpdir, ".hot-sync-stamp.json")
            json.dump(stamp, open(sp, "w"))
            if remote:
                subprocess.run(["rsync", "-a", "-e", rsh, sp, dest + ".hot-sync-stamp.json"],
                               capture_output=True, timeout=60)
            else:
                shutil.copy(sp, os.path.join(dest, ".hot-sync-stamp.json"))
            if rc_all == 0:
                json.dump(stamp, open(STATE + ".tmp", "w")); os.replace(STATE + ".tmp", STATE)
        logline("%s files=%d dur=%ss sent=%s rc=%s" % ("DRY" if dry else "OK" if rc_all == 0 else "FAIL",
                                                   len(files), dur, stats, rc_all))
        fleet("ok" if rc_all == 0 else "error", stamp)
        if rc_all != 0 and not dry:
            # Exit non-zero (→ agent_eval FAIL page) only when the RPO is actually at risk: last successful
            # sync older than 3x the 5-min target. A single transient SSH blip stays a logged WARN (10/7).
            try:
                last_ok = json.load(open(STATE)).get("epoch", 0)
            except Exception:
                last_ok = 0
            if time.time() - last_ok < 900:
                logline("WARN transient failure; last good sync %ds ago (< 15 min) — not escalating" % (time.time() - last_ok))
                return 0
        return 0 if rc_all == 0 else 1
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
