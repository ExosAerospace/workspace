#!/usr/bin/env python3
"""
util_metrics.py — per-host utilization collector for the two-machine compute pool.

Foundation of the utilization-sharing recursive self-improvement loop: you cannot
optimize allocation or forecast hardware demand without measuring both boxes first.
Runs on EVERY host (tagged by hostname + role), appends one JSON line per sample to
mission-control/data/host-utilization.jsonl. Deterministic, no LLM, no network writes.

Captured per sample: cpu load (per-core %), memory used %, disk free, Ollama loaded
models + running requests (best-effort), and the host role. GPU% on macOS needs sudo
(powermetrics) so it's best-effort/optional — CPU load + mem + Ollama activity are the
capacity proxies used by the weekly forecast.

Usage:
  python3 scripts/util_metrics.py            # take one sample, append to the log
  python3 scripts/util_metrics.py --print    # sample + print it, don't append
  python3 scripts/util_metrics.py --tail 5   # show last N samples for this host
"""
import os, sys, json, time, subprocess, shutil, socket
from datetime import datetime, timezone

WS = "/Users/exomac/.openclaw/workspace"
OUT = os.path.join(WS, "mission-control", "data", "host-utilization.jsonl")
MAX_LINES = 5000   # ~35 days at a 10-min cadence; trims oldest beyond this

# host -> role map (extend at migration). Unknown hosts default to "worker".
ROLE = {
    "ExoMacs-Mini": "primary-onsite",     # today the mini is primary; at migration it becomes offsite-worker
    "exomac-studio": "primary-onsite",     # Studio becomes primary onsite
}

def _sysctl_int(key):
    try: return int(subprocess.run(["sysctl","-n",key],capture_output=True,text=True,timeout=5).stdout.strip())
    except Exception: return None

def cpu():
    ncpu = os.cpu_count() or _sysctl_int("hw.ncpu") or 1
    try: l1,l5,l15 = os.getloadavg()
    except Exception: l1=l5=l15=None
    pct = round(100.0*l1/ncpu,1) if l1 is not None else None
    return {"ncpu": ncpu, "load1": l1, "load5": l5, "load15": l15, "load1_pct_of_cores": pct}

def memory():
    total = _sysctl_int("hw.memsize")
    used_pct = None; free_bytes = None
    try:
        out = subprocess.run(["vm_stat"],capture_output=True,text=True,timeout=5).stdout
        page = 4096
        for ln in out.splitlines():
            if "page size of" in ln:
                try: page = int(ln.split("page size of")[1].split("bytes")[0].strip())
                except Exception: pass
        def g(label):
            for ln in out.splitlines():
                if ln.startswith(label):
                    return int(ln.split(":")[1].strip().rstrip("."))
            return 0
        free = (g("Pages free")+g("Pages inactive"))*page
        active = (g("Pages active")+g("Pages wired down")+g("Pages occupied by compressor"))*page
        free_bytes = free
        if total: used_pct = round(100.0*active/total,1)
    except Exception: pass
    return {"total_gb": round(total/1e9,1) if total else None,
            "used_pct": used_pct, "free_gb": round(free_bytes/1e9,1) if free_bytes else None}

def disk():
    try:
        t,u,f = shutil.disk_usage("/")
        return {"root_free_gb": round(f/1e9,1), "root_used_pct": round(100.0*u/t,1)}
    except Exception: return {}

def _warm_cfg():
    # early-warning thresholds: GPU telemetry only arms when a proxy crosses these
    c = {"cpu_warm_pct": 50.0, "mem_warm_pct": 65.0, "gpu_telemetry": "auto"}
    try:
        j = json.load(open(os.path.join(WS, "config", "capacity-forecast.json")))
        for k in c: c[k] = j.get(k, c[k])
    except Exception: pass
    return c

def gpu(armed):
    """Real GPU telemetry via powermetrics — ONLY when armed (proxies near capacity) so the
    sudo-heavy sampler doesn't run all the time. Needs a passwordless sudoers entry for
    powermetrics (see scripts/README / migration runbook); until then it reports needs_sudo."""
    if not armed:
        return {"sampled": False, "reason": "below warm threshold (armed only near capacity)"}
    try:
        r = subprocess.run(
            ["sudo", "-n", "powermetrics", "--samplers", "gpu_power", "-n", "1", "-i", "200"],
            capture_output=True, text=True, timeout=8)
        if r.returncode != 0:
            return {"sampled": False, "reason": "needs_sudo_helper", "err": (r.stderr or "")[:80]}
        active = None
        for ln in r.stdout.splitlines():
            l = ln.strip()
            if "active residency" in l.lower() and "%" in l:
                try: active = float(l.split("%")[0].split()[-1])
                except Exception: pass
        return {"sampled": True, "active_pct": active}
    except FileNotFoundError:
        return {"sampled": False, "reason": "powermetrics not found"}
    except Exception as e:
        return {"sampled": False, "reason": f"error:{str(e)[:60]}"}

def ollama():
    # best-effort: loaded models + in-flight requests via the local API
    try:
        import urllib.request
        req=urllib.request.urlopen("http://127.0.0.1:11434/api/ps",timeout=3)
        d=json.load(req); models=d.get("models",[])
        return {"up": True, "loaded_models": [m.get("name") for m in models],
                "loaded_count": len(models)}
    except Exception:
        return {"up": False, "loaded_models": [], "loaded_count": 0}

def sample():
    host = socket.gethostname().split(".")[0]
    role = ROLE.get(host, "worker")
    c = cpu(); m = memory(); wc = _warm_cfg()
    # arm real GPU telemetry only when a proxy is near capacity (Jon 2026-09-13)
    cpu_pct = c.get("load1_pct_of_cores") or 0
    mem_pct = m.get("used_pct") or 0
    armed = (wc["gpu_telemetry"] != "off") and (cpu_pct >= wc["cpu_warm_pct"] or mem_pct >= wc["mem_warm_pct"])
    return {
        "ts": datetime.now(timezone.utc).isoformat(),
        "epoch": int(time.time()),
        "host": host, "role": role,
        "cpu": c, "mem": m, "disk": disk(), "ollama": ollama(),
        "gpu": gpu(armed), "gpu_armed": armed,
    }

def append(s):
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT,"a") as f: f.write(json.dumps(s)+"\n")
    # trim
    try:
        lines=open(OUT).read().splitlines()
        if len(lines)>MAX_LINES:
            open(OUT,"w").write("\n".join(lines[-MAX_LINES:])+"\n")
    except Exception: pass

if __name__=="__main__":
    a=sys.argv[1:]
    if a and a[0]=="--print":
        print(json.dumps(sample(),indent=2)); sys.exit(0)
    if a and a[0]=="--tail":
        n=int(a[1]) if len(a)>1 else 5
        host=socket.gethostname().split(".")[0]
        try:
            rows=[json.loads(l) for l in open(OUT).read().splitlines()]
            rows=[r for r in rows if r.get("host")==host][-n:]
            for r in rows:
                print(f'{r["ts"]}  cpu {r["cpu"].get("load1_pct_of_cores")}%  '
                      f'mem {r["mem"].get("used_pct")}%  disk_free {r["disk"].get("root_free_gb")}GB  '
                      f'ollama {r["ollama"].get("loaded_count")} models')
        except FileNotFoundError:
            print("(no samples yet)")
        sys.exit(0)
    s=sample(); append(s)
    print(f'sampled {s["host"]} ({s["role"]}): cpu {s["cpu"]["load1_pct_of_cores"]}%  '
          f'mem {s["mem"]["used_pct"]}%  disk_free {s["disk"].get("root_free_gb")}GB')
