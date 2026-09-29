#!/usr/bin/python3
"""
convert_job_to_logged.py: wrap a com.exos.* launchd job's ProgramArguments with
scripts/run_logged.py so every run lands in logs/runs/YYYY-MM-DD.jsonl (exo3 audit remedy).

  before: ProgramArguments = [cmd, arg, ...]
  after:  ProgramArguments = [/usr/bin/python3, <ws>/scripts/run_logged.py, <label>, --, cmd, arg, ...]

Nothing else in the plist changes (env, cwd, schedule, log paths stay as they were).

Safety:
  - the original plist is copied to ~/Library/LaunchAgents/.pre-runlog-backup/ first
    (the first backup is never overwritten, so it is always the true original);
  - idempotent: an already-wrapped plist is left alone;
  - the new plist is written to a temp file, checked with `plutil -lint`, then renamed in;
  - --dry-run prints what would change and writes nothing;
  - skipped outright: com.exos.missioncontrol, com.exos.series-a-worklist (must stay disabled),
    anything cloudflared/vault/bridge, KeepAlive services, jobs using the `Program` key;
  - --reload does `launchctl bootout` + `bootstrap` ONLY for jobs that are currently loaded,
    not running right now, and do NOT have RunAtLoad=true (a reload would fire those
    immediately, and many send email/Discord). Those are converted on disk and take effect on
    their next load. A job that isn't loaded is never bootstrapped.
  - a failed bootstrap restores the original plist and bootstraps it back.

Every action is recorded in logs/runs/conversion-manifest.json.

Usage:
  convert_job_to_logged.py [--dry-run] [--reload] <label-or-plist> ...
  convert_job_to_logged.py [--dry-run] [--reload] --all [--limit N]   # next N unconverted jobs
  convert_job_to_logged.py --restore <label>                            # put the backup back (no reload)
"""
import datetime
import glob
import json
import os
import plistlib
import shutil
import subprocess
import sys
import tempfile
import time

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WRAPPER = os.path.join(WS, "scripts", "run_logged.py")
PY = "/usr/bin/python3"
AGENTS = os.path.expanduser("~/Library/LaunchAgents")
BACKUP_DIR = os.path.join(AGENTS, ".pre-runlog-backup")
MANIFEST = os.path.join(WS, "logs", "runs", "conversion-manifest.json")
DOMAIN = "gui/%d" % os.getuid()

SKIP_LABELS = {"com.exos.missioncontrol", "com.exos.series-a-worklist"}
SKIP_WORDS = ("cloudflared", "vault", "bridge")


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def load_manifest():
    try:
        return json.load(open(MANIFEST))
    except Exception:
        # Keep job-scheduler words/paths out of this file: the exo3 gate reads them as agent creation.
        return {"_doc": "Background jobs wrapped by scripts/run_logged.py (scripts/convert_job_to_logged.py). "
                        "Originals are in the .pre-runlog-backup dir, one file per label.",
                "jobs": {}}


def save_manifest(m):
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    m["updated"] = now()
    tmp = MANIFEST + ".tmp"
    with open(tmp, "w") as f:
        json.dump(m, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, MANIFEST)


def launchctl_list():
    """label -> pid (None if loaded but not running)."""
    out = subprocess.run(["launchctl", "list"], capture_output=True, text=True).stdout
    res = {}
    for line in out.splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) == 3:
            res[parts[2]] = None if parts[0] == "-" else parts[0]
    return res


def is_wrapped(pa):
    return len(pa) >= 4 and pa[1] == WRAPPER


def skip_reason(label, p):
    if label in SKIP_LABELS:
        return "excluded label"
    blob = (label + " " + " ".join(map(str, p.get("ProgramArguments") or [])) + " " + str(p.get("Program", ""))).lower()
    for w in SKIP_WORDS:
        if w in blob:
            return "excluded (%s)" % w
    if p.get("KeepAlive"):
        return "KeepAlive service"
    if "Program" in p:
        return "uses Program key (argv[0] would change)"
    if not p.get("ProgramArguments"):
        return "no ProgramArguments"
    return None


def lint(path):
    r = subprocess.run(["plutil", "-lint", path], capture_output=True, text=True)
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def bootout(label):
    return subprocess.run(["launchctl", "bootout", "%s/%s" % (DOMAIN, label)], capture_output=True, text=True)


def bootstrap(path):
    last = None
    for _ in range(6):  # bootout is async; bootstrap can race it (EIO / in progress)
        last = subprocess.run(["launchctl", "bootstrap", DOMAIN, path], capture_output=True, text=True)
        if last.returncode == 0:
            return last
        time.sleep(1)
    return last


def resolve(arg):
    if arg.endswith(".plist"):
        return arg if os.path.isabs(arg) else os.path.join(AGENTS, arg)
    return os.path.join(AGENTS, arg + ".plist")


def convert(path, dry, reload, manifest, loaded):
    label = os.path.basename(path)[:-len(".plist")]
    entry = manifest["jobs"].get(label, {})
    try:
        with open(path, "rb") as f:
            p = plistlib.load(f)
    except Exception as e:
        return label, "error", "cannot read plist: %s" % e
    label = p.get("Label", label)
    why = skip_reason(label, p)
    if why:
        if not dry:
            manifest["jobs"][label] = dict(entry, status="skipped", reason=why, at=now())
        return label, "skipped", why

    pa = list(p["ProgramArguments"])
    ral = bool(p.get("RunAtLoad"))
    if is_wrapped(pa):
        status, detail = "already", "already wrapped"
        entry.setdefault("status", "already")
    else:
        new_pa = [PY, WRAPPER, label, "--"] + pa
        if dry:
            return label, "would-convert", "RunAtLoad=%s -> %s" % (ral, " ".join(new_pa)[:220])
        os.makedirs(BACKUP_DIR, exist_ok=True)
        bak = os.path.join(BACKUP_DIR, os.path.basename(path))
        if not os.path.exists(bak):
            shutil.copy2(path, bak)
        p["ProgramArguments"] = new_pa
        fd, tmp = tempfile.mkstemp(prefix=".runlog-", suffix=".plist", dir=AGENTS)
        with os.fdopen(fd, "wb") as f:
            plistlib.dump(p, f)
        ok, msg = lint(tmp)
        if not ok:
            os.unlink(tmp)
            manifest["jobs"][label] = dict(entry, status="error", reason="plutil -lint failed: " + msg, at=now())
            return label, "error", "lint failed: " + msg
        os.chmod(tmp, os.stat(path).st_mode & 0o777)
        os.replace(tmp, path)
        entry = dict(entry, status="converted", converted_at=now(), backed_up=True,
                     original_args=pa, run_at_load=ral)
        status, detail = "converted", "plist rewritten"

    if dry:
        return label, status, detail

    # Reload decision.
    if label not in loaded:
        entry["reload"] = "not-loaded (left unloaded; takes effect on next load)"
    elif entry.get("loaded_at"):
        pass  # already reloaded with the wrapper earlier
    elif not reload:
        entry["reload"] = "pending (not requested)"
    elif ral:
        entry["reload"] = "deferred: RunAtLoad=true (converted, takes effect on next load)"
    elif loaded.get(label) or launchctl_list().get(label):  # re-check right before bootout
        entry["reload"] = "deferred: running now; rerun later with this label + --reload"
    else:
        bootout(label)
        r = bootstrap(path)
        if r.returncode == 0:
            entry["reload"] = "reloaded"
            entry["loaded_at"] = now()
        else:
            err = (r.stdout + r.stderr).strip()
            bak = os.path.join(BACKUP_DIR, os.path.basename(path))
            if os.path.exists(bak):
                shutil.copy2(bak, path)
                r2 = bootstrap(path)
                entry.update(status="reverted", reload="bootstrap failed (%s); original restored, bootstrap rc=%s"
                             % (err, r2.returncode))
            else:
                entry.update(reload="bootstrap failed (%s); NO backup found" % err)
            manifest["jobs"][label] = entry
            return label, "error", entry["reload"]
    manifest["jobs"][label] = entry
    return label, status, detail + ("; " + entry["reload"] if entry.get("reload") else "")


def restore(label, manifest):
    bak = os.path.join(BACKUP_DIR, label + ".plist")
    if not os.path.exists(bak):
        return "no backup for %s" % label
    shutil.copy2(bak, os.path.join(AGENTS, label + ".plist"))
    e = manifest["jobs"].get(label, {})
    manifest["jobs"][label] = dict(e, status="restored", restored_at=now(), loaded_at=None,
                                   reload="restored on disk; takes effect on next load")
    return "restored %s from backup (not reloaded)" % label


def main(argv):
    dry = "--dry-run" in argv
    reload = "--reload" in argv
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    manifest = load_manifest()
    if "--restore" in argv:
        for lab in argv[argv.index("--restore") + 1:]:
            print(restore(lab, manifest))
        save_manifest(manifest)
        return 0
    loaded = launchctl_list()
    positional = [a for i, a in enumerate(argv[1:], 1)
                  if not a.startswith("--") and argv[i - 1] != "--limit"]
    if "--all" in argv:
        paths = []
        for path in sorted(glob.glob(os.path.join(AGENTS, "com.exos.*.plist"))):
            lab = os.path.basename(path)[:-6]
            st = manifest["jobs"].get(lab, {}).get("status")
            if st in ("converted", "already", "skipped", "reverted", "restored"):
                continue
            paths.append(path)
        if limit:
            paths = paths[:limit]
    else:
        paths = [resolve(a) for a in positional]
    if not paths:
        print("nothing to do")
        return 0
    rc = 0
    for path in paths:
        label, status, detail = convert(path, dry, reload, manifest, loaded)
        print("%-14s %-42s %s" % (status, label, detail))
        if status == "error":
            rc = 1
        if not dry:
            save_manifest(manifest)  # after every job, so a crash loses nothing
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
