#!/usr/bin/env python3
"""send_partner_dd_authorization_esign.py — ExoSign "Partner Due Diligence Intake & Background Check Authorization".
Jon 2026-10-21 06:32: full DD on a prospective teaming partner (first-flight payload bay buyer → AEDC Velocity
Alliance on-ramp). The partner fills in his own personal + company details in the envelope (ExoSign fillable
fields) and authorizes Exos to run OFAC/CSL screening and a consumer background check.

Sensitive answers (SSN, DOB, passport/DL numbers, EIN) never appear in the document or the executed-copy email —
the server writes them to mission-control/data/esign-pii/<envelope>.json (0600) for the screening run.
FCRA basis: the subject's written instructions, 15 U.S.C. §1681b(a)(2).

Usage:
  python3 scripts/send_partner_dd_authorization_esign.py --name "Full Name" --email a@b.com --company "Co, Inc." [--title CEO]
      (dry run: prints the document text + field list; --preview writes /tmp/partner_dd_preview.html)
  ... --send          creates the envelope; ExoSign emails him the signing link (he is the only signer).
"""
import argparse, datetime, html, json, os, sys, urllib.request, http.cookiejar

WS = "/Users/exomac/.openclaw/workspace"
BASE = "http://127.0.0.1:8080"
RIGHTS_URL = "https://files.consumerfinance.gov/f/documents/bcfp_consumer-rights-summary_2018-09.pdf"
FIELDS = []


def f(key, label, type="text", required=True, sensitive=False, options=None, placeholder=None):
    """Register a fillable field and return its placeholder span."""
    d = {"key": key, "label": label, "type": type, "required": required, "sensitive": sensitive}
    if options: d["options"] = options
    if placeholder: d["placeholder"] = placeholder
    FIELDS.append(d)
    return f'<span class="esign-field" data-field="{key}"></span>'


YN = ["No", "Yes"]


def row(label, field_html, note=""):
    n = f'<div style="font-size:11px;color:#777;">{note}</div>' if note else ""
    return (f'<tr><td style="width:38%;padding:6px 8px;border-bottom:1px solid #eee;vertical-align:top;font-weight:bold;'
            f'color:#0a1628;">{label}</td><td style="padding:6px 8px;border-bottom:1px solid #eee;">{field_html}{n}</td></tr>')


def table(rows):
    return '<table style="width:100%;border-collapse:collapse;font-size:13px;margin:6px 0 14px;">' + "".join(rows) + "</table>"


def build_html(name, company, title):
    today = datetime.date.today().strftime("%B %d, %Y")
    N, C = html.escape(name), html.escape(company)
    conf = '<span style="font-size:10px;color:#b45309;">&#128274; confidential — not shown on the signed copy</span>'
    h = [f"""<div style="font-family:Arial,sans-serif;color:#222;line-height:1.45;">
<div style="border-bottom:3px solid #0a1628;padding-bottom:8px;margin-bottom:14px;">
  <div style="font-size:18px;font-weight:bold;color:#0a1628;">EXOS AEROSPACE SYSTEMS &amp; TECHNOLOGIES, INC.</div>
  <div style="font-size:11px;color:#555;">299 FM 1903, Greenville, TX 75402 · www.exosaero.com</div>
</div>
<h2 style="text-align:center;color:#0a1628;margin:6px 0;">PARTNER DUE DILIGENCE INTAKE<br>&amp; BACKGROUND CHECK AUTHORIZATION</h2>
<p style="text-align:center;font-size:12px;color:#555;">Prepared {today} for {N}{(', ' + html.escape(title)) if title else ''} — {C}</p>
<p>Exos Aerospace Systems &amp; Technologies, Inc. ("<b>Exos</b>") screens every prospective teaming partner before a
U.S. Government or commercial teaming arrangement, including under the AEDC Velocity Alliance. Please complete the
highlighted fields, review the authorization in Part E, and sign at the bottom. Fields marked {conf} are stored
separately with restricted access and are used only to run the checks described below.</p>

<h3 style="color:#0a1628;border-bottom:1px solid #0a1628;">Part A — Individual</h3>"""]
    h.append(table([
        row("Full legal name (first, middle, last)", f("full_legal_name", "Full legal name")),
        row("Other names used (maiden, prior, aliases)", f("other_names", "Other names used", required=False, placeholder="None")),
        row("Date of birth", f("dob", "Date of birth", "date", sensitive=True), conf),
        row("Social Security Number", f("ssn", "Social Security Number", sensitive=True, placeholder="###-##-####"), conf + " · required for U.S. persons; non-U.S. persons enter N/A"),
        row("Place of birth (city, country)", f("place_of_birth", "Place of birth")),
        row("Citizenship(s)", f("citizenship", "Citizenship(s)", placeholder="List every citizenship held")),
        row("U.S. person status (22 CFR 120.62)", f("us_person_status", "U.S. person status", "select", options=["U.S. citizen", "U.S. lawful permanent resident", "Protected individual (8 U.S.C. 1324b)", "Not a U.S. person"])),
        row("Passport country and number", f("passport", "Passport country and number", required=False, sensitive=True), conf),
        row("Driver's license state and number", f("drivers_license", "Driver's license state and number", sensitive=True), conf),
        row("Current residential address", f("current_address", "Current residential address", "textarea")),
        row("Residential addresses, past 7 years", f("prior_addresses", "Prior addresses (7 years)", "textarea", placeholder="Address — from/to (MM/YYYY)"), "Needed for county-level criminal record searches."),
        row("Email", f("email", "Email", "email")),
        row("Mobile phone", f("phone", "Mobile phone", "tel")),
        row("LinkedIn / professional profile URL", f("linkedin", "LinkedIn URL", required=False)),
        row("Employment, past 10 years", f("employment_history", "Employment history (10 years)", "textarea", placeholder="Employer — title — from/to")),
    ]))
    h.append('<h3 style="color:#0a1628;border-bottom:1px solid #0a1628;">Part B — Company</h3>')
    h.append(table([
        row("Company full legal name", f("company_legal_name", "Company legal name")),
        row("DBA / trade names", f("company_dba", "DBA / trade names", required=False)),
        row("Entity type and state/country of formation", f("company_formation", "Entity type and jurisdiction", placeholder="e.g. Delaware C-corp")),
        row("Year formed", f("company_year", "Year formed")),
        row("Principal business address", f("company_address", "Company address", "textarea")),
        row("Website", f("company_website", "Website", required=False)),
        row("EIN / tax ID", f("company_ein", "EIN / tax ID", sensitive=True), conf),
        row("CAGE code / UEI (SAM.gov)", f("company_cage_uei", "CAGE / UEI", required=False, placeholder="Enter 'Not registered' if none")),
        row("Your title and ownership %", f("signer_role", "Your title and ownership %")),
        row("Beneficial owners (25% or more)", f("beneficial_owners", "Beneficial owners", "textarea", placeholder="Name — % — citizenship (one per line)")),
        row("Officers and directors", f("officers_directors", "Officers and directors", "textarea", placeholder="Name — title")),
        row("Parent company / affiliates", f("parent_affiliates", "Parent company / affiliates", "textarea", required=False, placeholder="None")),
        row("Any foreign ownership, control or influence?", f("foci", "Foreign ownership, control or influence", "select", options=YN)),
        row("Main investors / sources of funds", f("funding_sources", "Main investors / sources of funds", "textarea")),
        row("Company holds JCP (DD 2345) / CMMC?", f("jcp_cmmc", "JCP / CMMC status", required=False, placeholder="e.g. JCP active #…, CMMC L2 self-assessment in SPRS")),
    ]))
    h.append('<h3 style="color:#0a1628;border-bottom:1px solid #0a1628;">Part C — Disclosures (you and the company)</h3>')
    qs = [
        ("q_criminal", "Felony conviction, or any pending felony charge, in the past 10 years?"),
        ("q_debarment", "Ever suspended, debarred, excluded or proposed for debarment from U.S. Government contracting?"),
        ("q_sanctions", "Ever named on, or owned 50%+ by anyone named on, a U.S., UN, EU or UK sanctions or export denial list?"),
        ("q_export", "Ever charged with or penalized for a violation of export control (ITAR/EAR) or sanctions laws?"),
        ("q_bankruptcy", "Personal or company bankruptcy, receivership or insolvency in the past 7 years?"),
        ("q_litigation", "Any pending litigation, regulatory or SEC/FINRA action, or fraud judgment involving you or the company?"),
        ("q_foreign_gov", "Any current or past employment, funding or affiliation with a foreign government, military or state-owned company?"),
    ]
    h.append(table([row(q, f(k, q, "select", options=YN)) for k, q in qs] + [
        row("If you answered Yes to anything above, explain", f("disclosure_details", "Explanation of Yes answers", "textarea", required=False, placeholder="Leave blank if all No")),
    ]))
    h.append(f"""<h3 style="color:#0a1628;border-bottom:1px solid #0a1628;">Part D — What Exos will check</h3>
<ul style="font-size:13px;">
<li><b>Sanctions and restricted-party screening</b> of you, the company and its listed owners and officers: the OFAC Specially Designated Nationals (SDN) and other OFAC lists, the U.S. Consolidated Screening List (Commerce, State and Treasury), and SAM.gov exclusions.</li>
<li><b>Consumer background report on you</b>, from Exos's background screening provider (a consumer reporting agency): identity and SSN trace, address history, national/state/county criminal records, sex-offender registries, federal and state civil litigation, bankruptcies, liens and judgments, and verification of the employment and professional credentials you list above.</li>
<li><b>Company diligence</b>: corporate registry and good standing, SAM.gov registration, business credit, beneficial ownership, litigation and regulatory history, and public news and media review.</li>
</ul>
<p style="font-size:13px;">Exos will <b>not</b> obtain a personal credit report or an "investigative consumer report" (interviews with people who know you) without first giving you separate written notice and getting your consent.</p>

<h3 style="color:#0a1628;border-bottom:1px solid #0a1628;">Part E — Authorization, certification and consent</h3>
<div style="font-size:13px;border:1px solid #0a1628;padding:10px 12px;border-radius:4px;">
<p><b>1. Authorization.</b> I, the undersigned, instruct and authorize Exos and its designated consumer reporting agency and screening providers to obtain the consumer reports and records described in Part D about me, for the sole purpose of evaluating a proposed business and teaming relationship between Exos and {C}. This is my written instruction under the Fair Credit Reporting Act, 15 U.S.C. §1681b(a)(2). This authorization is valid for twelve (12) months from the date I sign, or for the duration of any resulting relationship, whichever is longer, and I may revoke it in writing to jquinn@exosaero.com at any time for checks not yet started.</p>
<p><b>2. Company authorization.</b> I represent that I am authorized to act for {C}, and on its behalf I authorize Exos to perform the company diligence and restricted-party screening in Part D on the company and the owners, officers and directors listed in Part B.</p>
<p><b>3. My rights.</b> I acknowledge receipt of <a href="{RIGHTS_URL}">A Summary of Your Rights Under the Fair Credit Reporting Act</a> (CFPB). If Exos decides not to proceed based in whole or part on a consumer report, Exos will tell me, give me the name and contact details of the reporting agency, and I may get a free copy of the report and dispute anything inaccurate with that agency.</p>
<p>{f("wants_report_copy", "Send me a free copy of any consumer report obtained", "checkbox", required=False)} Please send me a free copy of any consumer report Exos obtains about me.</p>
<p><b>4. Confidentiality and use.</b> Exos will keep all information on this form and all reports confidential, restrict access to the personnel performing the review, use them only for the purpose in paragraph 1, not sell or share them for any other purpose, and dispose of them securely when no longer needed for that purpose or for legal record-keeping.</p>
<p><b>5. Certification.</b> I certify that the information I have provided is true, correct and complete. I understand that a false statement or material omission may end the proposed relationship. I agree to tell Exos promptly if any answer in Part C changes.</p>
<p><b>6. Electronic signature.</b> I agree to sign this document electronically and that my electronic signature has the same effect as a handwritten one under the U.S. E-SIGN Act and UETA.</p>
<p>{f("ack_authorize", "I authorize the background check and screening described above", "checkbox")} <b>I have read this form and authorize the background check and screening described above.</b></p>
</div>
<p style="margin-top:22px;"><b>{C.upper()}</b><br>Signed by {N}{(', ' + html.escape(title)) if title else ''}, individually and on behalf of the company.</p>
</div>""")
    return "".join(h)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True); ap.add_argument("--email", required=True)
    ap.add_argument("--company", required=True); ap.add_argument("--title", default="")
    ap.add_argument("--send", action="store_true"); ap.add_argument("--preview", action="store_true")
    a = ap.parse_args()
    body = build_html(a.name, a.company, a.title)
    first = a.name.split()[0]
    env = {"title": f"Partner Due Diligence & Background Check Authorization — {a.company}", "html": body, "fields": FIELDS,
           "subject": "Exos partner onboarding: due diligence form and background check authorization",
           "message": (f"{first}, thanks again for the conversation. As part of bringing {a.company} on as an Exos teaming "
                       "partner, we run standard due diligence on every partner. Please complete the highlighted fields and sign; "
                       "it takes about 15 minutes. Sensitive items such as your SSN and date of birth are stored separately "
                       "and are not shown on the signed copy. Best regards, John Quinn"),
           "signers": [{"name": a.name, "email": a.email, "role": f"{a.title + ', ' if a.title else ''}{a.company}"}]}
    if a.preview:
        open("/tmp/partner_dd_preview.html", "w").write(f"<html><body style='max-width:820px;margin:20px auto'>{body}</body></html>")
        print("preview: /tmp/partner_dd_preview.html")
    if not a.send:
        print(f"DRY RUN — {len(FIELDS)} fields ({sum(x['sensitive'] for x in FIELDS)} sensitive, {sum(x['required'] for x in FIELDS)} required)")
        print(json.dumps({k: v for k, v in env.items() if k not in ("html", "fields")}, indent=1)); return
    sec = json.load(open(os.path.expanduser("~/.openclaw/secrets.json")))
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    op.open(urllib.request.Request(BASE + "/api/docusign/login", data=json.dumps({"passcode": sec["mc_docusign_passcode"]}).encode(), headers={"Content-Type": "application/json"}), timeout=30)
    r = op.open(urllib.request.Request(BASE + "/api/esign/create", data=json.dumps(env).encode(), headers={"Content-Type": "application/json"}), timeout=60)
    out = json.loads(r.read()); print(json.dumps({"id": out.get("id"), "success": out.get("success")}))
    os.makedirs(WS + "/logs", exist_ok=True)
    open(WS + "/logs/partner-dd-envelopes.log", "a").write(f"{datetime.datetime.now().isoformat()} {out.get('id')} {a.company} {a.email}\n")


if __name__ == "__main__":
    main()
