#!/usr/bin/env python3
"""
proposal_freshness_check.py — "is this the newest copy?" gate before anything is sent.

Jon 10/7: "How do we not send an outdated one?"  A file is STALE if either
  (a) the same doc (mc-attach doc_key) on an MC task has a newer current version, or
  (b) drafts/ holds a same-stem file with a later embedded ISO date.

  proposal_freshness_check.py <file> [<file> ...]   exit 1 if any file is stale
  proposal_freshness_check.py --open-decisions      scan open/delegated send Decisions
"""
import importlib.util, json, os, re, sys

WS = "/Users/exomac/.openclaw/workspace"
META = os.path.join(WS, "mission-control", "uploads", "_meta.json")
DEC = os.path.join(WS, "mission-control", "data", "decisions.json")
DRAFTS = os.path.join(WS, "drafts")

_sp = importlib.util.spec_from_file_location("mc_attach", os.path.join(WS, "scripts", "mc-attach.py"))
_ma = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(_ma)
doc_date = _ma.doc_date


def stem(name):
    """Doc identity for draft comparison: filename minus ISO date / _vN / DRAFT tokens.
    (Stricter than mc-attach's slug, which would fold OPP_PAY-5095 and OPP_PAY-4618 together.)"""
    s = os.path.splitext(os.path.basename(name))[0].lower()
    s = re.sub(r"[\s_.\-]*\(?\d{4}-\d{2}-\d{2}\)?", "", s)
    s = re.sub(r"[\s_.\-]+(?:v|rev)\d+(\.\d+)*$|[\s_.\-]+draft$", "", s)
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def rank(name):
    """(ISO date, _vN/_revN) so a same-day _v2 outranks _v1."""
    m = re.search(r"[\s_.\-](?:v|rev)(\d+)(?:\.\d+)*$", os.path.splitext(os.path.basename(name))[0], re.I)
    return (doc_date(name) or "", int(m.group(1)) if m else 1)


# Copy rules every outbound proposal/outreach must pass (USER.md claim caveat, Lizi 10/5 timing rule,
# AGENTS.md "no turnaround times unless sourced"). (pattern, replacement) — applied by copy_fix().
COPY_RULES = [
    (r"one of only three FAA-licensed reusable rocket launch (?:providers|companies)(?: in the (?:US|U\.S\.|country|United States))?",
     "one of only three FAA-licensed vertical-takeoff reusable rocket providers with demonstrated recovery and reflight"),
    (r"\b(?:in |for |by )?(?:March|Mar\.?) 2027\b", lambda m: ("in " if m.group(0).lower().startswith("in ") else
                                                               "for " if m.group(0).lower().startswith("for ") else
                                                               "by " if m.group(0).lower().startswith("by ") else "") + "early 2027"),
    (r",? and with fewer than 3,000 parts, turnaround is measured in weeks, not quarters", ", and the vehicle is built for reflight"),
    (r",? turnaround is measured in weeks,? not quarters", ""),
    # 10/8–10/12 payload drafts kept re-introducing unsourced turnaround claims
    (r"\s*Integration lead times are measured in weeks\.", ""),
    (r"\s+within days\b", ""),
]


def copy_fix(text):
    """Return (fixed_text, [rule hits]) for one string."""
    hits = []
    for pat, rep in COPY_RULES:
        text, n = re.subn(pat, rep, text, flags=re.I)
        if n:
            hits.append(f"{n}x {pat[:40]}")
    return text, hits


def check(path):
    """Return list of reasons the file is stale (empty = fresh)."""
    fn = os.path.basename(re.sub(r"^\d{13}_", "", os.path.basename(path)))
    key, d, ext = _ma.slug(fn), doc_date(fn), os.path.splitext(fn)[1].lower()
    why = []
    try:
        meta = json.load(open(META))
    except Exception:
        meta = []
    for m in meta:
        if m.get("doc_key") != key or m.get("current") is False or stem(m.get("stored_name", "")) != stem(fn):
            continue
        md = doc_date(m.get("stored_name"))
        if d and md and md > d and os.path.splitext(m.get("stored_name", ""))[1].lower() == ext:
            why.append(f"task #{m.get('task_id')} current version is {m.get('filename')} ({md})")
    if d and os.path.isdir(DRAFTS):
        for f in os.listdir(DRAFTS):
            if doc_date(f) and rank(f) > rank(fn) and stem(f) == stem(fn) and os.path.splitext(f)[1].lower() == ext:
                why.append(f"newer draft exists: drafts/{f}")
    return why


def latest_copy(path):
    """Newest same-doc copy in drafts/ (by embedded ISO date), else the path itself."""
    fn = os.path.basename(path); d = doc_date(fn); ext = os.path.splitext(fn)[1].lower()
    if not d or not os.path.isdir(DRAFTS):
        return path
    best, br = path, rank(fn)
    for f in os.listdir(DRAFTS):
        if doc_date(f) and rank(f) > br and stem(f) == stem(fn) and os.path.splitext(f)[1].lower() == ext:
            best, br = os.path.join(DRAFTS, f), rank(f)
    return best


def open_decision_files():
    rx = re.compile(r"((?:drafts|captures|mission-control/uploads)/[\w./()\- ]+\.(?:docx|pdf|xlsx|pptx))")
    try:
        d = json.load(open(DEC))
    except Exception:
        return []
    d = d if isinstance(d, list) else d.get("decisions", [])
    out = []
    for it in d:
        if str(it.get("status", "")).lower() not in ("open", "delegated", "reassigning"):
            continue
        blob = " ".join(str(it.get(k, "")) for k in ("title", "question", "proposedAction", "context", "note"))
        for p in set(rx.findall(blob)):
            out.append((it.get("id"), it.get("title", ""), os.path.join(WS, p)))
    return out


def main():
    args = sys.argv[1:]
    stale = 0
    if args == ["--open-decisions"]:
        for did, title, p in open_decision_files():
            why = check(p)
            if why:
                stale += 1
                print(f"STALE {did} | {title[:70]} | {os.path.basename(p)}\n   - " + "\n   - ".join(why))
        print(f"{stale} open Decision(s) reference a stale file")
    else:
        for p in args:
            why = check(p)
            stale += bool(why)
            print(("STALE " if why else "FRESH ") + os.path.basename(p) + "".join("\n   - " + w for w in why))
    sys.exit(1 if stale else 0)


if __name__ == "__main__":
    main()
