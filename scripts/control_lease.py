#!/usr/bin/python3
"""
control_lease.py — the Studio<->Mini control LEASE (single-active server role) + its decision logic.

Jon 2026-10-02: automatic failover at 6 minutes, never both boxes active.
Supersedes the local-file prototype scripts/active_lease.py (9/13, never wired).

WHERE: Supabase Storage, private bucket `exos-control` (service_role key from secrets.json):
  control-lease.json  {holder, renewed_epoch, renewed_by, generation, claim_epoch, promoted_epoch, note, write_id}
  failover-hold.json  {until_epoch, reason, by, set_epoch}        (maintenance hold, failover_hold.py)
  (Storage, not a table: the service_role REST key can't run DDL and the 8 CRM tables are the wrong home.
   Read-after-write is consistent — verified 2026-10-02.)

holder values:
  "studio"        Studio is the server; it renews every 60 s (lease_renew.py)
  "mini-pending"  Mini has seen the lease stale >= claim_after_s AND the Studio dark on both paths; a
                  claim, not a promote. A live Studio that sees this simply reclaims (writes "studio").
  "mini"          Mini promoted. The Studio stays FENCED until a human does a manual failback.

Timeline (defaults, config/failover.json):  Studio stops renewing at T
  T+240 s  Studio fences itself IF it also has no internet (partitioned) -> tunnels + send jobs stand down
  T+270 s  Mini writes mini-pending (only if Studio unreachable on BOTH paths and no hold)
  T+360 s  Mini writes mini (claim >= 60 s old, still dark, still no hold)        <- "6 minutes"
  T+420 s  Mini re-reads (nobody overwrote) and starts MC + tunnels + send jobs
Supabase unreachable = fail SAFE: the Mini never promotes on a lease it can't read; the Studio only
fences on a failed renew when its general internet is down too (so a Supabase outage can't take MC down).

The decision functions (studio_decide / mini_decide) are pure: the selftest in failover_monitor.py
replays them on a simulated clock. Python 3.9 compatible (the Mini runs /usr/bin/python3 3.9).
"""
import os, sys, json, time, socket, uuid, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.dirname(HERE)
HOME = os.path.expanduser("~")
STATE_DIR = os.path.join(HOME, ".openclaw", "state")
FENCE_FLAG = os.path.join(STATE_DIR, "server-fenced.flag")


def load_cfg():
    return json.load(open(os.path.join(WS, "config", "failover.json")))


def role(cfg=None):
    cfg = cfg or load_cfg()
    return cfg["hosts"].get(socket.gethostname().split(".")[0], "unknown")


def is_live(cfg):
    return str(cfg.get("mode", "dry-run")).lower() == "live"


def _service_key():
    for p in (os.path.join(HOME, ".openclaw", "secrets.json"),
              os.path.join(HOME, "dr-mirror", "openclaw-config", "secrets.json")):
        try:
            k = json.load(open(p)).get("supabase_service_role_key")
            if k:
                return k
        except Exception:
            continue
    raise RuntimeError("supabase_service_role_key not found")


# ---------------------------------------------------------------- store
class SupabaseStore(object):
    def __init__(self, cfg, timeout=15):
        self.base = cfg["supabase_url"].rstrip("/") + "/storage/v1"
        self.bucket = cfg["bucket"]
        self.timeout = timeout
        self.key = _service_key()

    def _req(self, method, url, body=None, headers=None):
        h = {"apikey": self.key, "Authorization": "Bearer " + self.key, "Cache-Control": "no-cache"}
        h.update(headers or {})
        req = urllib.request.Request(url, data=body, method=method, headers=h)
        return urllib.request.urlopen(req, timeout=self.timeout)

    def get(self, name):
        """Return (ok, dict|None). ok=False = could not read (network/auth). Missing object = (True, None)."""
        url = "%s/object/authenticated/%s/%s?t=%d" % (self.base, self.bucket, name, int(time.time() * 1000))
        try:
            with self._req("GET", url) as r:
                return True, json.loads(r.read().decode("utf-8") or "null")
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                try:
                    body = e.read().decode("utf-8", "replace")
                except Exception:
                    body = ""
                if e.code == 404 or "not_found" in body.lower() or "not found" in body.lower():
                    return True, None
            return False, None
        except Exception:
            return False, None

    def put(self, name, obj):
        url = "%s/object/%s/%s" % (self.base, self.bucket, name)
        try:
            with self._req("POST", url, json.dumps(obj).encode("utf-8"),
                           {"Content-Type": "application/json", "x-upsert": "true",
                            "cache-control": "no-store"}) as r:
                return 200 <= r.status < 300
        except Exception:
            return False


class MemStore(object):
    """In-memory store for the selftest. `reachable(who)` decides if a side can reach Supabase."""
    def __init__(self):
        self.objs = {}
        self.blocked = set()

    def view(self, who):
        store = self

        class V(object):
            def get(self, name):
                if who in store.blocked:
                    return False, None
                o = store.objs.get(name)
                return True, (json.loads(json.dumps(o)) if o is not None else None)

            def put(self, name, obj):
                if who in store.blocked:
                    return False
                store.objs[name] = json.loads(json.dumps(obj))
                return True
        return V()


# ---------------------------------------------------------------- pure decisions
def hold_active(hold, now):
    return bool(hold) and now < float(hold.get("until_epoch", 0))


def studio_decide(cfg, now, read_ok, lease, internet_ok, local):
    """Studio side, every renew_interval_s.
    local: {last_ok_epoch, fenced, fence_reason}
    Returns (write|None, fenced, reason)."""
    if not read_ok:
        since = now - float(local.get("last_ok_epoch") or now)
        if local.get("fenced") and local.get("fence_reason") in ("lease-lost", "partitioned"):
            # stay down until a successful READ proves we still hold the lease (the Mini may have
            # promoted while we were cut off — internet coming back alone is not proof)
            return None, True, local.get("fence_reason")
        if since >= cfg["fence_after_s"] and not internet_ok:
            return None, True, "partitioned"       # no Supabase AND no internet for >= fence_after_s
        return None, False, "supabase-unreachable %ds (internet %s) — not fencing" % (since, "ok" if internet_ok else "DOWN")
    if lease and lease.get("holder") == "mini":
        return None, True, "lease-lost"
    gen = int((lease or {}).get("generation", 0))
    reclaimed = bool(lease) and lease.get("holder") == "mini-pending"
    w = {"holder": "studio", "renewed_epoch": int(now), "renewed_by": "studio",
         "generation": gen + 1 if (reclaimed or not lease) else gen,
         "claim_epoch": None, "promoted_epoch": None,
         "note": "Studio reclaimed a Mini failover claim" if reclaimed else "",
         "write_id": uuid.uuid4().hex[:12]}
    return w, False, ("reclaimed-from-pending" if reclaimed else "renewed")


def mini_decide(cfg, now, read_ok, lease, hold, hb_age, mc_up, local):
    """Mini side, every 60 s.
    hb_age: seconds since the Studio last pushed its heartbeat over the exos-mini link (None = never)
    mc_up:  MC answered on https (exos-mc tunnel path)
    local:  {promoted_epoch, promote_due_epoch, promote_done}
    Returns (write|None, action, reason). action in: none|claim|withdraw|promote-lease|execute-promote."""
    studio_seen = (hb_age is not None and hb_age < cfg["heartbeat_fresh_s"]) or bool(mc_up)
    if not read_ok:
        return None, "none", "lease unreadable — fail safe, no promote"
    if lease is None:
        return None, "none", "no lease yet (Studio has not bootstrapped)"
    holder = lease.get("holder")
    stale = now - float(lease.get("renewed_epoch", 0))
    if holder == "mini":
        if local.get("promote_done"):
            return None, "none", "promoted (failback is manual)"
        if now >= float(local.get("promote_due_epoch") or 0) and lease.get("renewed_by") == "mini":
            return None, "execute-promote", "lease still ours after confirm wait"
        return None, "none", "promoted lease written; confirm wait"
    if hold_active(hold, now):
        if holder == "mini-pending":
            w = dict(lease, holder="studio", claim_epoch=None, note="Mini withdrew claim (maintenance hold)")
            return w, "withdraw", "maintenance hold active"
        return None, "none", "maintenance hold active until %d (%s)" % (hold.get("until_epoch", 0), hold.get("reason", ""))
    if holder == "mini-pending":
        if studio_seen or stale < cfg["claim_after_s"]:
            w = dict(lease, holder="studio", claim_epoch=None, note="Mini withdrew claim (Studio seen)")
            return w, "withdraw", "Studio reachable again (hb_age=%s mc_up=%s stale=%ds)" % (hb_age, mc_up, stale)
        if stale >= cfg["promote_after_s"] and now - float(lease.get("claim_epoch") or now) >= cfg["claim_min_age_s"]:
            w = dict(lease, holder="mini", renewed_epoch=int(now), renewed_by="mini",
                     generation=int(lease.get("generation", 0)) + 1, promoted_epoch=int(now),
                     note="Mini promoted: lease stale %ds, Studio dark on both paths" % stale,
                     write_id=uuid.uuid4().hex[:12])
            return w, "promote-lease", "lease stale %ds >= %ds, Studio dark on both paths" % (stale, cfg["promote_after_s"])
        return None, "none", "claim pending (stale %ds)" % stale
    # holder == studio
    if stale >= cfg["claim_after_s"] and not studio_seen:
        w = dict(lease, holder="mini-pending", claim_epoch=int(now), note="Mini claim: Studio dark", write_id=uuid.uuid4().hex[:12])
        return w, "claim", "lease stale %ds, heartbeat %s, MC https down" % (stale, hb_age)
    if stale >= cfg["claim_after_s"]:
        return None, "none", "lease stale %ds but Studio reachable (hb_age=%s mc_up=%s) — no failover" % (stale, hb_age, mc_up)
    return None, "none", "healthy (lease %ds old)" % stale


# ---------------------------------------------------------------- io helpers
def http_ok(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "exos-failover/1", "Cache-Control": "no-cache"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return 200 <= r.status < 300
    except Exception:
        return False


def internet_ok(cfg):
    return any(http_ok(u, 8) for u in cfg.get("internet_probe_urls", []))


def mc_https_up(cfg):
    """MC origin answering through the exos-mc tunnel (/sign is Access-bypassed, served by MC itself)."""
    try:
        req = urllib.request.Request(cfg["mc_health_url"], headers={"User-Agent": "exos-failover/1"})
        with urllib.request.urlopen(req, timeout=12) as r:
            return r.status == 200 and b"<html" in r.read(4096).lower()
    except Exception:
        return False


def read_json(p, default=None):
    try:
        return json.load(open(p))
    except Exception:
        return default


def write_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    json.dump(d, open(tmp, "w"), indent=1)
    os.replace(tmp, p)


def fleet(agent, action, outcome, detail, level="info"):
    try:
        sys.path.insert(0, HERE)
        import fleet_log
        fleet_log.event(agent, "govern", action, detail=detail, owner="John Quinn", outcome=outcome, level=level)
    except Exception:
        pass


if __name__ == "__main__":
    cfg = load_cfg()
    st = SupabaseStore(cfg)
    ok, lease = st.get(cfg["lease_object"])
    hok, hold = st.get(cfg["hold_object"])
    now = time.time()
    print("role: %s   mode: %s" % (role(cfg), cfg.get("mode")))
    print("lease (read %s): %s" % ("ok" if ok else "FAILED", json.dumps(lease)))
    if lease:
        print("lease age: %ds" % (now - float(lease.get("renewed_epoch", 0))))
    print("hold: %s %s" % ("ACTIVE" if hold_active(hold, now) else "none", json.dumps(hold) if hold else ""))
    print("local: %s" % json.dumps(read_json(os.path.join(STATE_DIR, "control-lease-local.json"))))
    print("fence flag: %s" % ("SET" if os.path.exists(FENCE_FLAG) else "clear"))
