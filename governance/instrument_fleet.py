#!/usr/bin/env python3
"""
instrument_fleet.py -- one-time installer that wires governance/govlog into the
live cron fleet so every run emits correlated start/end/error events.

Safe by construction:
  - idempotent (skips a file that already has the governance block)
  - backs up each file to <file>.govbak before touching it
  - inserts AFTER the module docstring (AST-located) so __doc__ is preserved
  - re-parses the result; if syntax breaks, restores the backup and reports
  - the injected block is wrapped in try/except, so it can never break the job

Run:  python3 governance/instrument_fleet.py [--revert]
"""
import ast
import os
import sys

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(WS, "scripts")

# entry script -> registry.json class id
FLEET = {
    "opportunity_processor.py": "opportunity-engine",
    "research_agent.py": "research",
    "mission-control-imap.py": "email-router",
    "dashboard-data-generator.py": "dashboard-data",
    "sam-amendment-watch.py": "sam-watch",
    "crm-reminder-lizi.py": "crm",
    "generate-crm-dashboard.py": "dashboard-data",
    # NOTE: payload_sales_engine.py is natively instrumented with a different
    # comment marker, so the injector does NOT recognize it and would double-inject.
    # It is intentionally NOT listed here. derisk_orbital_outreach.py carries the
    # injector's marker, so it is correctly skipped as ALREADY WIRED.
    "derisk_orbital_outreach.py": "derisk-orbital",
    # Consequential standalone launchd scripts — log-substrate coverage (Searchable
    # Logs pillar). Tags are govlog agent names, not registered eval classes.
    "capture-action-dispatch.py": "capture-dispatch",
    "decision-send-watcher.py": "decision-send",
    "priority-inbox-watcher.py": "priority-inbox",
    "outreach-autoclose.py": "outreach-autoclose",
    "mc-email-command.py": "email-command",
    "sent-loop-closer.py": "sent-loop-closer",
    "role-autoassign.py": "role-autoassign",
}

MARK = "# --- governance: correlation logging"

BLOCK = '''{mark} (auto-inserted; safe/soft) ---
try:
    import sys as _gsys, os as _gos, atexit as _gatexit
    _gsys.path.insert(0, _gos.path.join(_gos.path.dirname(_gos.path.abspath(__file__)), ".."))
    from governance.govlog import new_run as _gnew_run, event as _gevent
    _GRUN = _gnew_run("{cls}")
    _gevent(_GRUN, "start", detail=" ".join(_gsys.argv[1:])[:120])
    _gatexit.register(lambda: _gevent(_GRUN, "end"))
    _gprev_hook = _gsys.excepthook
    def _gexc(t, v, tb):
        try: _gevent(_GRUN, "error", status="error", detail=str(v)[:160])
        except Exception: pass
        return _gprev_hook(t, v, tb)
    _gsys.excepthook = _gexc
except Exception:
    pass
# --- /governance ---
'''


def insertion_line(src: str) -> int:
    """Return the 0-based line index to insert at: after shebang and docstring."""
    lines = src.splitlines()
    idx = 0
    if lines and lines[0].startswith("#!"):
        idx = 1
    try:
        tree = ast.parse(src)
        if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(
                getattr(tree.body[0], "value", None), ast.Constant) and isinstance(
                tree.body[0].value.value, str):
            idx = max(idx, tree.body[0].end_lineno)  # end_lineno is 1-based == next 0-based idx
    except SyntaxError:
        pass
    return idx


def revert():
    n = 0
    for fn in FLEET:
        path = os.path.join(SCRIPTS, fn)
        bak = path + ".govbak"
        if os.path.exists(bak):
            os.replace(bak, path)
            print(f"  reverted {fn}")
            n += 1
    print(f"reverted {n} file(s)")


def main():
    if "--revert" in sys.argv:
        return revert()
    done, skipped, failed = [], [], []
    for fn, cls in FLEET.items():
        path = os.path.join(SCRIPTS, fn)
        if not os.path.exists(path):
            failed.append((fn, "not found")); continue
        src = open(path, encoding="utf-8").read()
        if MARK in src:
            skipped.append(fn); continue
        lines = src.splitlines(keepends=True)
        at = insertion_line(src)
        block = "\n" + BLOCK.format(mark=MARK, cls=cls) + "\n"
        new = "".join(lines[:at]) + block + "".join(lines[at:])
        try:
            ast.parse(new)
        except SyntaxError as e:
            failed.append((fn, f"syntax after insert: {e}")); continue
        open(path + ".govbak", "w", encoding="utf-8").write(src)
        open(path, "w", encoding="utf-8").write(new)
        done.append(f"{fn} -> {cls}")
    print("INSTRUMENTED:")
    for d in done: print(f"  + {d}")
    if skipped: print("ALREADY WIRED:", ", ".join(skipped))
    if failed: print("FAILED:", "; ".join(f"{f} ({why})" for f, why in failed))
    print(f"\n{len(done)} wired, {len(skipped)} skipped, {len(failed)} failed")


if __name__ == "__main__":
    main()
