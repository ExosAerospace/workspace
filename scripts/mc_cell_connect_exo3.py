#!/usr/bin/env python3
"""
mc_cell_connect_exo3.py — store a customer system connection that Exo set up for an MC cell.
exo3 spec: agent-registry.json -> mc-cell-onboard-exo3 (same agent). Owner: John Quinn.

Jon 2026-10-22: "customers have to set up API key accounts, however I expect Exo to do that short of
login and saves on a Google browser window." Flow per system (runbook: skill 'mc-cell-connect'):
  1. Exo opens the vendor's sign-in page in a dedicated Chrome profile for the cell (OpenClaw browser,
     profile mc-<entity>); the customer signs in (their only step) while the rollout rep shares it.
  2. Exo clicks through the vendor's API-key / app-authorization screens.
  3. Exo pipes the key into this script on stdin (never on the command line, never in chat):
       store --entity sslc --system bamboohr --field api_key [--field subdomain=acme]  < key
  4. The key lands in two places only: ~/.openclaw/secrets.json as <entity>__<system>__<field> (0600)
     and the cell volume /data/connections/<system>.json (0600, outside the web-served app data).
  5. The cell's startup task SU-<system> gets a note "Connected by Exo" (state left for the owner).
  list --entity E      shows which systems are connected (field names only, never values)
  forget --entity E --system S [--apply]   removes the stored connection (offboarding / vendor change)
"""
import argparse, datetime, json, os, re, subprocess, sys

WS = "/Users/exomac/.openclaw/workspace"
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
AGENT, OWNER = "mc-cell-onboard-exo3", "John Quinn"
SYSTEMS = {"quickbooks", "bamboohr", "proton", "m365", "discord", "teamwork", "docusign", "peony", "samgov"}
sys.path.insert(0, os.path.join(WS, "scripts"))
try:
    from fleet_log import event as _fleet_event
except Exception:
    _fleet_event = None


def audit(action, outcome, detail):
    with open(os.path.join(WS, "logs", "mc-cell-onboard.jsonl"), "a") as f:
        f.write(json.dumps({"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(), "agent": AGENT,
                            "action": action, "outcome": outcome, "detail": detail}) + "\n")
    if _fleet_event:
        try:
            _fleet_event(AGENT, "govern", action, detail=detail, owner=OWNER, outcome=outcome)
        except Exception:
            pass


def dexec(entity, script, stdin=None):
    r = subprocess.run(["docker", "exec", "-i", f"{entity}-mc-container-exo3", "sh", "-c", script],
                       input=stdin, capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise RuntimeError(r.stderr.strip()[:300])
    return r.stdout


def secrets():
    try:
        return json.load(open(SECRETS))
    except Exception:
        return {}


def save_secrets(s):
    tmp = SECRETS + ".tmp"
    with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
        json.dump(s, f, indent=2)
    os.replace(tmp, SECRETS)


def cmd_store(a):
    secret = sys.stdin.read().strip()
    if not secret:
        sys.exit("no secret on stdin")
    fields = {}
    for f in a.field:
        k, _, v = f.partition("=")
        fields[k] = v if v else secret
    if not any(v == secret for v in fields.values()):
        sys.exit("one --field must take the stdin secret (no '=value')")
    s = secrets()
    for k, v in fields.items():
        s[f"{a.entity}__{a.system}__{k}"] = v
    save_secrets(s)
    doc = json.dumps({"system": a.system, **fields, "connected_at": datetime.datetime.now(datetime.timezone.utc).isoformat(), "by": "exo"})
    dexec(a.entity, f"umask 077; mkdir -p /data/connections && cat > /data/connections/{a.system}.json", doc)
    note = json.dumps({"id": "N-exo-" + a.system, "type": "task_note", "subject": f"task:SU-{a.system}",
                       "body": f"Connected by Exo ({', '.join(fields)} stored securely). Please run the test step above and mark Done.",
                       "owner": "Exo", "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()})
    dexec(a.entity, "cd /app/mission-control && node -e \"const fs=require('fs'),f='data/task-notes.json';let n=[];try{n=JSON.parse(fs.readFileSync(f))}catch{};"
                    "const r=JSON.parse(require('fs').readFileSync(0,'utf8'));if(!n.some(x=>x.id===r.id)){n.push(r);fs.writeFileSync(f,JSON.stringify(n,null,1))}\"", note)
    audit("connect_store", "ok", {"entity": a.entity, "system": a.system, "fields": list(fields)})
    print(f"stored {a.system} for {a.entity}: {', '.join(fields)}")


def cmd_list(a):
    out = dexec(a.entity, "ls /data/connections 2>/dev/null || true").split()
    keys = sorted(k for k in secrets() if k.startswith(a.entity + "__"))
    print(f"{a.entity} connections: {', '.join(x[:-5] for x in out) or 'none'}")
    for k in keys:
        print("  ", k)


def cmd_forget(a):
    keys = [k for k in secrets() if k.startswith(f"{a.entity}__{a.system}__")]
    print(f"remove {keys} and /data/connections/{a.system}.json")
    if not a.apply:
        print("DRY-RUN — re-run with --apply"); return
    s = secrets()
    for k in keys:
        s.pop(k, None)
    save_secrets(s)
    dexec(a.entity, f"rm -f /data/connections/{a.system}.json")
    audit("connect_forget", "ok", {"entity": a.entity, "system": a.system})
    print("removed")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)
    for n in ("store", "list", "forget"):
        s = sp.add_parser(n)
        s.add_argument("--entity", required=True)
        if n != "list":
            s.add_argument("--system", required=True, choices=sorted(SYSTEMS))
        if n == "store":
            s.add_argument("--field", action="append", required=True)
        if n == "forget":
            s.add_argument("--apply", action="store_true")
    a = p.parse_args()
    if not re.fullmatch(r"[a-z0-9]+", a.entity):
        sys.exit("bad entity")
    try:
        {"store": cmd_store, "list": cmd_list, "forget": cmd_forget}[a.cmd](a)
    except Exception as e:
        audit("connect_" + a.cmd, "fail", {"entity": a.entity, "err": str(e)[:300]})
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    main()
