#!/usr/bin/env python3
"""
build-dossiers.py — Relationship Dossier auto-aggregator (Phase 2).

Reads config/relationships.json (curated editorial fields) and auto-enriches the
objective, freshness-prone facts:
  - last_touch : live IMAP scan of the relationship's contact emails (most recent
                 message in or out) -> date + subject.
  - agreements : curated list PLUS auto-scanned matches from submissions-archive/
                 (executed docs/NDAs whose filename contains a company alias).
  - pipeline   : cross-reference each opportunity_id against opportunities.json
                 (shows the raw pipeline status; may lag the curated status).

Writes mission-control/data/dossiers.json. Fail-soft: any source that errors is
skipped, the dossier still builds from the curated config.
"""
import imaplib, email, json, os, re, glob
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime

WS = "/Users/exomac/.openclaw/workspace"
CONFIG = os.path.join(WS, "config", "relationships.json")
OPPS   = os.path.join(WS, "mission-control", "data", "opportunities.json")
ARCHIVE = os.path.join(WS, "submissions-archive")
OUT    = os.path.join(WS, "mission-control", "data", "dossiers.json")
SECRETS = os.path.expanduser("~/.openclaw/secrets.json")
IMAP_HOST, IMAP_PORT, EMAIL_USER = "127.0.0.1", 1143, "jquinnexo@pm.me"


def dec(s):
    if not s:
        return ""
    out = ""
    for t, enc in decode_header(s):
        out += t.decode(enc or "utf-8", "ignore") if isinstance(t, bytes) else t
    return out


def load_json(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def imap_last_touch(conn, emails):
    """Most recent message (FROM or TO any of the emails). Returns 'YYYY-MM-DD — subject' or ''."""
    best_dt, best_sub = None, ""
    for addr in emails:
        if not addr:
            continue
        for key in ("FROM", "TO"):
            try:
                typ, data = conn.uid("search", None, key, addr)
            except Exception:
                continue
            uids = data[0].split() if data and data[0] else []
            for u in uids[-5:]:  # only the few newest per address
                typ, d = conn.uid("fetch", u, "(BODY.PEEK[HEADER.FIELDS (DATE SUBJECT)])")
                if not d or not d[0]:
                    continue
                msg = email.message_from_bytes(d[0][1])
                try:
                    dt = parsedate_to_datetime(msg["Date"]).replace(tzinfo=None)
                except Exception:
                    continue
                if best_dt is None or dt > best_dt:
                    best_dt, best_sub = dt, dec(msg["Subject"])
    if best_dt is None:
        return ""
    return f"{best_dt.strftime('%Y-%m-%d')} — {best_sub[:60]}"


def archive_agreements(aliases):
    """Scan submissions-archive filenames for executed docs / NDAs matching an alias."""
    hits = []
    for path in glob.glob(os.path.join(ARCHIVE, "*")):
        fn = os.path.basename(path)
        low = fn.lower()
        if not any(a.lower() in low for a in aliases):
            continue
        if any(k in low for k in ("nda", "executed", "loi", "safe", "agreement", "mnda")):
            hits.append(f"archive: {fn}")
    return hits


def main():
    cfg = load_json(CONFIG, {})
    rels = cfg.get("relationships", [])
    opps = {o["id"]: o for o in load_json(OPPS, {}).get("opportunities", [])}

    # one IMAP connection for the whole run (fail-soft)
    conn = None
    try:
        pw = load_json(SECRETS, {}).get("protonmail_bridge_smtp_password")
        if pw:
            conn = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)
            conn.starttls()
            conn.login(EMAIL_USER, pw)
            conn.select('"All Mail"', readonly=True)
    except Exception:
        conn = None

    out = []
    for r in rels:
        d = {k: r.get(k) for k in
             ("id", "name", "headline", "stage", "stage_color", "deals",
              "status", "next_step", "flags")}
        # contacts -> display strings (+ exclude styling marker)
        d["contacts"] = []
        emails = []
        for c in r.get("contacts", []):
            label = c.get("name", "")
            if c.get("role"):
                label += f" — {c['role']}"
            if c.get("email"):
                label += f" ({c['email']})"
                emails.append(c["email"])
            if c.get("exclude"):
                label = "❌ " + label
            d["contacts"].append(label)
        # agreements = curated + archive scan (deduped)
        agr = list(r.get("agreements", []))
        for h in archive_agreements(r.get("company_aliases", [])):
            if h not in agr:
                agr.append(h)
        d["agreements"] = agr
        # pipeline cross-reference from opportunities.json
        for oid in r.get("opportunity_ids", []):
            o = opps.get(oid)
            if o:
                d["deals"].append(f"[pipeline {oid}] {o.get('status','')}")
        # last touch (live IMAP) overrides nothing if unavailable
        lt = imap_last_touch(conn, emails) if conn else ""
        d["last_touch"] = lt or r.get("last_touch", "(no email match)")
        out.append(d)

    if conn:
        try:
            conn.logout()
        except Exception:
            pass

    # ── Preserve DD dossiers so a rebuild never wipes them (see log_dd.py / crm_dd_engine.py). ──
    # DD records live in two durable places: any existing dd-* dossier already in dossiers.json,
    # plus the authoritative dd-registry.json. Merge both in (curated relationships win on id clash).
    have_ids = {d.get("id") for d in out}
    try:
        prev = load_json(OUT, {}).get("dossiers", [])
        for d in prev:
            if str(d.get("id", "")).startswith("dd-") and d.get("id") not in have_ids:
                out.append(d); have_ids.add(d.get("id"))
    except Exception:
        pass
    try:
        COLOR = {"pass": "#2E7D32", "caution": "#B8860B", "fail": "#B00020"}
        reg = load_json(os.path.join(WS, "mission-control", "data", "dd-registry.json"), {})
        for dom, v in (reg.items() if isinstance(reg, dict) else []):
            if not isinstance(v, dict):
                continue
            name = v.get("company") or dom
            sid = "dd-" + re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
            if sid in have_ids:
                continue
            verdict = v.get("status") or v.get("verdict") or "caution"
            out.append({"id": sid, "name": name, "headline": (v.get("summary") or "")[:140],
                        "stage": f"DD {verdict.title()}", "stage_color": COLOR.get(verdict, "#888"),
                        "deals": [], "status": f"DD complete ({verdict}) {v.get('date','')}",
                        "next_step": v.get("next_step", ""), "flags": [f"DD {verdict.upper()} {v.get('date','')}: {v.get('summary','')}"],
                        "contacts": [], "agreements": [], "last_touch": v.get("date", ""), "dd": v})
            have_ids.add(sid)
    except Exception:
        pass

    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M")
    payload = {"generated_display": stamp,
               "note": "Auto-aggregated by build-dossiers.py from config/relationships.json + opportunities.json + live email + submissions-archive.",
               "dossiers": out}
    tmp = OUT + ".tmp"
    with open(tmp, "w") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    os.replace(tmp, OUT)
    print(f"Wrote {OUT}: {len(out)} dossiers @ {stamp}")


if __name__ == "__main__":
    main()
