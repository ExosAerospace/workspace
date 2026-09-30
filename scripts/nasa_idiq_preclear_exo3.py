#!/usr/bin/env python3
"""nasa_idiq_preclear_exo3.py — ExO3 GOVERN/ASSURE gate: pre-clear the two 2023 FO IDIQ4
disqualifiers on ANY NASA IDIQ submission before it goes to John to submit.

Standing guardrail (Jon 2026-07-24, MC task #1539), from the 2023 elimination on sol. 80AFRC23R0001:
  D1 PAST-PERFORMANCE RELEVANCY — AFWERX BLK3 was ruled "not a representative qualified launch
     vehicle." Past performance must LEAD with the FAA-licensed, flight-qualified BLK3
     (FAA license 3/13/26, flight heritage since 2018), not with AFWERX work.
  D2 PRICE-VOLUME DETAIL — the 2023 response "lacked sufficient financial detail over the five
     contract years." Price volume must be a year-by-year 5-year schedule with a cost basis,
     not ROM/summary figures.
  Advisory: OSP-4 anchor (3-day turnaround, $1,017,500/flight standard FFP) should be stated.

Usage:
  python3 scripts/nasa_idiq_preclear_exo3.py <submission.docx|.md|.txt|.pdf> [--json]
  python3 scripts/nasa_idiq_preclear_exo3.py --selftest     # eval: replays the 2023 failure
Exit: 0 = PASS, 1 = FAIL (do not route for submission), 3 = could not read input.
Read-only: never sends, never edits the submission. Emits fleet_log + decision_trace telemetry.
"""
import json, os, re, subprocess, sys

WS = "/Users/exomac/.openclaw/workspace"
AGENT = "nasa-idiq-preclear-exo3"
sys.path.insert(0, os.path.join(WS, "scripts"))

ANCHOR_PRICE = "1,017,500"


def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        from docx import Document
        from docx.table import Table
        from docx.text.paragraph import Paragraph
        d = Document(path)
        parts = []
        # body order matters: "leads with" is judged on what comes first in the section
        for el in d.element.body.iterchildren():
            tag = el.tag.rsplit("}", 1)[-1]
            if tag == "p":
                parts.append(Paragraph(el, d).text)
            elif tag == "tbl":
                for row in Table(el, d).rows:
                    parts.append(" | ".join(c.text for c in row.cells))
        return "\n".join(parts)
    if ext == ".pdf":
        return subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True,
                              text=True, timeout=120).stdout
    return open(path, encoding="utf-8", errors="replace").read()


def _section(text, heading_re, span=4000):
    m = re.search(heading_re, text, re.I)
    if not m:
        return None
    rest = text[m.end():m.end() + span]
    nxt = re.search(r"\n\s*(Section\s+\d+|Volume\s+[IVX\d]+|Appendix\s+[A-Z])\b", rest, re.I)
    return rest[:nxt.start()] if nxt else rest


def check(text):
    res = {"D1_past_performance": {}, "D2_price_volume": {}, "advisory": []}

    # ---- D1: past performance must lead with the FAA-licensed, flight-qualified BLK3 ----
    pp = _section(text, r"past[\s-]+performance")
    d1 = res["D1_past_performance"]
    if pp is None:
        d1.update(status="FAIL", why="No Past Performance section found.")
    else:
        lead = pp[:1500]
        faa = re.search(r"FAA", lead) and re.search(r"licen[sc]", lead, re.I)
        blk3 = re.search(r"BLK\s*-?3|Block\s*3", lead, re.I)
        heritage = re.search(r"2018|flight heritage|flown|flight-qualified|flight qualified", lead, re.I)
        afw = re.search(r"AFWERX", pp, re.I)
        faa_pos = re.search(r"FAA", pp)
        afwerx_leads = bool(afw) and (not faa_pos or afw.start() < faa_pos.start())
        miss = [n for n, ok in (("FAA license", faa), ("BLK3", blk3), ("flight heritage", heritage)) if not ok]
        if afwerx_leads:
            d1.update(status="FAIL", why="AFWERX appears before the FAA license in Past Performance — move the "
                                          "FAA-licensed, flight-qualified BLK3 evidence to the top (2023 finding: "
                                          "'not a representative qualified launch vehicle').")
        elif miss:
            d1.update(status="FAIL", why="Opening of Past Performance is missing: " + ", ".join(miss) + ".")
        else:
            d1.update(status="PASS", why="Leads with FAA-licensed, flight-qualified BLK3.")

    # ---- D2: year-by-year 5-contract-year price volume with a cost basis ----
    d2 = res["D2_price_volume"]
    years = set()
    for m in re.finditer(r"\b(?:contract\s+year|CY|year|option\s+year|OY|PY)\s*[-#]?\s*([1-5])\b", text, re.I):
        years.add(int(m.group(1)))
    if re.search(r"\bbase\s+(?:year|period)\b", text, re.I):
        oy = {int(m.group(1)) for m in re.finditer(r"option\s+(?:year|period)\s*([1-4])\b", text, re.I)}
        if len(oy) == 4:
            years = {1, 2, 3, 4, 5}
    fy = set(re.findall(r"\b(?:FY|GFY)\s*'?(\d{2,4})\b", text))
    five_years = len(years) >= 5 or len(fy) >= 5
    basis = re.search(r"cost\s+basis|basis\s+of\s+estimate|\bBOE\b|labor|materials?|overhead|G&A|fee\b|wrap\s+rate",
                      text, re.I)
    rom_only = re.search(r"\bROM\b|rough\s+order\s+of\s+magnitude|illustrative|will\s+be\s+provided\s+at\s+formal",
                         _section(text, r"pric(?:e|ing)") or "", re.I)
    if not five_years:
        d2.update(status="FAIL", why=f"No year-by-year 5-contract-year price schedule found (years detected: "
                                     f"{sorted(years) or 'none'})" + ("; pricing is ROM/illustrative" if rom_only else "") +
                                     " — the exact 2023 'insufficient financial detail over five contract years' finding.")
    elif not basis:
        d2.update(status="FAIL", why="5-year schedule present but no granular cost basis (labor/materials/"
                                     "overhead/G&A/fee/BOE) — summary figures only.")
    else:
        d2.update(status="PASS", why="Year-by-year 5-year schedule with cost basis present.")

    # ---- Advisory: OSP-4 anchor ----
    if ANCHOR_PRICE not in text:
        res["advisory"].append(f"OSP-4 anchor ${ANCHOR_PRICE}/flight not stated — confirm the per-flight figure "
                               "used is the approved one (the FO IDIQ4 draft uses the $1,012,500 full-bay floor).")
    if not re.search(r"3[\s-]*day\s+turnaround|turnaround[^\n]{0,40}3[\s-]*day", text, re.I):
        res["advisory"].append("3-day turnaround not stated.")

    res["verdict"] = "PASS" if d1.get("status") == "PASS" and d2.get("status") == "PASS" else "FAIL"
    return res


def telemetry(path, res):
    try:
        import fleet_log
        corr = fleet_log.new_corr()
        fleet_log.event(AGENT, "govern", "nasa_idiq_preclear", corr=corr, owner="John Quinn",
                        outcome=res["verdict"],
                        detail={"file": path, "D1": res["D1_past_performance"].get("status"),
                                "D2": res["D2_price_volume"].get("status")},
                        level="info" if res["verdict"] == "PASS" else "warn")
        import decision_trace
        decision_trace.emit(agent=AGENT, corr=corr, inputs=[path],
                            policy_applied="MC #1539 standing guardrail: pre-clear 2023 FO IDIQ4 disqualifiers",
                            options=["route to John for submission", "hold and fix disqualifiers"],
                            chosen="route to John for submission" if res["verdict"] == "PASS"
                            else "hold and fix disqualifiers",
                            precedent=["80AFRC23R0001 (2023 elimination)"],
                            write_back="report returned to caller; no submission edits",
                            final_call="human", approver="John Quinn", outcome=res["verdict"])
    except Exception:
        pass  # telemetry never blocks the gate


def render(path, res):
    out = [f"NASA IDIQ PRE-CLEAR ({AGENT}) — {os.path.basename(path)}: {res['verdict']}"]
    for k in ("D1_past_performance", "D2_price_volume"):
        out.append(f"  {k}: {res[k]['status']} — {res[k]['why']}")
    for a in res["advisory"]:
        out.append(f"  advisory: {a}")
    return "\n".join(out)


def selftest():
    fail_2023 = """Section 4: Past Performance
AFWERX SBIR contract for BLK3 development; Exos delivered test reports to the Air Force.
Section 5: Pricing
ROM pricing: approximately $1M per flight. Summary total over the contract: $10M."""
    good = """Section 4: Past Performance
BLK3 is FAA licensed (license issued 3/13/26) with commercial flight heritage since 2018 —
one of only three FAA-licensed reusable rocket launch providers. AFWERX work is supporting.
Section 5: Price Volume
Contract Year 1 | Contract Year 2 | Contract Year 3 | Contract Year 4 | Contract Year 5
Cost basis: labor, materials, range fees, overhead, G&A and fee by year.
Standard flight $1,017,500 FFP; 3-day turnaround."""
    no_pp = "Section 5: Price Volume\nYear 1 Year 2 Year 3 Year 4 Year 5 labor overhead"
    cases = [
        ("2023 replay fails both", fail_2023,
         lambda r: r["verdict"] == "FAIL" and r["D1_past_performance"]["status"] == "FAIL"
         and r["D2_price_volume"]["status"] == "FAIL"),
        ("compliant package passes", good,
         lambda r: r["verdict"] == "PASS" and not r["advisory"]),
        ("missing past performance fails D1", no_pp,
         lambda r: r["D1_past_performance"]["status"] == "FAIL" and r["D2_price_volume"]["status"] == "PASS"),
    ]
    ok = True
    for name, txt, pred in cases:
        r = check(txt)
        passed = pred(r)
        ok &= passed
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    print("SELFTEST", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest())
    paths = [a for a in args if not a.startswith("--")]
    if len(paths) != 1:
        print(__doc__)
        sys.exit(3)
    path = paths[0]
    try:
        text = read_text(path)
    except Exception as e:
        print(f"could not read {path}: {e}")
        sys.exit(3)
    res = check(text)
    telemetry(path, res)
    print(json.dumps(res, indent=2) if "--json" in args else render(path, res))
    sys.exit(0 if res["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
