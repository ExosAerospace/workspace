#!/usr/bin/env python3
"""
MC RECYCLE BIN — Python side (exo3 remedy 2026-09-28, recoverable deletes).

Same store and entry shape as mission-control/lib/recycle.js:
  mission-control/data/recycle-bin/YYYY-MM-DD.jsonl  (one JSON entry per line)
  entry = {recycle_id, deleted_at, type, id, who, route, source, record, extra}

Scripts that hard-delete MC records call record() / snapshot_rows() BEFORE deleting.
record() fsyncs and raises on failure, so the caller must not delete if it raises.

  python3 scripts/mc_recycle.py --purge [--days 90]   # drop recycle entries older than N days
"""
import os, sys, json, secrets, datetime, re, argparse

WS = os.path.expanduser("~/.openclaw/workspace")
MC_DIR = os.path.join(WS, "mission-control")
RECYCLE_DIR = os.path.join(MC_DIR, "data", "recycle-bin")
FILES_DIR = os.path.join(RECYCLE_DIR, "files")
RETENTION_DAYS = 90


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def record(type_, id_, rec, source, who="system", route=None, extra=None):
    os.makedirs(RECYCLE_DIR, mode=0o700, exist_ok=True)
    now = _now()
    iso = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    rid = "rb_" + now.strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(4)
    entry = {"recycle_id": rid, "deleted_at": iso, "type": type_,
             "id": None if id_ is None else str(id_), "who": who, "route": route,
             "source": source, "record": rec, "extra": extra}
    fp = os.path.join(RECYCLE_DIR, now.strftime("%Y-%m-%d") + ".jsonl")
    fd = os.open(fp, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    try:
        os.write(fd, (json.dumps(entry) + "\n").encode())
        os.fsync(fd)
    finally:
        os.close(fd)
    return rid


def snapshot_rows(table, rows, key="id", type_=None, who="system", route=None, extra=None):
    """Record already-fetched Supabase rows (full rows!) before deleting them."""
    return [record(type_ or table, r.get(key), r, {"kind": "supabase", "table": table, "key": key},
                   who=who, route=route, extra=extra) for r in rows]


def iter_entries():
    if not os.path.isdir(RECYCLE_DIR):
        return
    for f in sorted(os.listdir(RECYCLE_DIR)):
        if not re.match(r"^\d{4}-\d{2}-\d{2}\.jsonl$", f):
            continue
        with open(os.path.join(RECYCLE_DIR, f)) as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        yield json.loads(line)
                    except ValueError:
                        continue


def purge(days=RETENTION_DAYS):
    """Remove ONLY recycle-bin day files / parked binaries older than `days`."""
    cutoff = (_now() - datetime.timedelta(days=days)).strftime("%Y%m%d")
    removed = []
    if os.path.isdir(RECYCLE_DIR):
        for f in os.listdir(RECYCLE_DIR):
            m = re.match(r"^(\d{4})-(\d{2})-(\d{2})\.jsonl$", f)
            if m and "".join(m.groups()) < cutoff:
                os.remove(os.path.join(RECYCLE_DIR, f)); removed.append(f)
    if os.path.isdir(FILES_DIR):
        for f in os.listdir(FILES_DIR):
            m = re.match(r"^rb_(\d{8})", f)
            if m and m.group(1) < cutoff:
                os.remove(os.path.join(FILES_DIR, f)); removed.append("files/" + f)
    return removed


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="MC recycle bin maintenance")
    ap.add_argument("--purge", action="store_true")
    ap.add_argument("--days", type=int, default=RETENTION_DAYS)
    a = ap.parse_args()
    if not a.purge:
        ap.print_help(); sys.exit(0)
    if a.days < 1:
        sys.exit("--days must be >= 1")
    gone = purge(a.days)
    print(f"[{_now().isoformat()}] mc_recycle purge (>{a.days}d): removed {len(gone)}" + (": " + ", ".join(gone) if gone else ""))
