"""Shared HTTP retry/backoff helper for cron scripts that hit Supabase (and other
Cloudflare-fronted origins).

Background: Supabase sits behind Cloudflare. Transient blips surface as 5xx gateway
errors (520-524) or socket timeouts, most often at quiet hours when the origin
cold-starts. A single blip was causing crons to SKIP whole runs (e.g. the decisions
stale-auto-close sweep). This wraps urllib.request.urlopen with retry + exponential
backoff so one transient error retries instead of aborting the run.

Usage: add this once, at the very top of a script (after the shebang/docstring):

    import supabase_util; supabase_util.install()

install() monkeypatches urllib.request.urlopen process-wide, so every existing
`urllib.request.urlopen(...)` call site (and aliases like `_ur.urlopen`) gets retry
behavior with no other code changes.

Retry policy:
  - Retries on: 429, 500, 502, 503, 504, 520, 521, 522, 523, 524, socket timeouts,
    connection resets/refused (URLError). These are connection-phase / gateway
    failures where the origin did not commit the request, so retrying is safe.
  - Does NOT retry on 4xx (except 429) — those are real client errors, not blips.
  - 4 attempts total, exponential backoff 1.5s -> 3s -> 6s.
  - Injects a default 60s timeout when a caller passed none, so a hung socket can
    actually fail and become retryable instead of blocking forever.
"""
import time
import socket
import urllib.request
import urllib.error

RETRY_STATUS = {429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
MAX_ATTEMPTS = 4
BASE_DELAY = 1.5          # seconds; exponential -> 1.5, 3.0, 6.0
DEFAULT_TIMEOUT = 60      # applied only when the caller passed no timeout

_orig_urlopen = urllib.request.urlopen
_installed = False


def urlopen_retry(*args, **kwargs):
    # Ensure a bounded timeout so hung connections fail (and retry) rather than block.
    # urlopen signature is urlopen(url, data=None, timeout=..., ...); timeout is the
    # 3rd positional arg, so only inject when <3 positional args and no timeout kwarg.
    if "timeout" not in kwargs and len(args) < 3:
        kwargs["timeout"] = DEFAULT_TIMEOUT

    last_err = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _orig_urlopen(*args, **kwargs)
        except urllib.error.HTTPError as e:
            # Retry only transient gateway/rate-limit codes; re-raise real 4xx/other.
            if e.code in RETRY_STATUS and attempt < MAX_ATTEMPTS:
                last_err = e
            else:
                raise
        except (urllib.error.URLError, socket.timeout, TimeoutError, ConnectionError) as e:
            if attempt < MAX_ATTEMPTS:
                last_err = e
            else:
                raise
        time.sleep(BASE_DELAY * (2 ** (attempt - 1)))
    if last_err is not None:
        raise last_err


def install():
    """Idempotently monkeypatch urllib.request.urlopen with the retrying version."""
    global _installed
    if _installed:
        return
    urllib.request.urlopen = urlopen_retry
    _installed = True
