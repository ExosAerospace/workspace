#!/usr/bin/env python3
"""
failover_validate.py — weekly failover-path validation drill (Sunday 02:10 CT).

NON-DESTRUCTIVE. Proves the Mini could take over from the Studio without actually flipping
production (never repoints the Cloudflare tunnel, never enables the singleton send-crons — no
split-brain). Steps:
  1. Fresh transfer  — run studio_dr_backup.sh (validates the transfer path + refreshes mirror).
  2. Mirror integrity — the critical paths landed on the backup target.
  3. Cold-start readiness — server.js syntax OK, Ollama model set present, Bridge cert present,
     every launchd plist lints clean.
  4. RTO/RPO — drill wall-time (RTO proxy) + age of last good backup (RPO = data-loss window).
  5. Degradation register — what runs slower / is unavailable while the Studio is down.
  6. Report + DM Jon a weekly pass/fail summary.

Pre-migration it runs in self-test mode against the LOCAL mirror (config/dr-backup.json);
post-migration it validates the real Studio->Mini path over Cloudflare.

Usage: python3 scripts/failover_validate.py [--print]   (--print = don't DM, just show)
"""
import os, sys, json, time, subprocess, shutil
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
sys.path.insert(0, os.path.join(WS, "scripts"))
import backup_health_gate as gate

CFG = json.load(open(os.path.join(WS, "config", "dr-backup.json")))
DEST = CFG["dest"]; REMOTE = str(CFG.get("dest_is_remote")).lower() == "true"
LOG = os.path.join(WS, "logs", "failover-validate.log")
REPORTS = os.path.join(WS, "reports")
OPENCLAW = "/Users/exomac/.local/share/mise/shims/openclaw"
DM = CFG.get("alert_discord_dm_target", "user:1501632195163590739")
SYSCH = CFG.get("alert_discord_system_channel")

# model set that MUST be resident for the Mini to serve as failover (fits 48GB)
REQUIRED_MODELS_SUBSTR = ["coder", "embed"]   # a coder + embeddings at minimum on the Mini

def logline(s):
    os.makedirs(os.path.join(WS, "logs"), exist_ok=True)
    line = f"{datetime.now(timezone.utc).isoformat()} {s}"
    print(line)
    open(LOG, "a").write(line + "\n")

def _exists(rel):
    """Does a path exist under the mirror dest (local or remote)?"""
    if REMOTE:
        host = DEST.split(":")[0]; base = DEST.split(":", 1)[1]
        r = subprocess.run(["ssh", host, f"test -e '{base}{rel}'"], timeout=20)
        return r.returncode == 0
    return os.path.exists(os.path.join(DEST, rel))

def send(text):
    if "--print" in sys.argv[1:]:
        return
    for tgt in [DM, SYSCH]:
        if not tgt: continue
        try:
            subprocess.run([OPENCLAW, "message", "send", "--channel", "discord",
                            "--target", tgt, "-m", text], timeout=60, check=False)
        except Exception as e:
            logline(f"WARN discord send failed: {e}")

def degradation_register():
    """What is degraded/delayed while the Studio is unavailable (Mini-only operation)."""
    # dynamic: RPO from the sentinel
    st = gate.read_state()
    rpo = "unknown (no backup on record)"
    if st:
        age_h = (time.time() - st.get("last_success_epoch", 0)) / 3600.0
        rpo = f"~{age_h:.1f}h of data-loss exposure (time since last good backup)"
    return [
        ("Heavy models", "DEGRADED", "Mini is 48GB vs Studio 96GB — cannot load 70B-class dense "
         "models; heavy inference falls back to ~30B-class (lower quality/slower). Kimi K3 stays archive-only (already true)."),
        ("Interactive latency for Jon", "DEGRADED", "Control plane + Jon's interactive would run on the "
         "Mini at Lizi's residence — remote for Jon, higher round-trip than the local Studio."),
        ("Compute throughput", "DELAYED", "Only one box — Lizi-interactive + batch + control plane "
         "contend; the parallel two-box pool is gone until the Studio returns."),
        ("Email (ProtonMail Bridge)", "DELAYED", "Bridge must be signed in on the Mini on failover; "
         "inbound/outbound email is down until re-auth."),
        ("Mission Control reachability", "DELAYED", "Automatic failover (failover-monitor-exo3): MC + both "
         "tunnels come up on the Mini ~7-8 min after the Studio's last lease renewal (dry-run until the live drill). "
         "Staff must use https://mc.exosaero.space — the LAN IP does not move."),
        ("Portal logins / 2FA", "DELAYED", "Some gov/vendor portals force a re-login+2FA from the "
         "'new device' on first use after failover."),
        ("QuickBooks", "DELAYED", "OAuth may need re-consent on the Mini."),
        ("Data freshness (RPO)", "EXPOSURE", rpo + " for the full tree; MC hot state (sessions, data JSON, "
         "mc.db, uploads) is synced every 5 min (dr-hot-sync), so logins + recent MC writes survive."),
        ("OpenClaw gateway crons + Studio Exobot", "MANUAL", "Not auto-started on promote (one bot token = one "
         "gateway; the Mini runs its own Exo (Mini) bot). Start by hand after a failover if needed."),
    ]

def _mini(cmd, timeout=90):
    host = DEST.split(":")[0] if REMOTE else None
    if not host:
        return 1, "", "local self-test mode"
    try:
        r = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", host, cmd],
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, "", str(e)[:120]

def failover_checks():
    out = []
    try:
        import control_lease as cl
        fcfg = cl.load_cfg()
        ok, lease = cl.SupabaseStore(fcfg).get(fcfg["lease_object"])
        age = time.time() - float((lease or {}).get("renewed_epoch", 0))
        out.append(("Control lease fresh (Supabase, holder=studio)",
                    ok and bool(lease) and lease.get("holder") == "studio" and age < 180,
                    f"holder={(lease or {}).get('holder')} age={age:.0f}s mode={fcfg.get('mode')}"))
        fl = os.path.exists(cl.FENCE_FLAG)
        out.append(("Studio not fenced", not fl, "server-fenced.flag " + ("SET" if fl else "clear")))
    except Exception as e:
        out.append(("Control lease fresh (Supabase, holder=studio)", False, str(e)[:80]))
    hs = gate_json(os.path.expanduser("~/.openclaw/state/hot-sync.json"))
    hs_age = time.time() - hs.get("epoch", 0) if hs else None
    out.append(("Hot-state sync age < 15 min (RPO 5 min target)", hs_age is not None and hs_age < 900,
                f"{hs_age:.0f}s" if hs_age is not None else "never"))
    if REMOTE:
        base = DEST.split(":", 1)[1]
        rc, so, se = _mini("cat ~/.openclaw/state/failover-monitor.json")
        try:
            st = json.loads(so); m_age = time.time() - st.get("last_run_epoch", 0)
            out.append(("Mini failover-monitor alive (< 5 min)", m_age < 300,
                        f"last run {m_age:.0f}s ago, mode={st.get('mode')}, action={st.get('last_action')}, "
                        f"hb_age={st.get('hb_age')}s mc_up={st.get('mc_up')}"))
        except Exception:
            out.append(("Mini failover-monitor alive (< 5 min)", False, (se or so or "no state")[:80]))
        rc, so, se = _mini(f"cd {base}workspace && /usr/bin/python3 scripts/failover_monitor.py --plan", 120)
        miss = [l for l in so.splitlines() if l.startswith("missing inputs")]
        out.append(("Dry-run promote plan on the Mini (all inputs present)", rc == 0, (miss[0] if miss else (se or "no output"))[:120]))
        rc, so, se = _mini(f"cd {base}workspace && /usr/bin/python3 scripts/failover_monitor.py --selftest | tail -1", 120)
        out.append(("Failover selftest on the Mini (blip/dead/partition/hold...)", rc == 0, so.strip()[:60] or se[:60]))
        rc, so, se = _mini(f"sqlite3 '{base}workspace/erp-foundation/mc.db' 'pragma integrity_check;'")
        out.append(("Mirrored mc.db integrity", rc == 0 and so.strip() == "ok", (so or se).strip()[:60]))
    return out

def gate_json(p):
    try: return json.load(open(p))
    except Exception: return None

def main():
    t0 = time.time()
    logline("=== weekly failover-validation drill START ===")
    checks = []  # (name, ok, detail)

    # 1) fresh transfer
    rc = subprocess.run(["bash", os.path.join(WS, "scripts", "studio_dr_backup.sh")]).returncode
    checks.append(("Transfer (studio_dr_backup)", rc == 0, f"exit={rc}"))

    # 2) mirror integrity
    for rel, label in [("workspace/mission-control/data/decisions.json", "MC decisions data"),
                       ("openclaw-config/secrets.json", "secrets"),
                       ("workspace/mission-control/server.js", "MC server"),
                       ("openclaw-config/.protonmail-bridge.crt", "Bridge cert")]:
        checks.append((f"Mirror has {label}", _exists(rel), rel))

    # 3) cold-start readiness (validate the source tree — what will be promoted)
    srv = os.path.join(WS, "mission-control", "server.js")
    node = shutil.which("node") or "/Users/exomac/.local/share/mise/installs/node/24.21.0/bin/node"
    try:
        r = subprocess.run([node, "--check", srv], capture_output=True, text=True, timeout=30)
        checks.append(("server.js syntax", r.returncode == 0, (r.stderr or "ok")[:80]))
    except Exception as e:
        checks.append(("server.js syntax", False, str(e)[:80]))
    try:
        # launchd PATH lacks Homebrew — resolve the binary explicitly (drill 10/4 false fail)
        oll = shutil.which("ollama") or next((c for c in ("/opt/homebrew/bin/ollama", "/usr/local/bin/ollama",
               os.path.expanduser("~/.local/bin/ollama")) if os.path.exists(c)), "ollama")
        r = subprocess.run([oll, "list"], capture_output=True, text=True, timeout=20)
        names = r.stdout.lower()
        have = all(any(sub in ln for ln in names.splitlines()) for sub in REQUIRED_MODELS_SUBSTR)
        checks.append(("Ollama failover model set", have,
                       "have coder+embed" if have else f"missing one of {REQUIRED_MODELS_SUBSTR}"))
    except Exception as e:
        checks.append(("Ollama failover model set", False, str(e)[:60]))
    staged = os.path.join(WS, "config", "launchd-staged")
    plist_ok = True; bad = []
    for p in os.listdir(staged) if os.path.isdir(staged) else []:
        if p.endswith(".plist"):
            r = subprocess.run(["plutil", "-lint", os.path.join(staged, p)], capture_output=True, text=True)
            if r.returncode != 0: plist_ok = False; bad.append(p)
    checks.append(("Staged launchd plists lint", plist_ok, "all OK" if plist_ok else f"bad: {bad}"))

    # 3b) automatic-failover readiness (dr-failover 2026-10-02): lease, hot sync, Mini monitor,
    #     dry-run promote plan on the Mini, selftest. NEVER runs a live promote.
    checks.extend(failover_checks())

    # 4) RTO/RPO
    rto = time.time() - t0
    st = gate.read_state()
    rpo_h = (time.time() - st.get("last_success_epoch", 0)) / 3600.0 if st else None

    passed = sum(1 for _, ok, _ in checks if ok); total = len(checks)
    verdict = "✅ PASS" if passed == total else ("⚠️ PARTIAL" if passed >= total - 1 else "🔴 FAIL")

    # 5+6) report
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [f"# Failover validation drill — {stamp}", f"Verdict: {verdict}  ({passed}/{total} checks)",
             f"RTO (drill wall-time): {rto:.0f}s   RPO (data-loss window): "
             f"{rpo_h:.1f}h" if rpo_h is not None else "RPO: unknown",
             f"Mode: {'REMOTE Studio->Mini' if REMOTE else 'LOCAL self-test (pre-migration)'}", "", "## Checks"]
    for n, ok, d in checks:
        lines.append(f"- [{'x' if ok else ' '}] {n} — {d}")
    lines += ["", "## Degradation register (Mini-only operation)"]
    for name, sev, desc in degradation_register():
        lines.append(f"- **{name}** [{sev}] — {desc}")
    report = "\n".join(lines)
    os.makedirs(REPORTS, exist_ok=True)
    rp = os.path.join(REPORTS, f"failover-drill-{stamp}.md")
    open(rp, "w").write(report)
    logline(f"=== drill END {verdict} {passed}/{total} RTO={rto:.0f}s ===")

    fails = [n for n, ok, _ in checks if not ok]
    send(f"🛟 Weekly failover drill ({stamp}): {verdict} — {passed}/{total} checks, "
         f"RTO {rto:.0f}s, RPO {rpo_h:.1f}h.{(' Failing: ' + ', '.join(fails)) if fails else ''} "
         f"Full report + degradation register: reports/failover-drill-{stamp}.md")
    if "--print" in sys.argv[1:]:
        print("\n" + report)

if __name__ == "__main__":
    main()
