#!/usr/bin/env python3
"""
dr_verify.py — post-backup checksum verification of the Studio -> Mini DR mirror.

Right after studio_dr_backup.sh copies, this hashes a fixed set of CRITICAL files on the
Studio (source) and the same files in the Mini mirror (over ssh) and compares sha256.
Any mismatch / missing file = checksum FAIL. Result is written to
~/.openclaw/state/dr-verify.json; backup_watchdog.py alerts Jon on a FAIL.

Also exposes link_up() — a cheap 'is the Mini reachable over the DR link' probe the watchdog
uses to catch "Mini link down" (e.g. FileVault-locked after a power-loss reboot).

CLI:
  dr_verify.py --verify      # exit 0 pass, 1 fail (writes state)
  dr_verify.py --verify --heal  # on mismatch, re-copy mismatched files once + re-verify
  dr_verify.py --link        # exit 0 link up, 1 down
  dr_verify.py --status
"""
import os, sys, json, time, hashlib, subprocess

WS = "/Users/exomac/.openclaw/workspace"
HOME = os.path.expanduser("~")
STATE = os.path.join(HOME, ".openclaw", "state", "dr-verify.json")

# (source path on Studio, path relative to the mirror base)
CRITICAL = [
    (f"{HOME}/.openclaw/secrets.json",                 "openclaw-config/secrets.json"),
    (f"{HOME}/.openclaw/openclaw.json",                "openclaw-config/openclaw.json"),
    (f"{WS}/mission-control/server.js",                "workspace/mission-control/server.js"),
    (f"{WS}/config/dr-backup.json",                    "workspace/config/dr-backup.json"),
    (f"{HOME}/.cloudflared/exos-mc.yml",               "cloudflared/exos-mc.yml"),
    (f"{HOME}/.cloudflared/exos-exomac-lan.token",     "cloudflared/exos-exomac-lan.token"),
]

def _cfg():
    return json.load(open(os.path.join(WS, "config", "dr-backup.json")))

def _dest():
    c = _cfg(); d = c["dest"]
    remote = str(c.get("dest_is_remote")).lower() == "true"
    if remote:
        host, base = d.split(":", 1)
        return remote, host, base
    return remote, None, d

def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def link_up(timeout=20):
    """True if the Mini answers over the DR ssh link (BatchMode: never prompts)."""
    remote, host, _ = _dest()
    if not remote:
        return True, "local dest (self-test)"
    try:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", f"ConnectTimeout={timeout}", host, "echo ok"],
                           capture_output=True, text=True, timeout=timeout + 15)
        if r.returncode == 0 and "ok" in r.stdout:
            return True, "link up"
        return False, f"ssh rc={r.returncode} {(r.stderr or '').strip()[:120]}"
    except Exception as e:
        return False, f"ssh probe failed: {str(e)[:120]}"

def verify():
    remote, host, base = _dest()
    pairs = [(s, rel) for s, rel in CRITICAL if os.path.exists(s)]
    local = {rel: _sha(s) for s, rel in pairs}
    if remote:
        paths = " ".join(f"'{base}{rel}'" for _, rel in pairs)
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host,
                            f"shasum -a 256 {paths} 2>/dev/null"], capture_output=True, text=True, timeout=90)
        got = {}
        for ln in r.stdout.splitlines():
            parts = ln.split(None, 1)
            if len(parts) == 2:
                got[parts[1].strip()[len(base):]] = parts[0]
    else:
        got = {rel: _sha(os.path.join(base, rel)) for _, rel in pairs if os.path.exists(os.path.join(base, rel))}
    bad = [rel for rel in local if got.get(rel) != local[rel]]
    res = {"ts": int(time.time()), "ok": not bad, "checked": len(local), "mismatched": bad}
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = STATE + ".tmp"; json.dump(res, open(tmp, "w"), indent=2); os.replace(tmp, STATE)
    return res

def heal(res):
    """Race-tolerance (secrets.json is rewritten by token rotation mid-run, 10/21): re-copy ONLY
    the mismatched critical files to the mirror once, then re-verify. A persistent mismatch still FAILs."""
    remote, host, base = _dest()
    src = {rel: s for s, rel in CRITICAL}
    for rel in res.get("mismatched", []):
        if rel not in src or not os.path.exists(src[rel]):
            continue
        dst = f"{host}:{base}{rel}" if remote else os.path.join(base, rel)
        cmd = ["rsync", "-a"] + (["-e", "ssh"] if remote else []) + [src[rel], dst]
        subprocess.run(cmd, capture_output=True, timeout=120)
    return verify()

def read_state():
    try: return json.load(open(STATE))
    except Exception: return None

if __name__ == "__main__":
    a = sys.argv[1:] or ["--status"]
    if a[0] == "--verify":
        r = verify(); print(json.dumps(r))
        if not r["ok"] and "--heal" in a:
            r = heal(r); print("heal re-copy + re-verify: " + json.dumps(r))
        sys.exit(0 if r["ok"] else 1)
    if a[0] == "--link":
        ok, why = link_up(); print(("UP " if ok else "DOWN ") + why); sys.exit(0 if ok else 1)
    if a[0] == "--status":
        print(json.dumps(read_state())); sys.exit(0)
    print(__doc__); sys.exit(2)
