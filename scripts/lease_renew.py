#!/usr/bin/python3
"""
lease_renew.py — STUDIO side of the control lease (launchd com.exos.lease-renew, every 60 s).

Each run:
  1. read the lease from Supabase; studio_decide() -> renew / reclaim / fence
  2. write the renewal (+ re-read verify: if the Mini's 'mini' landed at the same moment we fence)
  3. push a heartbeat to the Mini over the exos-mini link (independent path #1 for failover_monitor)
  4. enforce the fence:
       LIVE     -> write ~/.openclaw/state/server-fenced.flag (run_logged.py then skips every
                   non-exempt com.exos job = send-crons/state-mutating jobs stand down) and
                   launchctl bootout the exos-mc + lan-tunnel connectors (+ the OpenClaw gateway
                   when the lease is LOST to the Mini). Unfence (partition healed, lease still ours)
                   removes the flag and bootstraps the connectors again.
       DRY-RUN  -> only records what it WOULD do (~/.openclaw/state/server-fence-dryrun.json).
  5. telemetry: ~/.openclaw/state/control-lease-local.json, logs/lease-renew.log, fleet_log
     (agent=lease-renew) on every state change.

Never takes the lease back from holder=mini — failback is manual (failover_hold.py --failback).
Usage: lease_renew.py [--status]
"""
import os, sys, json, time, subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import control_lease as cl

LOCAL = os.path.join(cl.STATE_DIR, "control-lease-local.json")
DRY = os.path.join(cl.STATE_DIR, "server-fence-dryrun.json")
LOG = os.path.join(cl.WS, "logs", "lease-renew.log")
UID = str(os.getuid())


def logline(s):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), s)
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def push_heartbeat(cfg, now):
    p = cfg["heartbeat_file_on_mini"]
    try:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "mini-dr",
                            "echo %d > '%s.tmp' && mv '%s.tmp' '%s'" % (int(now), p, p, p)],
                           capture_output=True, timeout=25)
        return r.returncode == 0
    except Exception:
        return False


def _loaded(label):
    return subprocess.run(["launchctl", "print", "gui/%s/%s" % (UID, label)], capture_output=True).returncode == 0


def enforce(cfg, fenced, reason, live):
    labels = list(cfg["studio_fence_labels"])
    if reason == "lease-lost":
        labels += cfg.get("studio_fence_labels_when_lease_lost", [])
    if not live:
        prev = cl.read_json(DRY, {})
        if bool(prev.get("would_fence")) != fenced:
            logline("[dry-run] WOULD %s: %s (%s)" % ("FENCE" if fenced else "UNFENCE", labels, reason))
        cl.write_json(DRY, {"would_fence": fenced, "reason": reason, "labels": labels, "ts": int(time.time())})
        return
    if fenced:
        if not os.path.exists(cl.FENCE_FLAG):
            with open(cl.FENCE_FLAG, "w") as f:
                f.write("%s %s\n" % (time.strftime("%Y-%m-%dT%H:%M:%S"), reason))
        for lb in labels:
            if _loaded(lb):
                subprocess.run(["launchctl", "bootout", "gui/%s/%s" % (UID, lb)], capture_output=True)
                logline("FENCE: booted out %s" % lb)
    else:
        if os.path.exists(cl.FENCE_FLAG):
            os.remove(cl.FENCE_FLAG)
            logline("UNFENCE: flag cleared")
        for lb in cfg["studio_fence_labels"]:
            pl = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % lb)
            if os.path.exists(pl) and not _loaded(lb):
                subprocess.run(["launchctl", "bootstrap", "gui/%s" % UID, pl], capture_output=True)
                logline("UNFENCE: bootstrapped %s" % lb)


def main():
    cfg = cl.load_cfg()
    if "--status" in sys.argv[1:]:
        print(json.dumps(cl.read_json(LOCAL), indent=1)); return 0
    if cl.role(cfg) != "studio":
        logline("not the Studio (role=%s) — refusing to renew" % cl.role(cfg)); return 0
    live = cl.is_live(cfg)
    now = time.time()
    local = cl.read_json(LOCAL, {}) or {}
    store = cl.SupabaseStore(cfg)
    read_ok, lease = store.get(cfg["lease_object"])
    inet = True if read_ok else cl.internet_ok(cfg)
    write, fenced, reason = cl.studio_decide(cfg, now, read_ok, lease, inet, local)
    holder = (lease or {}).get("holder")
    if write is not None:
        if store.put(cfg["lease_object"], write):
            ok2, back = store.get(cfg["lease_object"])
            if ok2 and back and back.get("holder") == "mini":
                fenced, reason, write = True, "lease-lost", None    # lost the race to a promote
                holder = "mini"
            elif ok2 and back and back.get("write_id") == write["write_id"]:
                local["last_ok_epoch"] = int(now)
                holder = "studio"
            else:
                reason = "renew write not confirmed"
        else:
            reason = "renew write failed"
    hb = push_heartbeat(cfg, now)
    prev = (local.get("fenced"), local.get("fence_reason"))
    local.update({"holder": holder, "fenced": fenced, "fence_reason": reason if fenced else None,
                  "last_run_epoch": int(now), "mode": cfg.get("mode"), "heartbeat_pushed": hb,
                  "last_reason": reason})
    cl.write_json(LOCAL, local)
    enforce(cfg, fenced, reason, live)
    changed = prev != (fenced, local["fence_reason"]) or reason in ("reclaimed-from-pending",)
    if changed or not hb or reason not in ("renewed",):
        logline("holder=%s fenced=%s reason=%s heartbeat=%s mode=%s" % (holder, fenced, reason, hb, cfg.get("mode")))
    if changed:
        cl.fleet("lease-renew", "fence" if fenced else "renew", reason,
                 {"holder": holder, "fenced": fenced, "mode": cfg.get("mode")}, "warn" if fenced else "info")
    return 0


if __name__ == "__main__":
    sys.exit(main())
