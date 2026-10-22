#!/usr/bin/env python3
"""watch_task_attachment.py — one-shot watcher: when a file is attached to an MC task, post ONE
Discord alert, then remove its own cron (self-cleaning). First use: Lizi 10/22, MC #3962
(John uploads the 10/22 UTD meeting transcript → tell Lizi in #utd-exo3capstone).

  watch_task_attachment.py --task 3962 --channel 1539382179120021616 --mention 1506647219351060631 \
      --label "the 10/22 UTD meeting transcript" --cron-name watch-3962-transcript [--dry-run]
  watch_task_attachment.py selftest
"""
import argparse, json, os, subprocess, sys, tempfile

WS = "/Users/exomac/.openclaw/workspace"
META = os.path.join(WS, "mission-control/uploads/_meta.json")
STATE_DIR = os.path.join(WS, "state")
sys.path.insert(0, os.path.join(WS, "scripts"))


def uploads_for(task, meta_path=META):
    try:
        meta = json.load(open(meta_path))
    except Exception:
        return []
    return [m for m in meta if str(m.get("task_id")) == str(task)]


def run(a, meta_path=META, state_dir=STATE_DIR, send=None, remove=None):
    state = os.path.join(state_dir, f"watch-task-{a.task}.json")
    if os.path.exists(state):
        return "already-alerted"
    ups = uploads_for(a.task, meta_path)
    if not ups:
        return "nothing-yet"
    names = ", ".join(u.get("filename", "?") for u in ups[:3])
    text = (f"<@{a.mention}> {a.label} is attached on MC #{a.task}: {names}. "
            f"Open it here: <https://mc.exosaero.space> (task #{a.task}).")
    ok = (send or discord)(a.channel, text, a.dry_run)
    if not ok:
        return "send-failed"  # no state written → retried next run
    if not a.dry_run:
        json.dump({"alerted": True, "files": names}, open(state, "w"))
        (remove or remove_cron)(a.cron_name)
    return "alerted"


def discord(channel, text, dry):
    cmd = ["openclaw", "message", "send", "--channel", "discord", "--target", f"channel:{channel}", "-m", text]
    if dry:
        print("[dry-run]", text)
        return True
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return p.returncode == 0


def remove_cron(name):
    """`openclaw cron rm` takes an id, so resolve the job name first."""
    if not name:
        return
    p = subprocess.run(["openclaw", "cron", "list", "--json"], capture_output=True, text=True, timeout=60)
    try:
        d = json.loads(p.stdout)
        jobs = d.get("jobs", d) if isinstance(d, dict) else d
        ids = [j["id"] for j in jobs if j.get("name") == name]
    except Exception:
        ids = []
    for i in ids:
        subprocess.run(["openclaw", "cron", "rm", i], capture_output=True, text=True, timeout=60)


def selftest():
    fails = 0
    with tempfile.TemporaryDirectory() as d:
        meta = os.path.join(d, "meta.json")
        json.dump([{"task_id": "1", "filename": "x.pdf"}], open(meta, "w"))
        sent, removed = [], []
        a = argparse.Namespace(task="3962", channel="c", mention="u", label="L", cron_name="n", dry_run=False)
        s = lambda c, t, dr: sent.append(t) or True
        r = lambda n: removed.append(n)
        for want, got in [("nothing-yet", run(a, meta, d, s, r))]:
            fails += want != got; print(("PASS" if want == got else "FAIL"), "no upload -> silent")
        json.dump([{"task_id": "3962", "filename": "transcript.docx"}], open(meta, "w"))
        got = run(a, meta, d, s, r)
        ok = got == "alerted" and len(sent) == 1 and "transcript.docx" in sent[0] and removed == ["n"]
        fails += not ok; print("PASS" if ok else "FAIL", "upload -> one alert + cron removed")
        got = run(a, meta, d, s, r)
        ok = got == "already-alerted" and len(sent) == 1
        fails += not ok; print("PASS" if ok else "FAIL", "rerun -> no second alert")
        a.task = "4000"; json.dump([{"task_id": "4000", "filename": "y"}], open(meta, "w"))
        got = run(a, meta, d, lambda c, t, dr: False, r)
        ok = got == "send-failed" and not os.path.exists(os.path.join(d, "watch-task-4000.json"))
        fails += not ok; print("PASS" if ok else "FAIL", "failed send -> retried next run")
    print("watch_task_attachment selftest:", "PASS" if not fails else f"FAIL ({fails})")
    return not fails


if __name__ == "__main__":
    if sys.argv[1:2] == ["selftest"]:
        sys.exit(0 if selftest() else 1)
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True); ap.add_argument("--channel", required=True)
    ap.add_argument("--mention", required=True); ap.add_argument("--label", required=True)
    ap.add_argument("--cron-name", default=""); ap.add_argument("--dry-run", action="store_true")
    print(run(ap.parse_args()))
