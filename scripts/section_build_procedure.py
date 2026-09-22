#!/usr/bin/env python3
"""section_build_procedure.py — assemble a rocket-section BUILD procedure from the BLK3 BOM
order + the photos captured against each part (inventory_capture) + live on-hand status.

ONE approvable procedure per SECTION (not per photo). Regenerate on demand as more photos land.
Runs through build_procedure.py so it gets the Exos house template, the Procedures Master List
row, and Process Library registration — as a DRAFT for John to approve.

Usage:
  python3 scripts/section_build_procedure.py [Section] [--owner "Name"] [--email]
  (default Section = Computer)
"""
import json, os, sys, subprocess, tempfile, argparse

WS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MC = os.path.join(WS, "mission-control")
UPLOADS = os.path.join(MC, "uploads")
BOM_INDEX = os.path.join(MC, "data", "bom-index.json")
INVENTORY = os.path.join(MC, "data", "inventory.json")
BUILDER = os.path.join(WS, "scripts", "build_procedure.py")
EMBEDDABLE = (".png", ".jpg", ".jpeg")
SECTION_CODE = {"Computer": "COMP", "Engine Bay": "ENGB", "Fin Can": "FINC",
                "Pressure Section": "PRES", "Tanks": "TANK", "Payload Section": "PAYL",
                "Recovery section": "RECV", "BLK3 Top Level": "TOP"}
SECTION_OWNER = {"Computer": "Steve Norsworthy"}   # avionics/computer owner; else default below


def load(p, d):
    try:
        return json.load(open(p))
    except Exception:
        return d


def resolve_photo(stored_name):
    """Return an embeddable (png/jpg) absolute path for a stored upload, converting HEIC/webp/gif
    to a temp JPEG via macOS sips if needed. None if unusable."""
    if not stored_name:
        return None
    src = os.path.join(UPLOADS, stored_name)
    if not os.path.exists(src):
        return None
    ext = os.path.splitext(src)[1].lower()
    if ext in EMBEDDABLE:
        return src
    out = os.path.join(tempfile.gettempdir(), "secproc_" + os.path.splitext(stored_name)[0] + ".jpg")
    try:
        subprocess.run(["/usr/bin/sips", "-s", "format", "jpeg", src, "--out", out],
                       capture_output=True, timeout=30)
        return out if os.path.exists(out) else None
    except Exception:
        return None


def inv_index(inv):
    by = {}
    for r in inv.get("records", []):
        for k in [r.get("vendor_pn"), r.get("mfg_pn"), r.get("key")]:
            if k:
                by[str(k).strip().upper()] = r
        if r.get("section") and r.get("item"):
            by[f"{r['section'].upper()}#{r['item']}"] = r
    return by


def num(x):
    try:
        return float(str(x).strip())
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("section", nargs="?", default="Computer")
    ap.add_argument("--owner")
    ap.add_argument("--email", action="store_true")
    a = ap.parse_args()
    section = a.section
    bom = load(BOM_INDEX, {"rows": []})
    rows = [r for r in bom.get("rows", []) if r.get("section", "").lower() == section.lower()]
    if not rows:
        print(f"no BOM rows for section '{section}'. Sections: "
              f"{sorted(set(r.get('section') for r in bom.get('rows', [])))}")
        sys.exit(1)
    inv = load(INVENTORY, {"records": []})
    bykey = inv_index(inv)

    steps = []
    captured = short = total = 0
    for r in rows:
        total += 1
        item, qty, vpn, mpn, desc = r.get("item"), r.get("qty"), r.get("vendor_pn"), r.get("mfg_pn"), r.get("description")
        rec = None
        for k in [vpn, mpn]:
            if k and str(k).strip().upper() in bykey:
                rec = bykey[str(k).strip().upper()]; break
        if rec is None and item:
            rec = bykey.get(f"{section.upper()}#{item}")
        oh = rec.get("qty_on_hand", 0) if rec else 0
        req = num(qty)
        pn = vpn or mpn or ""
        label = f"Item {item or '-'}: {desc or pn}"
        if pn:
            label += f"  ·  P/N {pn}"
        label += f"  ·  req {qty or '-'}, on-hand {oh}"
        if req is not None and oh < req:
            label += f"  ·  SHORT {round(req - oh, 3)}"; short += 1
        # newest photo for this part, if any
        img = cap = None
        if rec and rec.get("photos"):
            ph = sorted(rec["photos"], key=lambda p: p.get("at", ""), reverse=True)[0]
            img = resolve_photo(ph.get("file"))
            if img:
                captured += 1
                cap = f"As-built photo (by {ph.get('by','team')}, {str(ph.get('at',''))[:10]})"
        steps.append({"text": label, "image": img, "caption": cap} if img else label)

    code = SECTION_CODE.get(section, section[:4].upper())
    owner = a.owner or SECTION_OWNER.get(section, "John Quinn")
    spec = {
        "title": f"BLK3 {section} Section — Build & Inventory Verification",
        "doc_no": f"EXOS-US-BUILD-BLK3-{code}",
        "area": "Manufacturing / Vehicle Build",
        "area_id": "11-manufacturing-build",
        "owner": owner,
        "status": "DRAFT",
        "intl_release": False,
        "reference_docs": f"BLK3 BOM ({bom.get('source','')}); Mission Control build task; inventory ledger",
        "objective": (f"build and inventory-verify the BLK3 {section.lower()} section: confirm each BOM "
                      f"component is on hand, install it in BOM order, and capture an as-built photo of "
                      f"each component as the reusable build/training record for this section."),
        "overview": (f"This procedure is assembled from the BLK3 {section} BOM and the photos captured on "
                     f"the build task. It lists every component in BOM order with its part number, required "
                     f"quantity, and current on-hand count. Shorts are flagged for procurement. As each "
                     f"component is installed, the builder photographs it (📷 on the Mission Control task); the "
                     f"photo is recorded to inventory and appears here. Regenerate this document as more "
                     f"components are captured — it becomes the section's illustrated build & training record. "
                     f"Status: {captured}/{total} components photographed, {short} short."),
        "tasks": [
            {"name": f"Components & Inventory Verification — {section} ({captured}/{total} photographed, {short} short)",
             "steps": steps},
            {"name": "Build Sequence",
             "steps": ["Install each component above in BOM order, verifying part number and quantity against the BOM line.",
                       "Photograph each component as installed using the 📷 Take Photo button on this section's Mission Control task.",
                       "For any component flagged SHORT, confirm the procurement action before proceeding past that step.",
                       "On completion, regenerate this procedure so every installed component shows its as-built photo."]},
        ],
    }
    tmp = os.path.join(tempfile.gettempdir(), f"secproc_spec_{code}.json")
    json.dump(spec, open(tmp, "w"))
    r = subprocess.run(["/usr/bin/python3", BUILDER, tmp], capture_output=True, text=True)
    print(r.stdout.strip());
    if r.returncode != 0:
        print(r.stderr.strip()); sys.exit(r.returncode)
    fname = spec["doc_no"].replace(" ", "_") + "_" + spec["title"].replace(" ", "_").replace("/", "-") + ".docx"
    out = os.path.join(WS, "process-library", spec["area_id"], fname)
    print("DOCX:", out)
    print(f"summary: {total} components · {captured} photographed · {short} short")

    if a.email and os.path.exists(out):
        subj = f"[Procedure DRAFT for approval] BLK3 {section} Section — Build & Inventory Verification"
        body = (f"John,\n\nDraft section build procedure for the BLK3 {section.lower()} section is attached "
                f"for your approval.\n\nIt is assembled automatically from the BLK3 BOM order, the current "
                f"inventory on-hand counts, and the as-built photos captured on the build task.\n\n"
                f"Status: {captured} of {total} components photographed; {short} flagged short.\n\n"
                f"As the team photographs more components (📷 on the Mission Control task), regenerate this "
                f"and each installed part shows its as-built photo. It also lands in the Process Library as a "
                f"DRAFT pending your approval.\n\nDoc: {spec['doc_no']}\n\n— Exo")
        eml = os.path.join(tempfile.gettempdir(), f"secproc_{code}.eml")
        # build a MIME email with attachment via python then hand to msmtp
        import email.message, mimetypes
        m = email.message.EmailMessage()
        m["From"] = "jquinnexo@pm.me"; m["To"] = "jquinn@exosaero.com"; m["Subject"] = subj
        m.set_content(body)
        ctype, _ = mimetypes.guess_type(out)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        with open(out, "rb") as fh:
            m.add_attachment(fh.read(), maintype=maintype, subtype=subtype, filename=fname)
        with open(eml, "wb") as fh:
            fh.write(bytes(m))
        er = subprocess.run(["msmtp", "-a", "protonmail", "jquinn@exosaero.com"],
                            stdin=open(eml, "rb"), capture_output=True, text=True)
        print("emailed John:" , "ok" if er.returncode == 0 else ("FAIL " + er.stderr.strip()))


if __name__ == "__main__":
    main()
