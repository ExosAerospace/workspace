#!/usr/bin/env python3
"""minute_book.py — corporate Minute Book for the Exos companies (compliance + business-audit record).

Files board/member minutes and written consents into
  data-room/Corporate/<Entity>/Minute_Book/YYYY-MM-DD_<Body>_<Type>_<Kind>[_vN].<ext>  (+ PDF render)
records each in data-room/Corporate/minute-book-register.json with sha256, makes the files read-only,
and rebuilds a per-entity MINUTE_BOOK_INDEX.md. Records are append-only: a corrected or adopted copy
is filed as a new version; nothing is overwritten or deleted.

  minute_book.py file <path> --entity east --date 2026-10-06 --type special [--body board]
                       [--kind minutes|consent|notice|agenda] [--status draft|adopted] [--note "..."]
  minute_book.py adopt <record-id> --on 2026-11-03 [--note "approved at regular meeting"]
  minute_book.py verify          # re-hash every filed record; non-zero exit on any mismatch/missing file
  minute_book.py list [--entity east]
  minute_book.py --selftest
Owner: John Quinn. Registered in mission-control/data/agent-registry.json as minute-book-exo3.
"""
import os, sys, json, shutil, hashlib, argparse, subprocess, datetime, tempfile, stat

WS = "/Users/exomac/.openclaw/workspace"
CORP = os.path.join(WS, "data-room", "Corporate")
FLEET = os.path.join(WS, "logs", "fleet_log.jsonl")

ENTITIES = {
    "east":     ("Exos_Aerospace_Systems_and_Technologies_Inc", "Exos Aerospace Systems & Technologies, Inc."),
    "eai_llc":  ("Exos_Aerospace_Investments_LLC",              "Exos Aerospace Investments, LLC (Wyoming)"),
    "japan_kk": ("Exos_Aerospace_Japan_KK",                     "Exos Aerospace Japan K.K."),
    "italia":   ("Exos_Aerospace_Italia_Srl",                   "Exos Aerospace Italia, Srl"),
}
TYPES = ("special", "regular", "annual", "organizational", "written-consent")
BODIES = ("board", "members", "shareholders", "committee")
KINDS = ("minutes", "consent", "notice", "agenda", "resolution")


def now():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def fleet(action, detail, outcome="ok"):
    try:
        with open(FLEET, "a") as f:
            f.write(json.dumps({"ts": now(), "agent": "minute-book-exo3", "action": action,
                                "detail": detail, "outcome": outcome}) + "\n")
    except Exception:
        pass


def reg_path(corp):
    return os.path.join(corp, "minute-book-register.json")


def load(corp):
    p = reg_path(corp)
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return {"schema": 1, "records": []}


def save(corp, reg):
    # read-before-write is done by caller (load); write via temp + atomic replace, never truncate in place
    p = reg_path(corp)
    fd, tmp = tempfile.mkstemp(dir=corp, prefix=".mbreg-")
    with os.fdopen(fd, "w") as f:
        json.dump(reg, f, indent=1)
    os.replace(tmp, p)


def make_readonly(p):
    os.chmod(p, stat.S_IRUSR | stat.S_IRGRP)


def render_pdf(src, outdir):
    if src.lower().endswith(".pdf"):
        return None
    try:
        subprocess.run(["soffice", "--headless", "--convert-to", "pdf", "--outdir", outdir, src],
                       capture_output=True, timeout=180)
    except Exception:
        return None
    pdf = os.path.splitext(src)[0] + ".pdf"
    return pdf if os.path.exists(pdf) else None


def write_index(corp, reg, key):
    folder, legal = ENTITIES[key]
    mb = os.path.join(corp, folder, "Minute_Book")
    os.makedirs(mb, exist_ok=True)
    rows = sorted([r for r in reg["records"] if r["entity"] == key], key=lambda r: (r["meeting_date"], r["version"]))
    L = [f"# Minute Book — {legal}", "",
         "Append-only record of board/member meetings and written consents. Files are read-only; sha256 below is "
         "verified by `scripts/minute_book.py verify`. Corrections and adopted copies are filed as new versions.", "",
         "| ID | Date | Body | Type | Kind | Ver | Status | File | sha256 (first 12) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['id']} | {r['meeting_date']} | {r['body']} | {r['type']} | {r['kind']} | v{r['version']} | "
                 f"{r['status']}{(' ' + r['adopted_on']) if r.get('adopted_on') else ''} | {os.path.basename(r['file'])} | {r['sha256'][:12]} |")
    p = os.path.join(mb, "MINUTE_BOOK_INDEX.md")
    fd, tmp = tempfile.mkstemp(dir=mb, prefix=".idx-")
    with os.fdopen(fd, "w") as f:
        f.write("\n".join(L) + "\n")
    os.replace(tmp, p)


def file_record(src, entity, date, mtype, body="board", kind="minutes", status="draft", note="", corp=CORP):
    if entity not in ENTITIES:
        raise SystemExit(f"unknown entity {entity}; one of {list(ENTITIES)}")
    if mtype not in TYPES or body not in BODIES or kind not in KINDS or status not in ("draft", "adopted"):
        raise SystemExit("bad --type/--body/--kind/--status")
    datetime.date.fromisoformat(date)
    if not os.path.exists(src):
        raise SystemExit(f"missing {src}")
    reg = load(corp)
    digest = sha256(src)
    dup = [r for r in reg["records"] if r["sha256"] == digest]
    if dup:
        print(f"already filed as {dup[0]['id']} ({dup[0]['file']})")
        return dup[0]
    folder, _ = ENTITIES[entity]
    mb = os.path.join(corp, folder, "Minute_Book")
    os.makedirs(mb, exist_ok=True)
    same = [r for r in reg["records"] if r["entity"] == entity and r["meeting_date"] == date
            and r["body"] == body and r["type"] == mtype and r["kind"] == kind]
    ver = len(same) + 1
    ext = os.path.splitext(src)[1].lower()
    base = f"{date}_{body.capitalize()}_{mtype.replace('-', '_').title()}_{kind.capitalize()}" + (f"_v{ver}" if ver > 1 else "")
    dst = os.path.join(mb, base + ext)
    shutil.copy2(src, dst)
    pdf = render_pdf(dst, mb)
    rec = {"id": f"MB-{entity}-{date}-{body[:1]}{mtype[:3]}-{kind[:3]}-v{ver}", "entity": entity,
           "entity_name": ENTITIES[entity][1], "meeting_date": date, "body": body, "type": mtype, "kind": kind,
           "version": ver, "status": status, "file": os.path.relpath(dst, WS) if dst.startswith(WS) else dst,
           "sha256": sha256(dst), "pdf": (os.path.relpath(pdf, WS) if pdf and pdf.startswith(WS) else pdf),
           "pdf_sha256": sha256(pdf) if pdf else None, "source": os.path.basename(src), "filed_at": now(),
           "filed_by": "Exo (minute-book-exo3)", "note": note}
    for p in (dst, pdf):
        if p:
            make_readonly(p)
    reg["records"].append(rec)
    save(corp, reg)
    write_index(corp, reg, entity)
    fleet("file", {"id": rec["id"], "file": rec["file"], "sha256": rec["sha256"]})
    return rec


def adopt(rid, on, note="", corp=CORP):
    reg = load(corp)
    r = next((x for x in reg["records"] if x["id"] == rid), None)
    if not r:
        raise SystemExit(f"no record {rid}")
    datetime.date.fromisoformat(on)
    r["status"], r["adopted_on"] = "adopted", on
    r.setdefault("history", []).append({"ts": now(), "event": "adopted", "on": on, "note": note})
    save(corp, reg)
    write_index(corp, reg, r["entity"])
    fleet("adopt", {"id": rid, "on": on})
    return r


def verify(corp=CORP, quiet=False):
    reg = load(corp)
    bad = []
    for r in reg["records"]:
        for key, hkey in (("file", "sha256"), ("pdf", "pdf_sha256")):
            p = r.get(key)
            if not p:
                continue
            ap = p if os.path.isabs(p) else os.path.join(WS, p)
            if not os.path.exists(ap):
                bad.append((r["id"], p, "MISSING"))
            elif sha256(ap) != r[hkey]:
                bad.append((r["id"], p, "HASH MISMATCH"))
    fleet("verify", {"records": len(reg["records"]), "problems": len(bad)}, "ok" if not bad else "fail")
    if not quiet:
        print(f"minute book: {len(reg['records'])} records, {len(bad)} problems")
        for b in bad:
            print("  ", *b)
    return bad


def selftest():
    ok = True
    def t(name, cond):
        nonlocal ok
        ok &= bool(cond)
        print(("PASS " if cond else "FAIL ") + name)
    with tempfile.TemporaryDirectory() as d:
        src = os.path.join(d, "m.pdf")
        with open(src, "wb") as f:
            f.write(b"%PDF-1.4 test minutes")
        r = file_record(src, "east", "2026-10-06", "special", corp=d)
        t("filed + hashed", r["sha256"] == sha256(src) and os.path.exists(os.path.join(d, ENTITIES["east"][0], "Minute_Book")))
        t("read-only", not os.access(os.path.join(WS, r["file"]) if not os.path.isabs(r["file"]) else r["file"], os.W_OK))
        r2 = file_record(src, "east", "2026-10-06", "special", corp=d)
        t("duplicate not re-filed", r2["id"] == r["id"] and len(load(d)["records"]) == 1)
        src2 = os.path.join(d, "m2.pdf")
        with open(src2, "wb") as f:
            f.write(b"%PDF-1.4 corrected minutes")
        r3 = file_record(src2, "east", "2026-10-06", "special", corp=d)
        t("correction = new version, original kept", r3["version"] == 2 and len(load(d)["records"]) == 2)
        t("verify clean", verify(d, quiet=True) == [])
        p = r["file"] if os.path.isabs(r["file"]) else os.path.join(WS, r["file"])
        os.chmod(p, 0o600)
        with open(p, "ab") as f:
            f.write(b"tamper")
        t("verify catches tamper", any(x[2] == "HASH MISMATCH" for x in verify(d, quiet=True)))
        adopt(r3["id"], "2026-11-03", corp=d)
        t("adopt recorded", next(x for x in load(d)["records"] if x["id"] == r3["id"])["status"] == "adopted")
    print("SELFTEST", "OK" if ok else "FAILED")
    return 0 if ok else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    f = sp.add_parser("file"); f.add_argument("path"); f.add_argument("--entity", required=True)
    f.add_argument("--date", required=True); f.add_argument("--type", required=True)
    f.add_argument("--body", default="board"); f.add_argument("--kind", default="minutes")
    f.add_argument("--status", default="draft"); f.add_argument("--note", default="")
    a = sp.add_parser("adopt"); a.add_argument("id"); a.add_argument("--on", required=True); a.add_argument("--note", default="")
    sp.add_parser("verify")
    l = sp.add_parser("list"); l.add_argument("--entity")
    args = ap.parse_args(argv)
    if args.cmd == "file":
        r = file_record(args.path, args.entity, args.date, args.type, args.body, args.kind, args.status, args.note)
        print(json.dumps(r, indent=1))
    elif args.cmd == "adopt":
        print(json.dumps(adopt(args.id, args.on, args.note), indent=1))
    elif args.cmd == "verify":
        return 1 if verify() else 0
    elif args.cmd == "list":
        for r in load(CORP)["records"]:
            if not args.entity or r["entity"] == args.entity:
                print(r["id"], r["meeting_date"], r["status"], r["file"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
