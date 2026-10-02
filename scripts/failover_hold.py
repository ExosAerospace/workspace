#!/usr/bin/python3
"""
failover_hold.py — maintenance HOLD for the automatic Studio->Mini failover + manual FAILBACK.

Before a planned Studio reboot / macOS update / network work, set a hold so the Mini does NOT
promote while the Studio is intentionally dark:

  python3 scripts/failover_hold.py --minutes 45 --reason "macOS 26.8 update"
  python3 scripts/failover_hold.py --status
  python3 scripts/failover_hold.py --clear

The hold lives next to the lease in Supabase (bucket exos-control, object failover-hold.json) so
both boxes see it. It expires on its own (max 24 h). While a hold is active the Mini also withdraws
any pending claim. Works from either box (or any machine with the workspace + secrets).

FAILBACK (Mini -> Studio) is MANUAL ONLY (Jon). With the Studio healthy again:
  1. on the Mini:   stop the promoted jobs (launchctl bootout each com.exos.* the promote loaded)
  2. sync Mini -> Studio state (MC data, mc.db, uploads) — hot state written on the Mini while promoted
  3. on the Studio: python3 scripts/failover_hold.py --failback --confirm "<your name>"
     -> writes holder=studio (fresh renewal); lease_renew then unfences the Studio on its next tick.
"""
import os, sys, json, time, socket

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import control_lease as cl

MAX_MIN = 24 * 60


def main():
    a = sys.argv[1:]
    cfg = cl.load_cfg()
    st = cl.SupabaseStore(cfg)
    now = int(time.time())
    who = "%s@%s" % (os.environ.get("USER", "?"), socket.gethostname().split(".")[0])

    def arg(flag, default=None):
        return a[a.index(flag) + 1] if flag in a and a.index(flag) + 1 < len(a) else default

    if not a or "--status" in a:
        ok, hold = st.get(cfg["hold_object"])
        lok, lease = st.get(cfg["lease_object"])
        print("hold:  %s" % ("unreadable" if not ok else ("ACTIVE until %s (%s, by %s)" % (
            time.strftime("%Y-%m-%d %H:%M", time.localtime(hold["until_epoch"])), hold.get("reason"), hold.get("by"))
            if cl.hold_active(hold, now) else "none")))
        if lok and lease:
            print("lease: holder=%s age=%ds gen=%s" % (lease.get("holder"), now - lease.get("renewed_epoch", 0), lease.get("generation")))
        return 0
    if "--minutes" in a:
        m = int(arg("--minutes"))
        if not 1 <= m <= MAX_MIN:
            print("minutes must be 1..%d" % MAX_MIN); return 2
        hold = {"until_epoch": now + m * 60, "reason": arg("--reason", "planned maintenance"), "by": who, "set_epoch": now}
        ok = st.put(cfg["hold_object"], hold)
        cl.fleet("failover-hold", "set", "ok" if ok else "error", hold)
        print(("hold SET for %d min (until %s)" % (m, time.strftime("%H:%M", time.localtime(hold["until_epoch"])))) if ok else "FAILED to write hold")
        return 0 if ok else 1
    if "--clear" in a:
        ok = st.put(cfg["hold_object"], {"until_epoch": 0, "reason": "cleared", "by": who, "set_epoch": now})
        cl.fleet("failover-hold", "clear", "ok" if ok else "error", {"by": who})
        print("hold cleared" if ok else "FAILED"); return 0 if ok else 1
    if "--failback" in a:
        name = arg("--confirm")
        if not name:
            print("failback is manual: add --confirm \"<your name>\" after the Mini's promoted jobs are stopped"); return 2
        if cl.role(cfg) != "studio":
            print("run --failback on the Studio"); return 2
        ok, lease = st.get(cfg["lease_object"])
        if not ok:
            print("lease unreadable — not failing back"); return 1
        w = dict(lease or {}, holder="studio", renewed_epoch=now, renewed_by="studio",
                 generation=int((lease or {}).get("generation", 0)) + 1, claim_epoch=None, promoted_epoch=None,
                 note="manual failback by %s" % name, write_id="failback-%d" % now)
        ok = st.put(cfg["lease_object"], w)
        cl.fleet("failover-hold", "failback", "ok" if ok else "error", {"by": name})
        local = os.path.join(cl.STATE_DIR, "control-lease-local.json")
        d = cl.read_json(local, {}) or {}
        d.update({"fenced": False, "fence_reason": None, "last_ok_epoch": now, "holder": "studio"})
        cl.write_json(local, d)
        print("failback written (holder=studio). lease_renew will unfence on its next tick." if ok else "FAILED")
        return 0 if ok else 1
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())
