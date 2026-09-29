#!/usr/bin/env python3
"""
MC RESTORE — put a deleted Mission Control record back from the recycle bin
(exo3 remedy 2026-09-28, recoverable deletes). Human-run tool: a person chooses what to restore.

  python3 scripts/mc_restore.py --list [--since 2026-09-01] [--type tasks] [--id 123]
  python3 scripts/mc_restore.py --show <recycle_id>
  python3 scripts/mc_restore.py --restore <recycle_id> [--force]

Supabase-backed entries are upserted back into their table. JSON-backed entries are
re-inserted into their file (atomic write). Refuses if a live record with the same id
already exists, unless --force (which overwrites the live record with the snapshot).
Uploads: the parked binary is moved back into mission-control/uploads/.
Tasks: documents detached at delete time are re-attached.
Every restore is logged to mission-control/data/recycle-bin/restores.jsonl.
"""
import os, sys, json, argparse, datetime, shutil, urllib.request, urllib.parse, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mc_recycle  # noqa: E402

SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
SB = "https://pcrgpuoljylqcumijvnw.supabase.co/rest/v1/"


def sb(path, method="GET", body=None, prefer="return=representation"):
    key = json.load(open(SECRETS))["supabase_service_role_key"]
    r = urllib.request.Request(SB + path, data=(json.dumps(body).encode() if body is not None else None),
                               method=method, headers={"apikey": key, "Authorization": "Bearer " + key,
                                                       "Content-Type": "application/json", "Prefer": prefer})
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw.strip() else []


def find(rid):
    for e in mc_recycle.iter_entries():
        if e.get("recycle_id") == rid:
            return e
    return None


def _json_path(src):
    fp = os.path.normpath(os.path.join(mc_recycle.MC_DIR, src["file"]))
    if not fp.startswith(mc_recycle.MC_DIR + os.sep):
        raise SystemExit(f"refusing: source file outside mission-control: {src['file']}")
    return fp


def _atomic_write(fp, obj):
    tmp = fp + ".restore.tmp"
    with open(tmp, "w") as fh:
        json.dump(obj, fh, indent=2)
    os.replace(tmp, fp)


def restore_supabase(e, force):
    src, rec = e["source"], e["record"]
    table, key = src["table"], src.get("key", "id")
    if not rec or rec.get(key) is None:
        raise SystemExit("refusing: snapshot has no record/key")
    kv = urllib.parse.quote(str(rec[key]), safe="")
    live = sb(f"{table}?{key}=eq.{kv}&select={key}")
    if live and not force:
        raise SystemExit(f"refusing: live {table} row {key}={rec[key]} already exists (use --force to overwrite)")
    sb(f"{table}?on_conflict={key}", "POST", rec, prefer="resolution=merge-duplicates,return=representation")
    return f"upserted {table} {key}={rec[key]}"


def restore_json(e, force):
    src, rec = e["source"], e["record"]
    key = src.get("key", "id")
    fp = _json_path(src)
    doc = json.load(open(fp)) if os.path.exists(fp) else ([] if not src.get("path") else {})
    # Walk to the containing array, creating intermediate dicts / the array if missing.
    parent, arr = None, doc
    pth = src.get("path") or []
    for i, k in enumerate(pth):
        parent = arr
        if k not in parent or parent[k] is None:
            parent[k] = [] if i == len(pth) - 1 else {}
        arr = parent[k]
    if not isinstance(arr, list):
        raise SystemExit(f"refusing: {src['file']} path {pth} is not a list")
    idx = next((i for i, x in enumerate(arr) if isinstance(x, dict) and str(x.get(key)) == str(rec.get(key))), None)
    if idx is not None and not force:
        raise SystemExit(f"refusing: live record {key}={rec.get(key)} already exists in {src['file']} (use --force to overwrite)")
    # Uploads: move the parked binary back before touching metadata.
    ex = e.get("extra") or {}
    if ex.get("parked_file"):
        parked = os.path.join(mc_recycle.MC_DIR, ex["parked_file"])
        dest = os.path.join(mc_recycle.MC_DIR, "uploads", rec.get("stored_name") or "")
        if os.path.exists(dest) and not force:
            raise SystemExit(f"refusing: upload file already exists at {dest} (use --force)")
        if not os.path.exists(parked):
            raise SystemExit(f"refusing: parked binary missing: {parked}")
        shutil.move(parked, dest)
    if idx is not None:
        arr[idx] = rec
    else:
        arr.append(rec)
    _atomic_write(fp, doc)
    return f"re-inserted {key}={rec.get(key)} into {src['file']}" + (" (+ binary)" if ex.get("parked_file") else "")


def reattach_task_docs(e):
    ups = (e.get("extra") or {}).get("detached_uploads") or []
    if not ups:
        return ""
    fp = os.path.join(mc_recycle.MC_DIR, "uploads", "_meta.json")
    meta = json.load(open(fp))
    prev = {str(u["id"]): u for u in ups}
    n = 0
    for m in meta:
        u = prev.get(str(m.get("id")))
        if u and m.get("task_id") is None and str(m.get("deleted_task_id")) == str(e["id"]):
            m["task_id"] = u.get("task_id", e["id"])
            if u.get("current", "__absent__") == "__absent__":
                m.pop("current", None)
            else:
                m["current"] = u["current"]
            m.pop("deleted_task_id", None); m.pop("detached_at", None)
            n += 1
    if n:
        _atomic_write(fp, meta)
    return f"; re-attached {n} doc(s)"


def main():
    ap = argparse.ArgumentParser(description="Restore deleted Mission Control records from the recycle bin")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true")
    g.add_argument("--show", metavar="RECYCLE_ID")
    g.add_argument("--restore", metavar="RECYCLE_ID")
    ap.add_argument("--since", help="YYYY-MM-DD (list filter)")
    ap.add_argument("--type", help="record type / table (list filter)")
    ap.add_argument("--id", help="original record id (list filter)")
    ap.add_argument("--force", action="store_true", help="overwrite a live record with the same id")
    a = ap.parse_args()

    if a.list:
        n = 0
        for e in mc_recycle.iter_entries():
            if a.since and (e.get("deleted_at") or "") < a.since: continue
            if a.type and a.type not in (e.get("type"), (e.get("source") or {}).get("table")): continue
            if a.id and str(e.get("id")) != str(a.id): continue
            rec = e.get("record") or {}
            label = rec.get("title") or rec.get("name") or rec.get("filename") or rec.get("email") or rec.get("organization") or ""
            print(f"{e['recycle_id']}  {e.get('deleted_at','')[:19]}  {e.get('type',''):<16} id={e.get('id')}  by={e.get('who')}  {str(label)[:60]}")
            n += 1
        print(f"-- {n} entr{'y' if n == 1 else 'ies'}")
        return
    if a.show:
        e = find(a.show)
        if not e: sys.exit(f"not found: {a.show}")
        print(json.dumps(e, indent=2)); return

    e = find(a.restore)
    if not e: sys.exit(f"not found: {a.restore}")
    kind = (e.get("source") or {}).get("kind")
    try:
        if kind == "supabase":
            msg = restore_supabase(e, a.force)
            if e.get("type") == "tasks":
                msg += reattach_task_docs(e)
        elif kind == "json":
            msg = restore_json(e, a.force)
        else:
            sys.exit(f"unsupported source kind: {kind}")
    except urllib.error.HTTPError as err:
        sys.exit(f"supabase error {err.code}: {err.read().decode()[:500]}")
    os.makedirs(mc_recycle.RECYCLE_DIR, mode=0o700, exist_ok=True)
    with open(os.path.join(mc_recycle.RECYCLE_DIR, "restores.jsonl"), "a") as fh:
        fh.write(json.dumps({"restored_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             "recycle_id": e["recycle_id"], "type": e.get("type"), "id": e.get("id"),
                             "by": os.environ.get("USER", "unknown"), "force": a.force, "result": msg}) + "\n")
    print(f"OK {e['recycle_id']}: {msg}")


if __name__ == "__main__":
    main()
