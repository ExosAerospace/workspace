"""
durable_send_shim.py — import once to make a cron's `openclaw message send`
subprocess calls durable, with zero call-site changes.

Importing this transparently wraps subprocess.run: any call whose argv looks
like `[<openclaw>, "message", "send", ...]` is routed through deliver.deliver()
(spool-to-disk-then-send, retried by delivery-sweeper.py). It returns a
success-shaped CompletedProcess so existing `r.returncode == 0` checks keep
working — "returncode 0" now means "accepted for durable delivery", i.e. the
content is safe on disk even if the live send flaked.

Every OTHER subprocess.run call in the host script is passed through untouched.

Usage: add one line after the script's subprocess import:
    import durable_send_shim  # noqa: F401
"""
import os
import sys
import subprocess as _sp

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_ORIG_RUN = _sp.run
_IN_DELIVER = False  # re-entrancy guard so deliver()'s own send isn't re-wrapped


def _looks_like_send(argv):
    return (
        isinstance(argv, (list, tuple))
        and len(argv) >= 3
        and isinstance(argv[0], str)
        and "openclaw" in argv[0]
        and str(argv[1]) == "message"
        and str(argv[2]) == "send"
    )


def _parse(argv):
    channel, target, text = "discord", None, None
    i = 3
    n = len(argv)
    while i < n:
        a = str(argv[i])
        if a == "--target" and i + 1 < n:
            target = argv[i + 1]; i += 2; continue
        if a == "--channel" and i + 1 < n:
            channel = argv[i + 1]; i += 2; continue
        if a in ("-m", "--message") and i + 1 < n:
            text = argv[i + 1]; i += 2; continue
        i += 1
    return channel, target, text


def _patched_run(argv, *a, **kw):
    global _IN_DELIVER
    # deliver.try_send's own send must go straight out: re-wrapping it when a host calls
    # deliver() directly spooled a 2nd copy of every message (dupsend 2026-10-26).
    _caller = os.path.basename(sys._getframe(1).f_code.co_filename)
    if not _IN_DELIVER and _caller != "deliver.py" and _looks_like_send(argv):
        try:
            _IN_DELIVER = True
            from deliver import deliver, DEFAULT_TARGET
            ch, tgt, txt = _parse(argv)
            src = os.path.basename(sys.argv[0] or "cron").replace(".py", "") or "cron"
            deliver(txt or "", target=tgt or DEFAULT_TARGET,
                    channel=ch or "discord", source=src)
            return _sp.CompletedProcess(argv, 0, stdout="", stderr="")
        except Exception:
            # any shim failure -> fall back to the real, un-wrapped send
            pass
        finally:
            _IN_DELIVER = False
    return _ORIG_RUN(argv, *a, **kw)


# install once (idempotent)
if getattr(_sp.run, "__name__", "") != "_patched_run":
    _sp.run = _patched_run
