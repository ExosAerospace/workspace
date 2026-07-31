#!/usr/bin/env python3
"""Three Exos government-readiness compliance docs on the PRIMARY letterhead (dark text on white).
   DOC1 Supplier/SCRM Policy · DOC2 QMS Charter · DOC3 Manufacturing Maturation Plan."""
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

SRC = "assets/EXOS_Letterhead_Greenville_TX_PRIMARY.docx"
NAVY = RGBColor(0x0b, 0x1a, 0x3a); GOLD = RGBColor(0xb8, 0x86, 0x1f)
DARK = RGBColor(0x1a, 0x1a, 0x1a); GREY = RGBColor(0x44, 0x44, 0x44)


def new_doc():
    return Document(SRC)


def para(doc, text="", size=11, bold=False, color=DARK, align=None, after=6, before=0, italic=False):
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(after); p.paragraph_format.space_before = Pt(before)
    if align:
        p.alignment = align
    r = p.add_run(text); r.font.size = Pt(size); r.font.bold = bold; r.font.italic = italic
    r.font.color.rgb = color; r.font.name = "Calibri"
    return p


def h1(doc, text, after=6, before=12):
    return para(doc, text, size=13, bold=True, color=NAVY, after=after, before=before)


def bullet(doc, text, size=10.5):
    p = doc.add_paragraph(); p.paragraph_format.left_indent = Inches(0.28); p.paragraph_format.space_after = Pt(4)
    r = p.add_run("▸  "); r.font.size = Pt(size); r.font.bold = True; r.font.color.rgb = GOLD; r.font.name = "Calibri"
    r2 = p.add_run(text); r2.font.size = Pt(size); r2.font.color.rgb = DARK; r2.font.name = "Calibri"
    return p


def title_block(doc, title, subtitle, doctype):
    para(doc, title, size=17, bold=True, color=NAVY, after=1)
    para(doc, subtitle, size=12.5, bold=True, color=GOLD, after=8)
    para(doc, doctype, size=9.5, italic=True, color=GREY, after=12)


def footer_mark(doc):
    para(doc, "", size=6, after=2, before=8)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; p.paragraph_format.space_before = Pt(6)
    r = p.add_run("PROPRIETARY — Exos Aerospace   ·   Unclassified   ·   Exos Aerospace Systems & Technologies, Inc., Greenville, TX")
    r.font.size = Pt(8); r.font.italic = True; r.font.color.rgb = GREY; r.font.name = "Calibri"


IDENT = ("Exos Aerospace is one of only three FAA-licensed reusable rocket launch providers in the US. "
         "This document reflects current company practice and honest program maturity; forward-looking "
         "certifications are marked as targets or in progress.")

# ─────────────────────────────────────────────────────────────────────────────
# DOC 1 — Supplier Management & Supply-Chain Risk Management (SCRM) Policy
# ─────────────────────────────────────────────────────────────────────────────
def build_scrm():
    doc = new_doc()
    title_block(doc, "SUPPLIER MANAGEMENT & SUPPLY-CHAIN RISK MANAGEMENT POLICY",
                "Sourcing, Supplier Quality, Risk & Scalability Governance",
                "Compliance Policy  ·  Rev A  ·  Owner: CEO / Quality  ·  Reviewed annually")
    para(doc, IDENT, size=9.5, italic=True, color=GREY, after=10)

    h1(doc, "1.  Purpose & Scope")
    para(doc, "This policy governs how Exos selects, qualifies, monitors, and manages suppliers and subcontractors "
              "supporting the design, manufacture, and test of Exos launch vehicles and payload services. It applies to "
              "all procurement of flight hardware, materials, tooling, and services, and to any subcontractor that "
              "receives Federal Contract Information (FCI) or Controlled Unclassified Information (CUI).")

    h1(doc, "2.  Federal Standards & Flow-Downs")
    bullet(doc, "Applicable FAR and DFARS clauses are flowed down to suppliers through purchase orders and subcontracts, "
                "including quality, cybersecurity, and export-control requirements.")
    bullet(doc, "Supply-chain risk management aligns to NIST SP 800-161 (Cybersecurity Supply Chain Risk Management).")
    bullet(doc, "Counterfeit-parts avoidance and detection follow DFARS 252.246-7007; suppliers must source from "
                "original manufacturers or authorized distributors and provide traceability on request.")
    bullet(doc, "Safeguarding and cyber-incident reporting for covered defense information flow down per DFARS 252.204-7012.")

    h1(doc, "3.  Supplier Sourcing & Approval")
    bullet(doc, "Procurement of flight-critical items is restricted to suppliers on the Approved Supplier List (ASL).")
    bullet(doc, "Qualification criteria include quality-system maturity, technical capability, financial stability, "
                "export-control posture, cybersecurity readiness, past performance, and traceability.")
    bullet(doc, "New suppliers are qualified via documentation review, first-article inspection, and where warranted a survey/audit "
                "before award; the ASL is reviewed and maintained by Quality.")

    h1(doc, "4.  Supplier Quality & Performance Monitoring")
    bullet(doc, "Active suppliers are scored on a periodic scorecard covering on-time delivery, quality/defect rate (PPM), "
                "and corrective-action responsiveness.")
    bullet(doc, "Nonconforming supplier material is dispositioned through the Exos nonconformance process; recurring issues "
                "trigger a Supplier Corrective Action Request (SCAR) with root-cause and verification of effectiveness.")
    bullet(doc, "Performance is reviewed on a defined cadence (routine review, with escalation for at-risk suppliers); "
                "results feed ASL retention decisions.")

    h1(doc, "5.  Supplier Risk Assessment")
    bullet(doc, "Each key supplier is rated across financial, single-source, geographic, and cyber risk dimensions.")
    bullet(doc, "Ratings drive mitigation: heightened monitoring, buffer stock, qualification of alternates, or contractual "
                "protections. High-risk single-source items are prioritized for second-source qualification.")

    h1(doc, "6.  Capacity & Scalability Assessment")
    bullet(doc, "Lead times and single-source exposure are tracked for critical items so production constraints are visible "
                "before they affect schedule.")
    bullet(doc, "Because current production is low-rate (BLK3 prototype/demonstration), the policy defines surge and "
                "second-source planning to be exercised as demand increases, including alternate-supplier qualification and "
                "capacity commitments ahead of rate ramp.")
    bullet(doc, "Composite raw structures are supplied by Scorpius (Torrance, CA); final build, integration, and test occur "
                "in Greenville, TX. Scalability planning addresses both nodes of this split.")

    h1(doc, "7.  FCI / CUI Subcontractor Flow-Down")
    bullet(doc, "Subcontracts that involve FCI or CUI flow down DFARS 252.204-7012 and the applicable CMMC requirement.")
    bullet(doc, "Each such subcontractor's required CMMC level is verified before award and monitored thereafter; suppliers "
                "must meet or be on a credible path to the required level.")
    bullet(doc, "This is managed under the Exos CMMC 2.0 program, implemented with contractor Atomus on a GCC High / Azure "
                "Government boundary. Exos CMMC 2.0 certification is in progress.")

    h1(doc, "8.  Records")
    bullet(doc, "The supplier master, purchase orders, receipts, and quality records are maintained in the Exos ERP system.")
    bullet(doc, "This policy, the ASL, and supplier risk and scorecard assessments are tracked and reviewed in Mission Control, "
                "the Exos operational-management system.")

    footer_mark(doc)
    out = "drafts/Exos_Supplier_SCRM_Policy.docx"
    doc.save(out); return out


# ─────────────────────────────────────────────────────────────────────────────
# DOC 2 — Quality Management System Charter (AS9100D / ISO 9001-aligned)
# ─────────────────────────────────────────────────────────────────────────────
def build_qms():
    doc = new_doc()
    title_block(doc, "QUALITY MANAGEMENT SYSTEM CHARTER",
                "AS9100D / ISO 9001-Aligned Operating QMS",
                "Quality Charter  ·  Rev A  ·  Owner: CEO / Quality  ·  AS9100D certification: target/in progress")
    para(doc, IDENT, size=9.5, italic=True, color=GREY, after=10)

    h1(doc, "1.  Purpose & Scope")
    para(doc, "This charter establishes the Exos Quality Management System (QMS) as the operating framework for the design, "
              "manufacture, integration, test, and launch-service delivery of Exos vehicles and payload services. The QMS is "
              "structured to align with AS9100D and ISO 9001:2015. AS9100D certification is a target and is in progress; this "
              "charter defines the QMS Exos operates today against those standards.")

    h1(doc, "2.  Quality Policy")
    para(doc, "Exos is committed to delivering safe, reliable, requirement-conforming products and services; to meeting "
              "applicable statutory, regulatory, and customer requirements; and to continually improving the effectiveness of "
              "the QMS. Quality objectives are set, measured, and reviewed by management.")

    h1(doc, "3.  Process Approach & Interactions")
    bullet(doc, "Core processes: engineering/design, procurement and supplier quality, manufacturing and integration, test and "
                "verification, launch operations, and customer/program management.")
    bullet(doc, "Supporting processes: document and record control, training/competency, calibration, corrective action, "
                "internal audit, and management review. Process inputs, outputs, owners, and metrics are defined.")

    h1(doc, "4.  Document & Record Control")
    bullet(doc, "Controlled documents (procedures, work instructions, drawings, specifications) are version-controlled with "
                "defined approval, distribution, and revision.")
    bullet(doc, "Quality records are retained per program and contract requirements and stored in the Exos ERP and document "
                "systems; access to CUI/FCI records is controlled under the CMMC program.")

    h1(doc, "5.  Nonconformance & Corrective/Preventive Action (CAPA)")
    bullet(doc, "Nonconforming material is identified, segregated, dispositioned (use-as-is, rework, repair, scrap), and "
                "documented.")
    bullet(doc, "Root-cause analysis and corrective/preventive action are applied to significant or recurring nonconformances, "
                "with verification of effectiveness before closure.")

    h1(doc, "6.  Internal Audit")
    para(doc, "Internal audits are planned on a defined schedule to assess conformance and effectiveness of the QMS. Findings "
              "are tracked to closure through the CAPA process; auditors are independent of the area audited.")

    h1(doc, "7.  Management Review")
    para(doc, "Leadership reviews QMS performance on a defined cadence, evaluating quality objectives, audit results, "
              "nonconformance and CAPA trends, supplier performance, customer feedback, and improvement actions. Outputs "
              "include resource and improvement decisions.")

    h1(doc, "8.  Supplier Quality")
    para(doc, "Supplier selection, qualification, monitoring, and risk management are governed by the Exos Supplier Management "
              "& Supply-Chain Risk Management (SCRM) Policy, which is an integral element of this QMS.")

    h1(doc, "9.  Continuous Improvement")
    para(doc, "Exos drives improvement through objective measurement, corrective/preventive action, audit findings, and "
              "management-review outputs, prioritizing changes that improve safety, conformance, and reliability.")

    h1(doc, "10.  Path to AS9100D Certification")
    bullet(doc, "Phase 1 — Gap assessment against AS9100D and documentation of the QMS (this charter and supporting procedures).")
    bullet(doc, "Phase 2 — Implementation and evidence generation: internal audits, management reviews, and CAPA maturity.")
    bullet(doc, "Phase 3 — Stage 1/Stage 2 certification audit by an accredited registrar, followed by surveillance.")
    bullet(doc, "In parallel, CMMC 2.0 is in progress with Atomus (GCC High / Azure Government) for CUI safeguarding.")

    footer_mark(doc)
    out = "drafts/Exos_QMS_Charter.docx"
    doc.save(out); return out


# ─────────────────────────────────────────────────────────────────────────────
# DOC 3 — Manufacturing Maturation Plan (DoD MRL 1-10)
# ─────────────────────────────────────────────────────────────────────────────
def build_mmp():
    doc = new_doc()
    title_block(doc, "MANUFACTURING MATURATION PLAN",
                "DoD Manufacturing Readiness Level (MRL) Framework",
                "Manufacturing Plan  ·  Rev A  ·  Program: BLK3 Reusable Suborbital Vehicle  ·  Owner: CEO / Manufacturing")
    para(doc, IDENT, size=9.5, italic=True, color=GREY, after=10)

    h1(doc, "1.  Purpose")
    para(doc, "This plan describes how Exos matures the manufacturing of its BLK3 reusable suborbital vehicle from the current "
              "low-rate/prototype state toward higher-rate, production-ready maturity, using the Department of Defense "
              "Manufacturing Readiness Level (MRL) framework as the assessment and planning basis.")

    h1(doc, "2.  MRL Framework Overview")
    para(doc, "The MRL scale spans MRL 1 (basic manufacturing implications identified) through MRL 10 (full-rate production "
              "demonstrated). Key gates include MRL 4-6 (capability in a laboratory/relevant/production-relevant environment), "
              "MRL 7-8 (production processes demonstrated / pilot-line and low-rate readiness), and MRL 9-10 (low-rate and "
              "full-rate production). MRLs are assessed across threads including technology/industrial base, design, materials, "
              "process capability, quality, manufacturing workforce, facilities, and cost.")

    h1(doc, "3.  Current-State MRL Assessment (BLK3)")
    bullet(doc, "BLK3 is a flight-proven reusable suborbital vehicle produced today at low rate / prototype maturity; Exos is "
                "one of only three FAA-licensed reusable rocket launch providers in the US.")
    bullet(doc, "Manufacturing is split: raw composite structures are produced by Scorpius (Torrance, CA); final build, "
                "integration, and test occur at Exos in Greenville, TX. It is not 100% Texas-built.")
    bullet(doc, "Honest current assessment: most threads sit in the pilot/low-rate band (roughly MRL 5-7) — processes "
                "demonstrated in a relevant/production-relevant environment but not yet proven at sustained rate. Process "
                "controls, tooling, and supplier qualification are maturing; rate production has not been demonstrated.")

    h1(doc, "4.  Target MRLs & Gaps")
    bullet(doc, "Near-term target: mature critical processes to MRL 7-8 (pilot-line demonstration, low-rate production readiness).")
    bullet(doc, "Gaps to close: statistical process control on key composite and integration steps; hard tooling maturity; "
                "second-source/qualified-supplier depth; documented rate capacity; and QMS evidence (AS9100D path).")

    h1(doc, "5.  Maturation Activities")
    bullet(doc, "Tooling — advance from prototype/soft tooling toward production tooling for repeatable, higher-rate build.")
    bullet(doc, "Process controls — define, characterize, and place under statistical control the critical composite, bonding, "
                "and integration processes; capture key characteristics.")
    bullet(doc, "Supplier qualification — qualify and, where single-source, second-source critical suppliers per the SCRM Policy.")
    bullet(doc, "Workforce — grow and cross-train the Greenville manufacturing/test workforce to support rate increases.")

    h1(doc, "6.  Milestones & Timeline")
    bullet(doc, "Milestone 1 — Baseline MRL assessment and gap register completed across all threads.")
    bullet(doc, "Milestone 2 — Critical-process control plans and production-tooling plan established.")
    bullet(doc, "Milestone 3 — Pilot-line demonstration of prioritized processes (toward MRL 7).")
    bullet(doc, "Milestone 4 — Low-rate production readiness demonstrated (toward MRL 8), aligned to CMMC and AS9100D maturity.")
    para(doc, "Timeline is demand-driven and scales with program funding and order volume; dates are managed and tracked in "
              "Mission Control.", size=9.5, italic=True, color=GREY, after=6)

    h1(doc, "7.  Risks & Mitigations")
    bullet(doc, "Single-source composite supply (Scorpius) — mitigation: second-source qualification and buffer planning under the SCRM Policy.")
    bullet(doc, "Low-rate cost/repeatability — mitigation: production tooling and statistical process control.")
    bullet(doc, "Workforce scale — mitigation: hiring and cross-training ahead of rate ramp.")
    bullet(doc, "Compliance maturity — mitigation: parallel AS9100D path and CMMC 2.0 program (Atomus, GCC High / Azure Gov).")

    footer_mark(doc)
    out = "drafts/Exos_Manufacturing_Maturation_Plan.docx"
    doc.save(out); return out


if __name__ == "__main__":
    for fn in (build_scrm, build_qms, build_mmp):
        print("BUILT", fn())
