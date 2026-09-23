#!/usr/bin/env python3
"""job_cost.py — per-job cost rollup (Phase 4). Material cost comes from consume postings
(job-costs.json, part qty x unit cost). Labor hours come from the ERP time_entry table joined by
WBS where mapped. Prints JSON. Material is solid today; loaded labor $ is pending the time->WBS
mapping + rates (flagged), so total shown is material + any priced labor.
"""
import json, os, sqlite3

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(WS, "mission-control", "data")
JOBS = os.path.join(DATA, "jobs.json")
JC = os.path.join(DATA, "job-costs.json")
ERP_DB = os.path.join(WS, "erp-foundation", "mc.db")


def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def labor_by_wbs():
    """Sum time_entry hours by wbs_id (loaded $ needs rates; report hours). Empty if unmapped."""
    out = {}
    if not os.path.exists(ERP_DB):
        return out
    try:
        con = sqlite3.connect(f"file:{ERP_DB}?mode=ro", uri=True)
        cur = con.execute("SELECT wbs_id, SUM(hours) FROM time_entry WHERE wbs_id IS NOT NULL AND wbs_id != '' GROUP BY wbs_id")
        for wbs, hrs in cur.fetchall():
            out[str(wbs)] = round(hrs or 0, 2)
        con.close()
    except Exception:
        pass
    return out


def main():
    jobs = load(JOBS, {"jobs": []}).get("jobs", [])
    postings = load(JC, {"postings": []}).get("postings", [])
    labor = labor_by_wbs()
    mat = {}
    for p in postings:
        j = p.get("job")
        e = mat.setdefault(j, {"cost": 0.0, "lines": 0, "priced": 0, "unpriced": 0})
        e["lines"] += 1
        if p.get("cost") not in (None, ""):
            e["cost"] += float(p["cost"]); e["priced"] += 1
        else:
            e["unpriced"] += 1
    rows = []
    total_material = 0.0
    for job in jobs:
        m = mat.get(job["id"], {"cost": 0.0, "lines": 0, "priced": 0, "unpriced": 0})
        lh = labor.get(str(job.get("wbs") or ""), 0)
        total_material += m["cost"]
        rows.append({"id": job["id"], "name": job.get("name"), "section": job.get("section"),
                     "vehicle": job.get("vehicle"), "task": job.get("task"), "wbs": job.get("wbs"),
                     "material_cost": round(m["cost"], 2), "material_lines": m["lines"],
                     "material_unpriced": m["unpriced"], "labor_hours": lh,
                     "labor_note": "" if job.get("wbs") else "no WBS mapped → labor pending",
                     "total_cost": round(m["cost"], 2)})
    print(json.dumps({"jobs": rows, "total_material": round(total_material, 2),
                      "labor_priced": bool(labor),
                      "note": "Material is live from consume postings. Loaded labor $ pending time->WBS mapping + rates."}))


if __name__ == "__main__":
    main()
