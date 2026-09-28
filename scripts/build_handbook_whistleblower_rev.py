#!/usr/bin/env python3
"""Build the Employee Handbook whistleblower revision (Rev 2026-09-28) as .docx.

Adds Section 2.5 (Whistleblower Protection & Reporting of Misconduct) and the
conforming carve-outs to 2.2, 2.4, 3.6, 3.8, 3.9 and 12 of the 3.12.26 handbook.
"""
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

OUT = "drafts/Exos_Employee_Handbook_Whistleblower_Revision_2026-09-28.docx"

doc = Document()
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(11)


def h(text, lvl=1):
    doc.add_heading(text, level=lvl)


def p(text, bold=False, italic=False):
    para = doc.add_paragraph()
    r = para.add_run(text)
    r.bold, r.italic = bold, italic
    return para


def bullets(items):
    for i in items:
        doc.add_paragraph(i, style="List Bullet")


def note(text):
    para = doc.add_paragraph()
    r = para.add_run("Change note: " + text)
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x80, 0x80, 0x80)


t = doc.add_heading("EXOS Aerospace Systems & Technologies, Inc.", 0)
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
p("Employee Handbook — Revision: Whistleblower Protection & Conforming Changes", bold=True).alignment = WD_ALIGN_PARAGRAPH.CENTER
p("Amends the Employee Handbook dated 3.12.26  |  Rev. 2026-09-28  |  DRAFT for CEO approval", italic=True).alignment = WD_ALIGN_PARAGRAPH.CENTER

h("Why this revision", 1)
p("The 3.12.26 handbook contains no whistleblower policy. Its only anti-retaliation language is limited to "
  "harassment reports (Sec. 2.2), and its confidentiality and monitoring sections (3.6, 3.8, 3.9) contain no "
  "carve-out for reporting to the government. Because EXOS performs Department of Defense contracts, the "
  "following apply now:")
bullets([
    "DFARS 252.203-7002 (in every DoD contract) — EXOS must inform employees IN WRITING of their whistleblower "
    "rights and protections under 10 U.S.C. § 4701 (formerly § 2409). The handbook is the natural place to do this.",
    "FAR 52.203-19 — EXOS may not require employees to sign internal confidentiality agreements or statements that "
    "restrict lawful reporting of waste, fraud, or abuse, and must notify employees that any existing agreements are "
    "limited accordingly. Current Sec. 3.8 and the Attachment A confidentiality agreement contain no such carve-out.",
    "FAR 52.203-17 / 41 U.S.C. § 4712 — same protections for civilian-agency work (NASA, NOAA, NIH).",
    "18 U.S.C. § 1833(b) (Defend Trade Secrets Act) — whistleblower immunity notice must appear in any policy or "
    "agreement governing confidential information, or EXOS forfeits exemplary damages and attorney fees in a "
    "trade-secret suit against an employee.",
    "FAR 52.203-13 / DFARS 252.203-7004 — written code of conduct, mandatory disclosure, and DoD Hotline poster "
    "(required on contracts above $6M and 120+ days; adopted here now as best practice so we are ready when a "
    "contract crosses that threshold).",
])

h("Summary of changes", 1)
bullets([
    "NEW Sec. 2.5 — Whistleblower Protection & Reporting of Misconduct.",
    "Sec. 2.2 — anti-retaliation sentence broadened and cross-referenced to 2.5.",
    "Sec. 2.4 — Open Door clarified as optional; never a precondition to reporting outside the company.",
    "Sec. 3.6, 3.8, 3.9 — protected-activity carve-out added; DTSA immunity notice added to 3.8.",
    "Sec. 12 — acknowledgment updated to confirm receipt of whistleblower rights notice.",
])

# ---------------------------------------------------------------- 2.5
h("NEW — 2.5 Whistleblower Protection & Reporting of Misconduct", 1)
note("Insert as new Section 2.5, after 2.4 Open Door Policy.")

h("2.5.1 Policy", 2)
p("EXOS is committed to integrity in all of its business, including its work on U.S. Government contracts, "
  "subcontracts, and grants. EXOS encourages employees to report suspected misconduct and strictly prohibits "
  "discharge, demotion, or any other form of discrimination or retaliation against an employee for making a "
  "protected disclosure. This section is the written notice of whistleblower rights that EXOS is required to "
  "provide under DFARS 252.203-7002 and FAR 52.203-17.")

h("2.5.2 What you may report", 2)
p("Employees are protected when they disclose information they reasonably believe is evidence of:")
bullets([
    "gross mismanagement of a federal contract or grant;",
    "a gross waste of federal funds;",
    "an abuse of authority relating to a federal contract or grant;",
    "a violation of law, rule, or regulation related to a federal contract or grant, including the competition "
    "for or negotiation of a contract (for example: fraud, false statements, mischarging of labor or costs, "
    "falsified test or inspection records, kickbacks, bribery, gratuities, or conflicts of interest);",
    "a substantial and specific danger to public health or safety;",
    "export control violations (ITAR/EAR), mishandling of Controlled Unclassified Information, or cybersecurity "
    "incidents; or",
    "any other violation of law or of EXOS policy.",
])
p("A disclosure is protected even if it is made in the ordinary course of your job duties, and even if the "
  "information turns out to be mistaken, so long as you reasonably believed it when you reported it.")

h("2.5.3 Who you may report to", 2)
p("You may report internally, externally, or both. You are never required to report internally first, and you "
  "do not need EXOS's permission or notice before reporting externally.")
p("Internal channels:", bold=True)
bullets([
    "your supervisor or any member of management;",
    "Human Resources;",
    "the Chief Executive Officer; or",
    "the Mission Control Ethics & Compliance Report tool (https://mc.exosaero.space/report.html). "
    "You may submit anonymously; anonymous reports are accepted and investigated to the extent possible.",
])
p("External recipients protected by law (10 U.S.C. § 4701 / 41 U.S.C. § 4712):", bold=True)
bullets([
    "a Member of Congress or a representative of a committee of Congress;",
    "an Inspector General (DoD Office of Inspector General; NASA OIG; or the IG of any other agency);",
    "the Government Accountability Office;",
    "a federal employee responsible for contract oversight or management at the relevant agency "
    "(e.g., a Contracting Officer or Contracting Officer's Representative);",
    "an authorized official of the Department of Justice or other law enforcement agency;",
    "a court or grand jury; or",
    "a management official or other employee of EXOS, or of a prime or subcontractor, who has responsibility "
    "to investigate, discover, or address misconduct.",
])
p("Employees may also report possible violations of law to, and communicate with, the Securities and Exchange "
  "Commission, the Equal Employment Opportunity Commission, the Occupational Safety and Health Administration, "
  "the National Labor Relations Board, or any other federal, state, or local agency, without notice to EXOS.")
p("DoD Hotline: 1-800-424-9098  |  www.dodig.mil/hotline")
p("NASA OIG Hotline: 1-800-424-9183  |  oig.nasa.gov/hotline")

h("2.5.4 No retaliation", 2)
p("EXOS will not discharge, demote, suspend, threaten, harass, reduce the pay or benefits of, or otherwise "
  "discriminate against any employee because the employee made a protected disclosure, participated in an "
  "investigation, or refused to participate in conduct the employee reasonably believes is unlawful. Any "
  "employee, supervisor, or manager who retaliates will be subject to discipline up to and including "
  "termination. Reprisal may be reported through any channel in 2.5.3.")
p("Under 10 U.S.C. § 4701 and 41 U.S.C. § 4712, an employee who believes they have been subjected to reprisal "
  "may file a complaint with the Inspector General of the agency concerned within three (3) years after the "
  "reprisal occurred. Remedies may include reinstatement, back pay, compensatory damages, and attorney fees. "
  "These rights cannot be waived by any agreement, policy, form, or condition of employment, including "
  "pre-dispute arbitration agreements.")

h("2.5.5 Management's duty to escalate; mandatory disclosure", 2)
p("Any manager who receives a report under this section must promptly forward it to the CEO (or, if the report "
  "concerns the CEO, to the Board of Directors). EXOS will investigate promptly and keep the reporter's "
  "identity confidential to the extent permitted by law and consistent with a thorough investigation. Where "
  "EXOS has credible evidence that a principal, employee, agent, or subcontractor has committed a violation of "
  "federal criminal law involving fraud, conflict of interest, bribery, or gratuities, or a violation of the "
  "civil False Claims Act, in connection with a federal contract or subcontract, EXOS will timely disclose it "
  "in writing to the agency Office of Inspector General and the Contracting Officer as required by "
  "FAR 52.203-13.")

h("2.5.6 Classified, export-controlled, and CUI information", 2)
p("Nothing in this section authorizes disclosing classified information, export-controlled technical data, or "
  "Controlled Unclassified Information to a recipient not authorized to receive it. When a report involves such "
  "information, make it through an Inspector General hotline or to an authorized government official, who can "
  "receive it through proper channels. If you are unsure, you may describe the concern in general terms without "
  "including the controlled content.")

h("2.5.7 Postings", 2)
p("EXOS displays the DoD Hotline poster and applicable agency hotline posters in common work areas and on the "
  "company intranet.")

# ---------------------------------------------------------------- conforming edits
h("CONFORMING CHANGES", 1)

h("2.2 Non-Harassment Policy — replace last sentence", 2)
p("Current: “Retaliation against employees who report concerns in good faith is strictly prohibited.”", italic=True)
p("Revised: “Retaliation against any employee who reports a concern, participates in an investigation, or "
  "makes a protected disclosure is strictly prohibited. See Section 2.5.”")

h("2.4 Open Door Policy — add at end", 2)
p("“The Open Door Policy is one option for raising concerns. It is never a precondition to, and does not limit, "
  "an employee's right to report concerns to any government agency or other recipient listed in Section 2.5.”")

h("3.6 Technology, Email & Communications Policy — add after the bullet list", 2)
p("“The restriction on transmitting confidential company data does not apply to disclosures protected by "
  "Section 2.5 or Section 3.8 (Protected Activity).”")

h("3.8 Data Protection & Confidential Information — add at end", 2)
p("Protected Activity. “Nothing in this handbook, in any EXOS confidentiality or invention assignment agreement, "
  "or in any other EXOS policy prohibits or restricts an employee from: (a) reporting waste, fraud, abuse, or "
  "any possible violation of law or regulation to a designated investigative or law enforcement representative "
  "of a federal department or agency authorized to receive such information, to an Inspector General, to "
  "Congress, or to any other government agency; (b) participating in or cooperating with any government "
  "investigation or proceeding; (c) receiving an award from a government agency for information provided; or "
  "(d) discussing wages, hours, or other terms and conditions of employment as protected by Section 7 of the "
  "National Labor Relations Act. Employees do not need prior authorization from, or to notify, EXOS before "
  "doing so. In accordance with FAR 52.203-19, EXOS hereby notifies all employees that any prior "
  "confidentiality agreement or statement is limited by, and does not supersede, these rights.”")
p("Defend Trade Secrets Act Notice (18 U.S.C. § 1833(b)). “An individual shall not be held criminally or "
  "civilly liable under any federal or state trade secret law for the disclosure of a trade secret that (A) is "
  "made (i) in confidence to a federal, state, or local government official, either directly or indirectly, or "
  "to an attorney, and (ii) solely for the purpose of reporting or investigating a suspected violation of law; "
  "or (B) is made in a complaint or other document filed in a lawsuit or other proceeding, if such filing is "
  "made under seal. An individual who files a lawsuit for retaliation by an employer for reporting a suspected "
  "violation of law may disclose the trade secret to the individual's attorney and use the trade secret "
  "information in the court proceeding, if the individual files any document containing the trade secret under "
  "seal and does not disclose the trade secret, except pursuant to court order.”")

h("3.9 Privacy & Monitoring — add at end", 2)
p("“EXOS will not use its monitoring rights to identify, discourage, or retaliate against an employee for a "
  "protected disclosure under Section 2.5.”")

h("12. Employee Acknowledgment — add sentence", 2)
p("“I acknowledge that I have received written notice of my whistleblower rights and protections under "
  "10 U.S.C. § 4701 and 41 U.S.C. § 4712 (Section 2.5), and that nothing in this handbook or in any agreement "
  "with EXOS restricts my right to report possible violations of law to the government.”")

# ---------------------------------------------------------------- rollout
h("Rollout (internal — not part of handbook text)", 1)
bullets([
    "Reporting channel designated: Mission Control Ethics & Compliance Report tool (/report.html).",
    "Amend Attachment A (Confidential Information and Invention Assignment Agreement) with the same "
    "Protected Activity + DTSA language — FAR 52.203-19 reaches that agreement too.",
    "Re-issue the handbook and collect a fresh signed acknowledgment from every current employee "
    "(the 7/30/26 acknowledgments predate this notice).",
    "Post the DoD Hotline poster (and NASA OIG poster) in the shop and office.",
    "Add a short whistleblower module to the annual employee training review.",
    "Final review by outside counsel, engaged per contract at signature/issuance.",
])

doc.save(OUT)
print(OUT)
