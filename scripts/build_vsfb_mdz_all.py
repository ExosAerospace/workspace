#!/usr/bin/env python3
"""Two-pass build: PDF -> page map of section headings -> rebuild PDF + DOCX with compliance-matrix page refs."""
import subprocess, json, re, os, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vsfb_mdz_content as K
PDF = "drafts/VSFB_MDZ/Exos_VSFB_MDZ_Whitepaper_%s%s.pdf" % (K.DATE, K.VER)
PM = "drafts/VSFB_MDZ/_pagemap.json"
SUBMIT = "drafts/VSFB_MDZ/SUBMIT/"
def build():
    subprocess.run(["python3", "scripts/build_vsfb_mdz_pdf.py"], check=True)
def pagemap():
    n = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", PDF], capture_output=True, text=True).stdout).group(1))
    keys = ["1.1","1.2","1.3","1.4","1.5","1.6","2.1","2.2","3.0","3.1","3.2","4.1","5.1","5.2","5.3","6.1","6.2","6.3","6.4","6.5","7.1","7.2","8.1","8.2","9.0"]
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
# Copy to SUBMIT/ with call-ready file names
DOCX = "drafts/VSFB_MDZ/Exos_VSFB_MDZ_Whitepaper_%s%s.docx" % (K.DATE, K.VER)
STEM = "Exos_Aerospace_VSFBMDZCall_Whitepaper_%s%s" % (K.DATE, K.VER)
os.makedirs(SUBMIT, exist_ok=True)
shutil.copy(PDF,  SUBMIT + STEM + ".pdf")
shutil.copy(DOCX, SUBMIT + STEM + ".docx")
print("SUBMIT:", SUBMIT + STEM + ".docx")
