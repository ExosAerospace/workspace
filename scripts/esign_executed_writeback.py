#!/usr/bin/env python3
"""E-sign completion write-back (Jon 2026-10-08, #3323 Scentience LSA).

When an MC e-sign envelope completes, server.js emails the signed PDF to the parties. Before this
script nothing wrote the execution back to Mission Control: the payload order kept saying "LSA sent"
and the task only got a copy when someone attached it by hand. This closes that loop:

  1. Payload orders whose envelope_id matches get lsa_executed_at / lsa_executed_pdf + a log entry.
  2. The executed PDF is attached to the owning task(s) labeled "EXECUTED — <title> ...".
     Task resolution: env.task_ids (set at envelope creation) → else the payload order's task whose
     title mentions countersign/sign + LSA/agreement → else the order's first task.
     If the same PDF is already on the task under another label, that record is relabeled instead.
  3. A dated "EXECUTED" line is appended to each task's description (Supabase).
  4. The envelope is stamped writebackAt / writebackTasks so it never runs twice.

Usage: esign_executed_writeback.py --envelope <id>   (server.js spawns this on completion)
       esign_executed_writeback.py --sweep [--dry-run] (backfill any completed envelope not yet written back)
"""
import argparse, hashlib, json, os, re, subprocess, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

WS = "/Users/exomac/.openclaw/workspace"
MC = os.path.join(WS, "mission-control")
ENVELOPES = os.path.join(MC, "data", "envelopes.json")
ORDERS = os.path.join(MC, "data", "payload-orders.json")
META = os.path.join(MC, "uploads", "_meta.json")
UPLOADS = os.path.join(MC, "uploads")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/tasks"
CDT = ZoneInfo("America/Chicago")


def jload(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def jsave(p, data):
    tmp = p + f".tmp{os.getpid()}"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, p)


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def _key():
    return json.load(open(SECRETS)).get("supabase_service_role_key")


def sb_task(tid):
    k = _key(); h = {"apikey": k, "Authorization": "Bearer " + k}
    url = SB + "?" + urllib.parse.urlencode({"id": f"eq.{tid}", "select": "id,title,description"})
    rows = json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=40))
    return rows[0] if rows else None


def sb_patch(tid, body):
    k = _key()
    h = {"apikey": k, "Authorization": "Bearer " + k, "Content-Type": "application/json", "Prefer": "return=minimal"}
    req = urllib.request.Request(SB + f"?id=eq.{tid}", data=json.dumps(body).encode(), headers=h, method="PATCH")
    urllib.request.urlopen(req, timeout=40)


def cdt(iso):
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(CDT)


def resolve_tasks(env, orders):
    if env.get("task_ids"):
        return [str(t) for t in env["task_ids"]]
    out = []
    for o in orders:
        ids = [t.strip() for t in str(o.get("task_ids") or "").split(",") if t.strip()]
        if not ids:
            continue
        # Best match: the "countersign" task (the signing action itself), then any sign + LSA task.
        best, best_score = ids[0], 0
        for tid in ids:
            try:
                t = sb_task(tid)
            except Exception:
                t = None
            if not t or not re.search(r"LSA|agreement|contract", t["title"], re.I):
                continue
            score = 2 if re.search(r"countersign", t["title"], re.I) else 1 if re.search(r"\bsign", t["title"], re.I) else 0
            if score > best_score:
                best, best_score = tid, score
        out.append(best)
        # Any other task of the order already carrying a copy gets its label fixed too.
        h = sha(os.path.join(MC, env["executedPdf"]))
        for m in jload(META, []):
            if str(m.get("task_id")) in ids and m.get("current") is not False:
                p = os.path.join(UPLOADS, m.get("stored_name", ""))
                if os.path.isfile(p) and os.path.getsize(p) == os.path.getsize(os.path.join(MC, env["executedPdf"])) and sha(p) == h:
                    out.append(str(m["task_id"]))
    return list(dict.fromkeys(out))


def writeback(env_id, dry=False):
    envs = jload(ENVELOPES, [])
    env = next((e for e in envs if e.get("id") == env_id), None)
    if not env:
        print(f"{env_id}: envelope not found"); return False
    if env.get("status") != "completed":
        print(f"{env_id}: not completed ({env.get('status')})"); return False
    if env.get("writebackAt"):
        print(f"{env_id}: already written back {env['writebackAt']} → tasks {env.get('writebackTasks')}"); return True
    pdf_rel = env.get("executedPdf")
    pdf = os.path.join(MC, pdf_rel) if pdf_rel else None
    if not pdf or not os.path.isfile(pdf):
        print(f"{env_id}: no executed PDF on disk yet (executedPdf={pdf_rel})"); return False

    done = cdt(env.get("completedAt") or env["signers"][-1].get("signedAt"))
    when = done.strftime("%Y-%m-%d %-I:%M %p CDT")
    signed_by = "; ".join(f"{s['name']} {cdt(s['signedAt']).strftime('%-m/%-d %-I:%M %p')}" for s in env["signers"] if s.get("signedAt"))
    label = f"EXECUTED — {env.get('title', 'Document')} (fully signed {done:%Y-%m-%d}, envelope {env_id})"
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # 1. payload orders
    od = jload(ORDERS, {"orders": []})
    olist = od["orders"] if isinstance(od, dict) else od
    orders = [o for o in olist if o.get("envelope_id") == env_id]
    for o in orders:
        if not o.get("lsa_executed_at"):
            o["lsa_executed_at"] = env.get("completedAt")
            o["lsa_executed_pdf"] = pdf_rel
            o.setdefault("log", []).append({"at": now, "by": "Exo", "email": "exo@exosaero.com",
                                            "action": "LSA fully executed",
                                            "detail": f"envelope {env_id} completed {when} ({signed_by}); executed PDF on record"})
            print(f"{env_id}: payload order {o['id']} marked executed")
    if orders and not dry:
        jsave(ORDERS, od)

    # 2. attach / relabel on owning task(s)
    tasks = resolve_tasks(env, orders)
    if not tasks:
        print(f"{env_id}: no owning task found (set task_ids on the envelope) — PDF stays in e-sign only")
    h = sha(pdf)
    for tid in tasks:
        meta = jload(META, [])
        existing = [m for m in meta if str(m.get("task_id")) == tid and m.get("current") is not False
                    and os.path.isfile(os.path.join(UPLOADS, m.get("stored_name", "")))
                    and sha(os.path.join(UPLOADS, m["stored_name"])) == h]
        if existing:
            for m in existing:
                if m.get("filename") != label:
                    print(f"{env_id}: task {tid} relabel '{m.get('filename')}' → '{label}'")
                    m["filename"] = label
            if not dry:
                jsave(META, meta)
        elif not dry:
            r = subprocess.run([sys.executable, os.path.join(WS, "scripts", "mc-attach.py"), "--task", tid, "--file", pdf,
                                "--doc-key", f"executed-{env_id}", "--title", label, "--by", "Exo (e-sign write-back)"],
                               capture_output=True, text=True)
            print(f"{env_id}: task {tid} attach → {(r.stdout or r.stderr).strip()[:200]}")
        else:
            print(f"{env_id}: task {tid} would attach '{label}'")

        # 3. task note
        try:
            t = sb_task(tid)
            note = f"\n\n— {done:%Y-%m-%d} (Exo, e-sign): EXECUTED. {env.get('title')} fully signed ({signed_by}), envelope {env_id}. Executed PDF attached as \"EXECUTED — …\"."
            if t and f"EXECUTED. {env.get('title')}" not in (t.get("description") or "") and not dry:
                sb_patch(tid, {"description": (t.get("description") or "") + note})
                print(f"{env_id}: task {tid} description noted")
        except Exception as e:
            print(f"{env_id}: task {tid} note failed: {e}")

    # 4. stamp envelope (reload: server may have written meanwhile)
    if not dry:
        envs = jload(ENVELOPES, [])
        e2 = next((e for e in envs if e.get("id") == env_id), None)
        if e2:
            e2["writebackAt"] = now
            e2["writebackTasks"] = tasks
            jsave(ENVELOPES, envs)
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--envelope")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.envelope:
        writeback(a.envelope, a.dry_run)
    elif a.sweep:
        for e in jload(ENVELOPES, []):
            if e.get("status") == "completed" and not e.get("writebackAt") and e.get("executedPdf"):
                writeback(e["id"], a.dry_run)
    else:
        ap.error("--envelope or --sweep")


if __name__ == "__main__":
    main()
