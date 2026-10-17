#!/usr/bin/env python3
"""google-media-exo3: spend + accountability guard for paid Google media generation
(scripts/gen_vid_veo.py = Veo video, scripts/gen_img.py = Gemini image).

Every paid call must:
  1. name an MC task (EXO_TASK=<n> env)            -> else REFUSED (exit 1, nothing sent)
  2. fit under the local monthly cap                 -> else REFUSED (exit 1)
     (config/google-media-spend.json; the AI Studio project cap is the outer stop)
  3. record its estimated cost in state/google-media-spend.json + fleet telemetry.

Why: Oct 5 2026 IDJ video iterations spent ~$39 of Veo in one day with no ledger,
no task link and no cap (Jon 10/17).

  google_media_guard.py --status      # month spend vs cap
  google_media_guard.py --selftest    # exo3 eval (offline, no API call)
"""
import datetime, json, os, sys

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = os.path.join(WS, "config", "google-media-spend.json")
STATE = os.path.join(WS, "state", "google-media-spend.json")
AGENT, OWNER = "google-media-exo3", "John Quinn"

# USD estimates from https://ai.google.dev/gemini-api/docs/pricing (checked 2026-10-17)
VEO_PER_SEC = {"veo-3.1-generate-preview": 0.40, "veo-3.1-fast-generate-preview": 0.12,
               "veo-3.1-lite-generate-preview": 0.08}
IMG_PER_IMAGE = {"gemini-3-pro-image-preview": 0.134}
DEFAULT_VEO, DEFAULT_IMG = 0.40, 0.134  # unknown model -> assume the expensive tier


class Refused(SystemExit):
    pass


def estimate(kind, model, seconds=8):
    if kind == "video":
        return round(VEO_PER_SEC.get(model, DEFAULT_VEO) * float(seconds), 4)
    return IMG_PER_IMAGE.get(model, DEFAULT_IMG)


def load_cfg(path=CFG):
    try:
        return json.load(open(path))
    except Exception:
        return {"monthly_cap_usd": 50.0}


def month_key(today=None):
    return (today or datetime.date.today()).strftime("%Y-%m")


def _load(state_path):
    try:
        return json.load(open(state_path))
    except Exception:
        return {}


def spend(state_path=STATE, today=None):
    return float(_load(state_path).get(month_key(today), {}).get("usd", 0.0))


def record(usd, entry, state_path=STATE, today=None):
    s = _load(state_path)
    m = s.setdefault(month_key(today), {"usd": 0.0, "calls": []})
    m["usd"] = round(m["usd"] + usd, 4)
    m["calls"].append({**entry, "usd": usd, "ts": datetime.datetime.now().isoformat(timespec="seconds")})
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    tmp = state_path + ".tmp"
    json.dump(s, open(tmp, "w"), indent=1)
    os.replace(tmp, state_path)


def fleet(action, detail, outcome=None, level="info"):
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from fleet_log import event
        event(AGENT, "govern", action, detail=detail, owner=OWNER, outcome=outcome, level=level)
    except Exception:
        pass


def check(kind, model, seconds=8, out="", task=None, state_path=STATE, cfg_path=CFG, today=None, quiet=False):
    """Pre-flight. Returns the estimated USD, or raises Refused. Call BEFORE the API request."""
    task = task if task is not None else os.environ.get("EXO_TASK", "").strip().lstrip("#")
    usd = estimate(kind, model, seconds)
    detail = {"kind": kind, "model": model, "seconds": seconds if kind == "video" else None,
              "out": os.path.basename(out), "task": task, "est_usd": usd}
    if not task:
        if not quiet:
            fleet("refused_no_task", detail, outcome="refused", level="warn")
        raise Refused(f"REFUSED: paid Google {kind} generation needs EXO_TASK=<MC task #> (est ${usd:.2f}).")
    cap = float(load_cfg(cfg_path).get("monthly_cap_usd", 50.0))
    spent = spend(state_path, today)
    if spent + usd > cap:
        if not quiet:
            fleet("refused_cap", {**detail, "spent": spent, "cap": cap}, outcome="refused", level="warn")
        raise Refused(f"REFUSED: Google media cap ${cap:.0f} for {month_key(today)} "
                      f"(spent ${spent:.2f} + this ${usd:.2f}). Raise config/google-media-spend.json only on Jon's OK.")
    return usd


def charge(kind, model, usd, seconds=8, out="", ok=True, state_path=STATE, today=None, quiet=False):
    """Record the call after submission (billed whether or not we keep the output)."""
    task = os.environ.get("EXO_TASK", "").strip().lstrip("#")
    entry = {"kind": kind, "model": model, "out": os.path.basename(out), "task": task, "ok": ok}
    if kind == "video":
        entry["seconds"] = seconds
    record(usd, entry, state_path, today)
    if not quiet:
        fleet("generated" if ok else "generate_failed", {**entry, "usd": usd,
              "month_usd": spend(state_path, today)}, outcome="ok" if ok else "error",
              level="info" if ok else "warn")


def selftest():
    import tempfile
    ok = 0
    def t(c, label):
        nonlocal ok
        if not c:
            print("FAIL:", label); sys.exit(1)
        ok += 1
    d = tempfile.mkdtemp(); sp = os.path.join(d, "s.json"); cp = os.path.join(d, "c.json")
    json.dump({"monthly_cap_usd": 10.0}, open(cp, "w"))
    day = datetime.date(2026, 10, 17)
    t(estimate("video", "veo-3.1-fast-generate-preview", 8) == 0.96, "veo fast 8s = $0.96")
    t(estimate("video", "veo-9-unknown", 8) == 3.2, "unknown veo model priced at standard tier")
    t(estimate("image", "gemini-3-pro-image-preview") == 0.134, "pro image $0.134")
    try:
        check("video", "veo-3.1-fast-generate-preview", 8, task="", state_path=sp, cfg_path=cp, today=day, quiet=True)
        t(False, "no task must refuse")
    except Refused:
        t(True, "no task refuses")
    usd = check("video", "veo-3.1-fast-generate-preview", 8, task="2928", state_path=sp, cfg_path=cp, today=day, quiet=True)
    t(usd == 0.96, "with task + under cap allows")
    record(9.5, {"kind": "video"}, sp, day)
    try:
        check("video", "veo-3.1-fast-generate-preview", 8, task="2928", state_path=sp, cfg_path=cp, today=day, quiet=True)
        t(False, "over cap must refuse")
    except Refused:
        t(True, "would-exceed cap refuses (pre-flight, before spend)")
    t(check("image", "gemini-3-pro-image-preview", task="2928", state_path=sp, cfg_path=cp, today=day, quiet=True) == 0.134,
      "small call still fits under cap")
    t(check("video", "veo-3.1-fast-generate-preview", 8, task="1", state_path=sp, cfg_path=cp,
            today=datetime.date(2026, 11, 1), quiet=True) == 0.96, "cap resets next month")
    t(spend(sp, day) == 9.5, "ledger sums month")
    t(os.path.exists(CFG), "config/google-media-spend.json present")
    for f in ("gen_vid_veo.py", "gen_img.py"):
        src = open(os.path.join(WS, "scripts", f)).read()
        body = src[src.index("def gen("):]
        first_api = min(i for i in (body.find("call("), body.find("urllib.request.Request(")) if i >= 0)
        t("import google_media_guard" in src and 0 <= body.find("guard.check(") < first_api,
          f"{f} calls guard.check before any API request")
    print(f"google_media_guard selftest: {ok}/{ok} pass")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
    elif "--status" in sys.argv:
        cap = float(load_cfg().get("monthly_cap_usd", 50.0))
        print(f"{month_key()}: ${spend():.2f} of ${cap:.2f} local cap")
    else:
        print(__doc__)
