#!/usr/bin/env python3
"""Two-pass build: PDF -> page map of section headings -> rebuild PDF + DOCX with compliance-matrix page refs."""
import subprocess, json, re, os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF = "drafts/VSFB_MDZ/Exos_VSFB_MDZ_Whitepaper_DRAFT_2026-10-11_v7.pdf"; PM = "drafts/VSFB_MDZ/_pagemap_v7.json"
def build():
    subprocess.run(["python3", "scripts/build_vsfb_mdz_pdf.py"], check=True)
def pagemap():
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", PDF], capture_output=True, text=True).stdout).group(1))
    keys = ["1.1","1.2","1.3","1.4","1.5","1.6","2.1","2.2","3.1","3.2","4.1","5.1","5.2","5.3","6.1","6.2","6.3","6.4","6.5","7.1","7.2","8.1"]
    pm = {}
    for pg in range(1, n+1):
        t = subprocess.run(["pdftotext","-f",str(pg),"-l",str(pg),"-layout",PDF,"-"],capture_output=True,text=True).stdout
        stop = "Appendix A" in t and "Compliance Matrix" in t and pg > 3
        if stop: t = t.split("Appendix A")[0]
        for k in keys:
            if k not in pm and re.search(r"^\s*%s\s+[A-Z]" % re.escape(k), t, re.M): pm[k] = pg
        if stop: break
    pm["Whole document"] = "%d pp total" % n
    json.dump(pm, open(PM, "w"), indent=1); return pm
if os.path.exists(PM): os.remove(PM)
build(); pm = pagemap(); build(); pm2 = pagemap(); build()
print(pm2)
env = dict(os.environ, PYTHONNOUSERSITE="1")
subprocess.run(["python3.12", "scripts/build_vsfb_mdz_docx.py"], check=True, env=env)
