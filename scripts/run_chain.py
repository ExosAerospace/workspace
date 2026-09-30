#!/usr/bin/env python3
"""
run_chain.py — run a launchd job's chained steps without masking a failed step (exo3 audit theme 6,
r2-launchd-residuals 2026-09-30).

Problem: plists that chain steps with ';' ("a; b; c") exit with c's status only, so a failing a or b never
reaches launchd LastExitStatus, run_logged, the 06:30 run-failures report or agent_eval.

Template (keeps ';' semantics — every step still runs, in order, same shell/env/cwd — but the chain exits
with the FIRST non-zero step status, and each failed step is named on stderr so run_logged's stderr tail
shows which one):

  ProgramArguments = [/usr/bin/python3, <ws>/scripts/run_logged.py, <label>, --,
                      /usr/bin/python3, <ws>/scripts/run_chain.py, --shell, /bin/zsh, -lc, --,
                      "step 1 command", "step 2 command", ...]

--shell takes the original shell + flag (/bin/sh -c or /bin/zsh -lc) so PATH/mise resolution is unchanged.
A step killed by a signal counts as 128+signal. SIGTERM/SIGINT/SIGHUP are forwarded to the running step
and stop the chain. Also emits one fleet_log 'chain_step_failed' event per failed step (soft).

Usage:
  run_chain.py [--label L] --shell <shell> <flag> -- <step> [<step> ...]
  run_chain.py --selftest
"""
import os, signal, subprocess, sys

WS = "/Users/exomac/.openclaw/workspace"
_child = None
_stop = None


def _fwd(sig, _frame):
    global _stop
    _stop = sig
    if _child and _child.poll() is None:
        try:
            _child.send_signal(sig)
        except Exception:
            pass


def _telemetry(label, idx, n, rc, step):
    try:
        sys.path.insert(0, os.path.join(WS, "scripts"))
        import fleet_log
        fleet_log.event("run_chain", "ops", "chain_step_failed", outcome="fail", level="warn",
                        detail={"label": label, "step": idx, "of": n, "exit": rc, "cmd": step[:160]})
    except Exception:
        pass


def run(shell, steps, label="", telemetry=True):
    """Run each step via shell+[step]; return (first non-zero status or 0, [(idx, rc)])."""
    global _child
    first, results = 0, []
    for i, step in enumerate(steps, 1):
        if _stop:
            break
        _child = subprocess.Popen(shell + [step])
        rc = _child.wait()
        _child = None
        if rc < 0:
            rc = 128 - rc
        results.append((i, rc))
        if rc != 0:
            print(f"run_chain: step {i}/{len(steps)} FAILED exit={rc}: {step[:200]}", file=sys.stderr, flush=True)
            if telemetry:
                _telemetry(label, i, len(steps), rc, step)
            if not first:
                first = rc
    if _stop and not first:
        first = 128 + _stop
    return first, results


def parse(argv):
    label, shell, i = os.environ.get("XPC_SERVICE_NAME", ""), None, 0
    while i < len(argv):
        a = argv[i]
        if a == "--label":
            label = argv[i + 1]; i += 2
        elif a == "--shell":
            shell = [argv[i + 1], argv[i + 2]]; i += 3
        elif a == "--":
            return label, shell, argv[i + 1:]
        else:
            raise SystemExit(f"run_chain: unexpected arg {a!r}")
    raise SystemExit("run_chain: missing -- <steps>")


def selftest():
    n = 0
    sh = ["/bin/sh", "-c"]
    assert run(sh, ["true", "true"], telemetry=False) == (0, [(1, 0), (2, 0)]); n += 1
    # the masking case: 'false; true' exits 0 under sh, must exit non-zero here
    assert subprocess.run(sh + ["false; true"]).returncode == 0; n += 1
    rc, res = run(sh, ["exit 3", "true"], telemetry=False)
    assert rc == 3 and res == [(1, 3), (2, 0)]; n += 1                      # later steps still run (';' semantics)
    rc, res = run(sh, ["true", "exit 5", "exit 7"], telemetry=False)
    assert rc == 5 and len(res) == 3; n += 1                                 # FIRST failure wins
    rc, _ = run(sh, ["kill -TERM $$"], telemetry=False)
    assert rc == 128 + signal.SIGTERM; n += 1                                # signal death -> 128+sig
    assert run(sh, ['[ "$PWD" = "%s" ]' % os.getcwd()], telemetry=False)[0] == 0; n += 1  # cwd inherited
    os.environ["RUN_CHAIN_FIXTURE"] = "x"
    assert run(sh, ['[ "$RUN_CHAIN_FIXTURE" = x ]'], telemetry=False)[0] == 0; n += 1     # env inherited
    assert parse(["--shell", "/bin/zsh", "-lc", "--", "a", "b"])[1:] == (["/bin/zsh", "-lc"], ["a", "b"]); n += 1
    assert parse(["--label", "L", "--shell", "/bin/sh", "-c", "--", "a"])[0] == "L"; n += 1
    print(f"run_chain selftest: {n}/{n} pass")
    return 0


def main():
    if "--selftest" in sys.argv[1:2]:
        return selftest()
    label, shell, steps = parse(sys.argv[1:])
    if not shell or not steps:
        raise SystemExit("run_chain: need --shell <shell> <flag> and at least one step")
    for s in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
        signal.signal(s, _fwd)
    rc, _ = run(shell, steps, label)
    return rc


if __name__ == "__main__":
    sys.exit(main())
