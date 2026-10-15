#!/usr/bin/env python3
"""fx_rate.py — documented FX conversion for Mission Control expenses (Jon 2026-10-15: "update the Mission Control
expenses to have an option to pay in yen").

Rate of record: Federal Reserve H.10 daily rate (FRED series DEXJPUS = JPY per 1 USD), taken for the EXPENSE DATE or
the most recent published business day before it (weekends/holidays). Cached in mission-control/data/fx-rates.json
so a report always converts reproducibly. Source cited on every converted line.

  fx_rate.py convert          stdin {"line_items":[...]} -> stdout same items; JPY lines get amount_original,
                              currency, fx_rate (JPY/USD), fx_date, fx_source and amount (USD, 2dp)
  fx_rate.py rate JPY [DATE]  print {"rate":..., "date":..., "source":...}
  fx_rate.py --selftest
Owner: John Quinn. Registered as capability of the MC expense workflow (expense-fx-exo3).
"""
import csv, io, json, os, sys, datetime, urllib.request

WS = "/Users/exomac/.openclaw/workspace"
CACHE = os.path.join(WS, "mission-control/data/fx-rates.json")
SERIES = {"JPY": "DEXJPUS"}          # foreign units per 1 USD
SOURCE = "Federal Reserve H.10 (FRED {s}), https://fred.stlouisfed.org/series/{s}"


def _load():
    try:
        return json.load(open(CACHE))
    except Exception:
        return {}


def _save(c):
    tmp = CACHE + ".tmp"
    json.dump(c, open(tmp, "w"), indent=1, sort_keys=True)
    os.replace(tmp, CACHE)


def fetch(series, since):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}&cosd={since}"
    txt = urllib.request.urlopen(url, timeout=20).read().decode()
    out = {}
    for row in csv.reader(io.StringIO(txt)):
        if len(row) == 2 and row[0][:2] == "20":
            try:
                out[row[0]] = float(row[1])
            except ValueError:
                pass      # "." = no publication that day
    return out


def rate(ccy, date=None, cache=None, fetcher=fetch):
    """JPY per USD for `date` (YYYY-MM-DD) or the latest published business day before it."""
    ccy = ccy.upper()
    if ccy == "USD":
        return {"rate": 1.0, "date": date, "source": "USD"}
    if ccy not in SERIES:
        raise ValueError(f"unsupported currency {ccy}")
    s = SERIES[ccy]
    date = (date or datetime.date.today().isoformat())[:10]
    c = _load() if cache is None else cache
    tab = c.setdefault(s, {})
    def pick():
        ds = [d for d in tab if d <= date]
        return max(ds) if ds else None
    d = pick()
    stale = d is None or (datetime.date.fromisoformat(date) - datetime.date.fromisoformat(d)).days > 4
    import time
    last = c.setdefault("_fetched_at", {}).get(s, 0)
    if stale and time.time() - last > 6 * 3600:   # H.10 publishes weekly; at most one fetch per 6h
        c["_fetched_at"][s] = time.time()
        since = (datetime.date.fromisoformat(date) - datetime.timedelta(days=21)).isoformat()
        try:
            tab.update(fetcher(s, since))
            if cache is None:
                _save(c)
        except Exception:
            pass
        d = pick()
    if d is None:
        raise RuntimeError(f"no {s} rate on or before {date}")
    return {"rate": tab[d], "date": d, "source": SOURCE.format(s=s)}


def convert(items, **kw):
    out = []
    for it in items:
        it = dict(it)
        ccy = str(it.get("currency") or "USD").upper()
        if ccy != "USD" and str(it.get("category", "")).lower() != "mileage":
            r = rate(ccy, it.get("date") or None, **kw)
            orig = float(it.get("amount") or 0)
            it.update(currency=ccy, amount_original=orig, fx_rate=r["rate"], fx_date=r["date"], fx_source=r["source"],
                      amount=round(orig / r["rate"], 2))
        else:
            it["currency"] = "USD"
        out.append(it)
    return out


def selftest():
    n = 0
    def ok(c, m):
        nonlocal n
        assert c, "FAIL: " + m
        n += 1
    calls = []
    def fake(series, since):
        calls.append(series)
        return {"2026-10-09": 158.34, "2026-10-08": 158.33}
    cache = {}
    r = rate("JPY", "2026-10-11", cache=cache, fetcher=fake)       # Sunday -> Friday 10/9
    ok(r["rate"] == 158.34 and r["date"] == "2026-10-09", "weekend expense uses the prior business day H.10 rate")
    ok("H.10" in r["source"] and "DEXJPUS" in r["source"], "source of record cited")
    rate("JPY", "2026-10-09", cache=cache, fetcher=fake)
    ok(len(calls) == 1, "cached rate reused (no refetch)")
    rate("JPY", "2026-10-30", cache=cache, fetcher=fake)
    ok(len(calls) == 1, "stale date does not refetch within 6h (H.10 is weekly)")
    items = convert([{"date": "2026-10-11", "category": "Meals", "amount": 15834, "currency": "JPY"},
                     {"date": "2026-10-11", "category": "Mileage", "miles": 10, "currency": "JPY"},
                     {"date": "2026-10-11", "category": "Lodging", "amount": 120}], cache=cache, fetcher=fake)
    ok(items[0]["amount"] == 100.0 and items[0]["amount_original"] == 15834 and items[0]["fx_rate"] == 158.34, "¥15,834 -> $100.00 at 158.34")
    ok(items[1]["currency"] == "USD" and "fx_rate" not in items[1], "mileage is never FX-converted (IRS USD rate)")
    ok(items[2]["currency"] == "USD" and items[2]["amount"] == 120, "USD lines unchanged")
    try:
        rate("XYZ", cache=cache, fetcher=fake); ok(False, "x")
    except ValueError:
        ok(True, "unsupported currency refused")
    print(f"fx_rate selftest: {n}/{n} pass")


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--selftest" in a:
        selftest()
    elif a[:1] == ["convert"]:
        d = json.load(sys.stdin)
        print(json.dumps({"line_items": convert(d.get("line_items") or [])}))
    elif a[:1] == ["rate"]:
        print(json.dumps(rate(a[1] if len(a) > 1 else "JPY", a[2] if len(a) > 2 else None)))
    else:
        print(__doc__)
