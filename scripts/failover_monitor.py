#!/usr/bin/python3
"""
failover_monitor.py — MINI side: automatic Studio->Mini failover at 6 minutes (Jon 2026-10-02).

launchd (user LaunchAgent on the Mini) com.exos.failover-monitor, every 60 s. Runs from the DR
mirror (~/dr-mirror/workspace/scripts) so every hourly backup ships the current code.

Promote ONLY if ALL of:
  - the control lease (Supabase) has not been renewed for >= promote_after_s (360 s), via a
    'mini-pending' claim that sat >= 60 s without the Studio reclaiming it;
  - the Studio is dark on BOTH independent paths:
      path 1  Studio->Mini heartbeat over the exos-mini link (lease_renew.py pushes it every 60 s)
      path 2  MC https health through the exos-mc tunnel (https://mc.exosaero.space/sign)
  - no maintenance hold (failover_hold.py).
Then: write holder=mini, wait confirm_wait_s, re-read (still ours) -> promote:
  restore hot state + config from the mirror, load MC (wait for :8080), then the exos-mc +
  lan-tunnel connectors, then the Studio's loaded com.exos jobs; DM Jon + post #exomac-system.
FAILBACK is manual only (Jon) — see failover_hold.py --failback.

mode (config/failover.json) = "dry-run" (default until the live drill passes): reads the real lease
and probes the real paths, but never writes the lease, never starts anything, never messages anyone —
it logs what it WOULD do (claim / promote / the full promote plan) to ~/Library/Logs/exos-failover-monitor.log
and ~/.openclaw/state/failover-monitor.json.

Usage:
  failover_monitor.py                 one tick (launchd)
  failover_monitor.py --plan          print the promote plan (dry, on the Mini) and check every input exists
  failover_monitor.py --selftest      replay the failure scenarios on a simulated clock (no I/O)
"""
import os, sys, json, time, glob, shutil, subprocess, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import control_lease as cl

LOCAL = os.path.join(cl.STATE_DIR, "failover-monitor.json")
LOG = os.path.expanduser("~/Library/Logs/exos-failover-monitor.log")
UID = str(os.getuid())


def logline(s):
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    line = "%s %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), s)
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


# ------------------------------------------------------------------ promote
def _loaded_labels_from_mirror(cfg):
    m = cfg["mini_mirror"]
    loaded_txt = os.path.join(m, "launchagents", "_loaded.txt")
    have = sorted(os.path.basename(p)[:-6] for p in glob.glob(os.path.join(m, "launchagents", "com.exos.*.plist")))
    if os.path.exists(loaded_txt):
        want = [l.strip() for l in open(loaded_txt) if l.strip()]
        have = [l for l in have if l in want]
    skip = set(cfg["promote_skip_labels"]) | set(cfg["promote_first"]) | set(cfg["promote_tunnels"])
    return [l for l in have if l not in skip]


def promote_plan(cfg):
    m = cfg["mini_mirror"]
    steps = [
        ("restore workspace (no delete) from mirror", "rsync -a %s/workspace/ ~/.openclaw/workspace/" % m),
        ("restore secrets.json (keep .pre-promote copy)", "%s/openclaw-config/secrets.json -> ~/.openclaw/secrets.json" % m),
        ("restore tunnel creds (keep .pre-promote copy)", "%s/cloudflared/ -> ~/.cloudflared/" % m),
        ("restore ~/.config/exos (no overwrite of newer)", "%s/config-exos/ -> ~/.config/exos/" % m),
        ("restore Bridge cert + msmtp", "%s/openclaw-config/{.protonmail-bridge.crt,.msmtprc} -> ~/" % m),
    ]
    for lb in cfg["promote_first"]:
        steps.append(("load " + lb + " then wait for http://127.0.0.1:8080/login == 200", lb))
    for lb in cfg["promote_tunnels"]:
        steps.append(("load connector " + lb, lb))
    rest = _loaded_labels_from_mirror(cfg)
    steps.append(("load %d Studio jobs (send-crons etc.)" % len(rest), ",".join(rest)))
    steps.append(("notify Jon DM + #exomac-system (Discord REST, Exobot token from mirror secrets)", ""))
    missing = []
    for p in ["workspace/mission-control/server.js", "workspace/erp-foundation/mc.db", "openclaw-config/secrets.json",
              "cloudflared/exos-mc.yml", "cloudflared/exos-exomac-lan.token", ".hot-sync-stamp.json"]:
        if not os.path.exists(os.path.join(m, p)):
            missing.append(p)
    for lb in cfg["promote_first"] + cfg["promote_tunnels"]:
        if not os.path.exists(os.path.join(m, "launchagents", lb + ".plist")):
            missing.append("launchagents/%s.plist" % lb)
    node = "/Users/exomac/.local/share/mise/installs/node/24.21.0/bin/node"
    if not os.path.exists(node):
        missing.append(node)
    if not os.path.exists("/opt/homebrew/bin/cloudflared"):
        missing.append("/opt/homebrew/bin/cloudflared")
    stamp = cl.read_json(os.path.join(m, ".hot-sync-stamp.json"), {}) or {}
    rpo = int(time.time() - stamp.get("epoch", 0)) if stamp else None
    return steps, missing, rest, rpo


def _copy_with_backup(src, dst, ts):
    if not os.path.exists(src):
        return
    if os.path.exists(dst):
        shutil.copy2(dst, dst + ".pre-promote-" + ts)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def _bootstrap(lb, m):
    src = os.path.join(m, "launchagents", lb + ".plist")
    dst = os.path.expanduser("~/Library/LaunchAgents/%s.plist" % lb)
    shutil.copy2(src, dst)
    if subprocess.run(["launchctl", "print", "gui/%s/%s" % (UID, lb)], capture_output=True).returncode == 0:
        return True
    r = subprocess.run(["launchctl", "bootstrap", "gui/%s" % UID, dst], capture_output=True, text=True)
    if r.returncode != 0:
        logline("WARN bootstrap %s rc=%s %s" % (lb, r.returncode, r.stderr.strip()[:200]))
    return r.returncode == 0


def discord_send(cfg, text):
    try:
        tok = json.load(open(os.path.join(cfg["mini_mirror"], "openclaw-config", "secrets.json")))["discord_token"]
    except Exception as e:
        logline("WARN no discord token: %s" % e); return False
    h = {"Authorization": "Bot " + tok, "Content-Type": "application/json", "User-Agent": "exos-failover (1)"}
    api = "https://discord.com/api/v10"
    ok = True
    try:
        req = urllib.request.Request(api + "/users/@me/channels", method="POST", headers=h,
                                     data=json.dumps({"recipient_id": cfg["discord_dm_user"]}).encode())
        dm = json.load(urllib.request.urlopen(req, timeout=15))["id"]
        for ch in (dm, cfg["discord_system_channel"]):
            req = urllib.request.Request(api + "/channels/%s/messages" % ch, method="POST", headers=h,
                                         data=json.dumps({"content": text[:1900]}).encode())
            urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        logline("WARN discord send failed: %s" % e); ok = False
    return ok


def execute_promote(cfg):
    m = cfg["mini_mirror"]
    ts = time.strftime("%Y%m%dT%H%M%S")
    t0 = time.time()
    steps, missing, rest, rpo = promote_plan(cfg)
    logline("PROMOTE START (missing inputs: %s, hot-state RPO %ss)" % (missing or "none", rpo))
    subprocess.run(["rsync", "-a", m + "/workspace/", os.path.expanduser("~/.openclaw/workspace/")], timeout=1800)
    _copy_with_backup(os.path.join(m, "openclaw-config", "secrets.json"), os.path.expanduser("~/.openclaw/secrets.json"), ts)
    for f in os.listdir(os.path.join(m, "cloudflared")) if os.path.isdir(os.path.join(m, "cloudflared")) else []:
        _copy_with_backup(os.path.join(m, "cloudflared", f), os.path.expanduser("~/.cloudflared/" + f), ts)
    subprocess.run(["rsync", "-a", "--update", m + "/config-exos/", os.path.expanduser("~/.config/exos/")], timeout=300)
    for f in (".protonmail-bridge.crt", ".msmtprc"):
        _copy_with_backup(os.path.join(m, "openclaw-config", f), os.path.expanduser("~/" + f), ts)
    for lb in cfg["promote_first"]:
        _bootstrap(lb, m)
    mc_ok = False
    for _ in range(30):
        if cl.http_ok("http://127.0.0.1:8080/login", 3):
            mc_ok = True; break
        time.sleep(2)
    logline("MC local health: %s" % ("200" if mc_ok else "NOT UP after 60 s"))
    for lb in cfg["promote_tunnels"]:
        _bootstrap(lb, m)
    n_ok = sum(1 for lb in rest if _bootstrap(lb, m))
    dur = int(time.time() - t0)
    msg = ("🛟 FAILOVER: the Mac Studio went dark (lease stale >= %d min, no heartbeat, MC https down) and the "
           "Mac mini at Lizi's has PROMOTED itself to server. MC local health: %s. Started %d/%d jobs + both tunnels in %ds. "
           "Hot-state RPO ~%ss. Degraded: 30B models only, OpenClaw gateway crons NOT auto-started (manual), "
           "Bridge may need re-auth. Studio stays fenced. FAILBACK IS MANUAL (Jon): failover_hold.py --failback."
           % (cfg["promote_after_s"] // 60, "OK" if mc_ok else "NOT UP", n_ok, len(rest), dur, rpo))
    discord_send(cfg, msg)
    cl.fleet("failover-monitor", "promote", "promoted", {"mc_ok": mc_ok, "jobs": n_ok, "of": len(rest), "dur_s": dur,
                                                          "rpo_s": rpo, "missing": missing}, "warn")
    logline("PROMOTE DONE " + msg)
    return mc_ok


# ------------------------------------------------------------------ one tick
def tick():
    cfg = cl.load_cfg()
    live = cl.is_live(cfg)
    if cl.role(cfg) != "mini":
        logline("not the Mini (role=%s) — monitor only runs on the Mini" % cl.role(cfg)); return 0
    now = time.time()
    local = cl.read_json(LOCAL, {}) or {}
    store = cl.SupabaseStore(cfg)
    read_ok, lease = store.get(cfg["lease_object"])
    _, hold = store.get(cfg["hold_object"])
    # dry-run: overlay our own un-written claim while the Studio still hasn't renewed
    shadow = local.get("dry_shadow")
    eff = lease
    if not live and shadow and lease and lease.get("renewed_epoch") == shadow.get("renewed_epoch") \
            and lease.get("holder") == "studio":
        eff = shadow
    try:
        hb = float(open(cfg["heartbeat_file_on_mini"]).read().strip())
        hb_age = now - hb
    except Exception:
        hb_age = None
    mc_up = cl.mc_https_up(cfg)
    write, action, reason = cl.mini_decide(cfg, now, read_ok, eff, hold, hb_age, mc_up, local)
    prev_action = local.get("last_action")
    local.update({"last_run_epoch": int(now), "mode": cfg.get("mode"), "last_action": action, "last_reason": reason,
                  "lease_holder": (lease or {}).get("holder"), "hb_age": None if hb_age is None else int(hb_age),
                  "mc_up": mc_up, "read_ok": read_ok})
    if action in ("claim", "withdraw", "promote-lease"):
        if live:
            if not store.put(cfg["lease_object"], write):
                reason += " [lease write FAILED]"; action = "none"
            elif action == "promote-lease":
                time.sleep(5)
                ok2, back = store.get(cfg["lease_object"])
                if ok2 and back and back.get("write_id") == write["write_id"]:
                    local["promote_due_epoch"] = int(now + cfg["confirm_wait_s"])
                else:
                    reason += " [lost the race — Studio reclaimed]"; action = "none"
        else:
            if action == "claim":
                local["dry_shadow"] = write
            elif action == "withdraw":
                local.pop("dry_shadow", None)
            elif action == "promote-lease":
                steps, missing, rest, rpo = promote_plan(cfg)
                local["dry_would_promote_epoch"] = int(now)
                local.pop("dry_shadow", None)
                logline("[dry-run] WOULD PROMOTE NOW (%s). Plan: %d jobs, missing inputs %s, hot RPO %ss" %
                        (reason, len(rest), missing or "none", rpo))
                cl.fleet("failover-monitor", "would-promote", "dry-run", {"reason": reason, "missing": missing, "rpo_s": rpo}, "warn")
    elif action == "execute-promote":
        if live:
            execute_promote(cfg)
            local["promote_done"] = int(time.time())
        else:
            logline("[dry-run] would execute promote (lease says mini)")
    elif not live and local.get("dry_shadow") and eff is lease:
        local.pop("dry_shadow", None)          # Studio renewed: drop our imaginary claim
    cl.write_json(LOCAL, local)
    if action != "none" or action != prev_action or "unreadable" in reason or "stale" in reason:
        logline("%s%s: %s (hb_age=%s mc_up=%s holder=%s)" % ("" if live else "[dry-run] ", action, reason,
                                                            local["hb_age"], mc_up, local["lease_holder"]))
        cl.fleet("failover-monitor", action, reason[:120], {"mode": cfg.get("mode"), "hb_age": local["hb_age"],
                                                            "mc_up": mc_up, "holder": local["lease_holder"]},
                 "warn" if action != "none" else "info")
    return 0


# ------------------------------------------------------------------ selftest (simulation)
def selftest():
    cfg = cl.load_cfg()
    results = []

    def run(name, minutes, studio_alive, studio_internet, studio_supabase=None, tunnel_ok=None, hold_until=None):
        """Simulate both sides on a shared clock. Each fn(t_minutes)->bool."""
        studio_supabase = studio_supabase or (lambda t: True)
        tunnel_ok = tunnel_ok or (lambda t: True)
        store = cl.MemStore()
        if hold_until is not None:
            store.objs[cfg["hold_object"]] = {"until_epoch": hold_until, "reason": "selftest maintenance"}
        s_local, m_local = {}, {}
        t0 = 1_800_000_000.0
        hb_last = None
        mini_active_at = None
        studio_fenced_at = None
        both = []
        studio_fenced = False
        mini_active = False
        for step in range(0, minutes * 60 + 1, 30):
            now = t0 + step
            tm = step / 60.0
            alive, inet = studio_alive(tm), studio_alive(tm) and studio_internet(tm)
            if step % 60 == 0 and alive:                       # Studio renewer tick
                if inet and studio_supabase(tm):
                    store.blocked.discard("studio")
                else:
                    store.blocked.add("studio")
                v = store.view("studio")
                ok, lease = v.get(cfg["lease_object"])
                w, fenced, reason = cl.studio_decide(cfg, now, ok, lease, inet, s_local)
                if w is not None and v.put(cfg["lease_object"], w):
                    s_local["last_ok_epoch"] = now
                s_local.update(fenced=fenced, fence_reason=reason if fenced else None)
                studio_fenced = fenced
                if fenced and studio_fenced_at is None:
                    studio_fenced_at = tm
                if inet:
                    hb_last = now                               # heartbeat push over exos-mini link
            if step % 60 == 30:                                 # Mini monitor tick
                v = store.view("mini")
                ok, lease = v.get(cfg["lease_object"])
                _, hold = v.get(cfg["hold_object"])
                hb_age = None if hb_last is None else now - hb_last
                mc_up = alive and inet and tunnel_ok(tm) and not studio_fenced
                w, action, reason = cl.mini_decide(cfg, now, ok, lease, hold, hb_age, mc_up, m_local)
                if w is not None:
                    v.put(cfg["lease_object"], w)
                    if action == "promote-lease":
                        m_local["promote_due_epoch"] = now + cfg["confirm_wait_s"]
                if action == "execute-promote":
                    m_local["promote_done"] = now
                    mini_active, mini_active_at = True, tm
            studio_active = alive and not studio_fenced and inet
            if studio_active and mini_active:
                both.append(tm)
        return {"mini_active_at": mini_active_at, "studio_fenced_at": studio_fenced_at, "both_active": both,
                "final_holder": (store.objs.get(cfg["lease_object"]) or {}).get("holder"), "studio_fenced_end": studio_fenced}

    def case(name, cond, detail):
        results.append(cond)
        print("%s %-62s %s" % ("PASS" if cond else "FAIL", name, detail))

    T, F = (lambda t: True), (lambda t: False)
    r = run("blip", 15, studio_alive=lambda t: not (2 <= t < 5), studio_internet=T)
    case("1. Studio blip 3 min -> NO promote", r["mini_active_at"] is None and r["final_holder"] == "studio", r)
    r = run("dead", 15, studio_alive=lambda t: t < 2, studio_internet=T)
    ok = r["mini_active_at"] is not None and 6 <= r["mini_active_at"] - 2 <= 8
    case("2. Studio dead 7+ min -> promote at 6-8 min after death", ok, r)
    r = run("partition", 20, studio_alive=T, studio_internet=lambda t: not (2 <= t < 14))
    ok = (r["mini_active_at"] is not None and r["studio_fenced_at"] is not None
          and r["studio_fenced_at"] < r["mini_active_at"] and not r["both_active"] and r["studio_fenced_end"])
    case("3. Studio alive-but-partitioned -> Studio fences, Mini promotes, never both, stays fenced after heal", ok, r)
    r = run("hold", 20, studio_alive=lambda t: t < 2, studio_internet=T, hold_until=1_800_000_000 + 3600)
    case("4. maintenance hold set, Studio dark 18 min -> NO promote", r["mini_active_at"] is None, r)
    r = run("supabase-only", 15, studio_alive=T, studio_internet=T, studio_supabase=lambda t: not (2 <= t < 12))
    ok = r["mini_active_at"] is None and r["studio_fenced_at"] is None
    case("5. Supabase unreachable from Studio only -> no fence, no promote", ok, r)
    r = run("returns", 15, studio_alive=lambda t: not (2 <= t < 7.2), studio_internet=T)
    ok = r["mini_active_at"] is None and r["final_holder"] == "studio" and not r["both_active"]
    case("6. Studio back during the Mini's claim -> Studio reclaims, no promote", ok, r)
    r = run("tunnel-dead", 15, studio_alive=T, studio_internet=T, tunnel_ok=lambda t: t < 2)
    case("7. exos-mc tunnel dead but Studio alive (lease+heartbeat fresh) -> no promote", r["mini_active_at"] is None, r)
    n = sum(results)
    print("selftest %d/%d" % (n, len(results)))
    return 0 if n == len(results) else 1


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--selftest" in a:
        sys.exit(selftest())
    if "--plan" in a:
        cfg = cl.load_cfg()
        steps, missing, rest, rpo = promote_plan(cfg)
        print("mode: %s   role: %s" % (cfg.get("mode"), cl.role(cfg)))
        for i, (s, d) in enumerate(steps, 1):
            print("%2d. %s%s" % (i, s, ("  [" + d[:160] + ("..." if len(d) > 160 else "") + "]") if d else ""))
        print("missing inputs: %s" % (missing or "none"))
        print("hot-state RPO now: %ss" % rpo)
        sys.exit(1 if missing else 0)
    sys.exit(tick())
