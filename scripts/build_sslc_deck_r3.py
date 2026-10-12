#!/usr/bin/env python3
"""Build SSLC board offer deck r3 from r2: align to what was sent to the SSLC board
(10/9 Offer Summary, 10/8 + 10/10 board emails) and add a Clarifications slide.
Jon 2026-10-11: "go with what was sent to the board; add clarifications that fill the gaps."
"""
import copy
from pptx import Presentation
from pptx.util import Pt
from pptx.opc.constants import RELATIONSHIP_TYPE as RT

SRC = 'drafts/Exos_SSLC_Board_Offer_Overview_2026-10-10_r2.pptx'
OUT = 'drafts/Exos_SSLC_Board_Offer_Overview_2026-10-11_r3_FINAL.pptx'

p = Presentation(SRC)
S = p.slides


def shp(slide, name):
    for sh in slide.shapes:
        if sh.name == name:
            return sh
    raise KeyError(name)


def set_text(slide, name, text):
    """Replace text keeping the first run's formatting; '\n' splits paragraphs."""
    tf = shp(slide, name).text_frame
    lines = text.split('\n')
    paras = tf.paragraphs
    # template paragraph/run
    p0 = paras[0]._p
    for extra in paras[1:]:
        extra._p.getparent().remove(extra._p)
    r0 = p0.findall('{http://schemas.openxmlformats.org/drawingml/2006/main}r')
    for r in r0[1:]:
        p0.remove(r)
    tf.paragraphs[0].runs[0].text = lines[0]
    for ln in lines[1:]:
        newp = copy.deepcopy(p0)
        p0.getparent().append(newp)
        p0 = newp
    for para, ln in zip(tf.paragraphs, lines):
        para.runs[0].text = ln


def set_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def clone_shape(slide, name, new_name, dy):
    el = copy.deepcopy(shp(slide, name)._element)
    slide.shapes._spTree.append(el)
    new = slide.shapes[-1]
    new.top = new.top + dy
    new.name = new_name
    return new


FOOT = 'NEGOTIATING TERMS — NOT A BINDING OFFER'

# ---------- Slide 1 ----------
s = S[0]
set_text(s, 'Text 5', 'October 11, 2026  ·  Revised (r3)')
set_text(s, 'Text 6', 'CONFIDENTIAL — NEGOTIATING TERMS — NOT A BINDING OFFER')
set_notes(s, 'Revised 10/11 (r3). Every figure matches what was sent to the SSLC board: the revised Option B Offer Summary (10/9), '
             'the 10/8 "Best and final" email and the 10/10 "update 2" email. The Clarifications slide fills gaps in those documents '
             'from the executed May 2025 Asset Acquisition Agreement (AAA) and SSLC QuickBooks. Negotiating terms; not a final or binding offer.')

# ---------- Slide 2 ----------
s = S[1]
set_text(s, 'Text 1', 'Three motions requested of the SSLC Board.')
set_text(s, 'Text 4', 'Motion 1: §3 exclusivity — 90-day window begins on board approval (May 2025 AAA)\n'
                      'Motion 2: Full read-only QB Online access for diligence (Cal. Corp. Code §1602 + AAA §§5, 8; under 7/27/2021 NDA)\n'
                      'Motion 3: Consent to ERP/MRP & inventory evaluation using QB data (confidential under NDA)')
set_notes(s, 'The three actions requested of the SSLC board. Motion 1: confirm §3 exclusivity under the May 2025 Asset Acquisition '
             'Agreement; the 90-day period begins on approval. Motion 2: full read-only QuickBooks Online access for John Quinn and '
             "Exos's finance reviewer to reconcile the $864K 'billed-ahead' balance and shared-facility costs. Basis: Cal. Corp. Code "
             '§1602 director inspection right + AAA §5 (diligence as a condition to closing) and §8 (due-diligence requests under the '
             '7/27/2021 NDA). Motion 3: consent to Exos using the same data to evaluate ERP/MRP and inventory systems for the combined '
             'operation. Governance: John Quinn abstains on all motions as an interested director.')

# ---------- Slide 3 ----------
s = S[2]
set_text(s, 'Text 15', "A $5.1M fiscal year requires approximately $1.46M per quarter — nearly double last quarter's pace of $713K — "
                       "starting Oct 1st. Exos's offer removes the funding risk, pays SSLC's verified debts at face, and gives SSLC "
                       'holders direct upside.')
set_notes(s, "SSLC's own numbers, presented factually. $198K cash and $713K last quarter are from the 10/8 board email and the "
             'Offer Summary. The $5.1M M1 milestone needs nearly double that quarterly pace.')

# ---------- Slide 5: restore debt line, totals per Offer Summary ----------
s = S[4]
dy = 2267712 - 1883664  # empty slot (Shape 11) is one row below Text 9/10
a = clone_shape(s, 'Text 9', 'Text 12', dy)
b = clone_shape(s, 'Text 10', 'Text 13', dy)
set_text(s, 'Text 12', 'SSLC debts paid at face (est.; verify in QB)')
set_text(s, 'Text 13', '~$500K')
set_text(s, 'Text 18', '① Cash & debt relief at close')
set_text(s, 'Text 19', '$4.36M')
set_text(s, 'Text 24', '② Total commitment (① + Exos equity)')
set_text(s, 'Text 25', '$5.36M')
set_text(s, 'Text 26', 'Equity awarded at execution\n(targeted by year-end 2026)\nRestricted at issuance (Rule 504)\n'
                       'Part of RTO public float\nFreely tradeable at listing')
set_notes(s, 'Matches the Offer Summary sent to the board (10/9). ① $4.36M = $2.51M cash + $60K SSLC transaction costs + $790K '
             'credit for Exos\'s existing stake (non-cash) + ~$500K SSLC debts paid at face + $500K working-capital bridge. '
             'Per the 10/8 email, Exos pays every verified SSLC debt in full, at face value, at closing, including Microcosm and '
             'Wertz; ~$500K is the QuickBooks estimate, confirmed in diligence. ② $5.36M adds the $1.0M EAI units. Per the 10/10 '
             'update, the $1.0M stock was moved from earn-outs to award at execution, targeted by year-end 2026. It counts toward '
             'the Rule 504 $10M rolling cap. Same in all three scenarios.')

# ---------- Slide 6: tank earn-out basis, M2/M5 per Offer Summary ----------
s = S[5]
set_text(s, 'Text 15', 'Earn-out on IM tank revenue\n(modeled 3%/5%/7%), cap $300K/yr, FY27–FY31')
set_text(s, 'Text 17', 'IM tank revenue\neach year FY27–FY31')
set_text(s, 'Text 19', '$150K/yr\n→$750K total')
set_text(s, 'Text 21', '$250K/yr\n→$1.25M total')
set_text(s, 'Text 23', '$300K/yr (cap)\n→$1.5M total')
set_text(s, 'Text 39', 'M2  Nebula/OTV production contract signed  →$200K')
set_text(s, 'Text 41', 'Production contract signed')
set_text(s, 'Text 49', 'At contract execution')
set_text(s, 'Text 75', 'M5  BLK3 tank qualification complete  →$200K (High)')
set_text(s, 'Text 77', 'BLK3 tank qualification complete')
set_text(s, 'Text 85', 'At BLK3 tank cert')
set_notes(s, 'Matches the Offer Summary (10/9). Tank earn-out: on Intuitive Machines tank revenue FY27–FY31, cap $300K/yr, modeled '
             'at 3% / 5% / 7% (Low/Base/High) = $750K / $1.25M / $1.5M. M1 (all): SSLC FY27 revenue ≥$5.1M → $200K, pays FY28 Q1 '
             'if verified. M2 (Base/High): Nebula/OTV production contract signed → $200K at contract execution (any year FY27–FY30). '
             'M3 (Base/High): annual revenue ≥$10M → $250K (est. FY29). M4 (High): ≥$20M → $250K (est. FY31). M5 (High): BLK3 tank '
             'qualification complete → $200K at Exos BLK3 tank cert (est. FY27–FY28). Stock earn-out: 0.0% / 0.25% / 0.50% FD '
             'issued at RTO listing, same lockup as Exos principals; $0 / $625K / $1.5M at listing value ($250M / $300M). At the '
             '409A they are $0 / $424K / $848K. Total earn-outs $950K / $2,525K / $4,100K (③ minus ②).')

# ---------- Slide 7 ----------
s = S[6]
for n, v in (('Text 5', '$6.3M'), ('Text 10', '$7.9M'), ('Text 15', '$9.5M'),
             ('Text 22', '$12.0M'), ('Text 27', '$15.8M'), ('Text 32', '$19.4M')):
    set_text(s, n, v)
set_notes(s, 'Matches the Offer Summary (10/9). ③ 5-yr total = ② $5.36M + earn-outs: Low $6.31M / Base $7.885M / High $9.46M '
             '(rounded on the slide). ④ If all Exos stock is held to 2031: $12.0M / $15.8M / $19.4M. This is an alternative to ③, '
             'not added to it, and assumes RTO completion, ~30% dilution and management-projected valuations. Forward-looking '
             'projection, not a promise; RTO may not close (SEC Rule 10b-5). Chart is the same one in the board package.')

# ---------- Slide 8 ----------
s = S[7]
set_text(s, 'Text 19', 'Units awarded at execution of the Definitive Agreement, targeted by year-end 2026. Targeted RTO ~6 months '
                       'post-financing. Not assured — RTO may not close.')
set_notes(s, 'Per the 10/10 update to the board, the $1.0M EAI units moved from earn-outs to award at execution, targeted by '
             'year-end 2026. At the ~$169.7M 409A this is ~0.59% fully diluted. Earn-out stock (0.0% / 0.25% / 0.50%) issued at '
             'the RTO listing brings total Exos equity to ~0.59%–1.09%. Rule 504 is U.S.-only; Japan-round EAI units are Reg S '
             'and stay separate.')

# ---------- Slide 9 ----------
s = S[8]
set_text(s, 'Text 7', 'Exos has an option pool for key employees. The allocation, key-employee retention and new-hire structure '
                      'will be mutually agreed in the Definitive Agreement.')

# ---------- Slide 10: commitments per what was sent ----------
s = S[9]
set_text(s, 'Text 4', 'at closing (≤90 days after exclusivity, AAA §6)')
set_text(s, 'Text 7', 'at closing (seller-side, $60K)')
dy = 1682496 - 1298448
clone_shape(s, 'Text 6', 'Text 9', dy)
clone_shape(s, 'Text 7', 'Text 10', dy)
set_text(s, 'Text 9', 'SSLC debts paid at face (~$500K est.)')
set_text(s, 'Text 10', 'at closing — every verified debt, in full')
set_text(s, 'Text 13', 'at closing')
set_text(s, 'Text 16', 'at execution (targeted by year-end 2026)')
set_text(s, 'Text 18', '5% escrow holdback')
set_text(s, 'Text 19', 'released at 12-month anniversary (AAA §7)')
set_text(s, 'Text 22', 'at closing')
set_text(s, 'Text 27', 'Motion 1: confirm §3 exclusivity  →  90 days  →  closing (AAA §6)')
set_notes(s, 'Every dollar and commitment Exos is making, as sent to the board (Offer Summary 10/9; emails 10/8 and 10/10). '
             'Funding is committed at closing; we are not representing that financing is already secured. Under AAA §6, closing '
             'occurs within 90 days of exclusivity; §3 extension is not unreasonably withheld. The 5% escrow holdback is released '
             'at the 12-month anniversary (AAA §7, Offer Summary Key Terms).')

# ---------- Slide 11 ----------
s = S[10]
set_text(s, 'TextBox 8', 'Approve a 90-day exclusivity period beginning on the date of this approval.\n'
                         'Extension not unreasonably withheld (per §3). Allows both parties to proceed to\n'
                         'diligence, the Definitive Agreement, and closing (within 90 days, AAA §6).')
set_text(s, 'TextBox 15', 'Authorize an all-access or accountant user for John Quinn and one Exos finance reviewer.\n'
                          'Purpose: reconcile the $864K "billed-ahead" balance and shared-facility costs (Microcosm\n'
                          'offset) before close.  Basis: Cal. Corp. Code §1602 director inspection right + AAA §§5, 8\n'
                          'confirmatory diligence.  Confidential under the 7/27/2021 NDA.\n'
                          'Access to be granted no later than October 15, 2026.')
set_notes(s, 'Motion 1: §3 exclusivity under the May 2025 AAA; 90 days from approval, extension not unreasonably withheld. '
             'Motion 2: full read-only QuickBooks Online access (accountant or all-access user) for John Quinn and one Exos finance '
             'reviewer. Basis: Cal. Corp. Code §1602 + AAA §5 (diligence as a closing condition) and §8 (due-diligence requests '
             'under the 7/27/2021 NDA). Motion 3: consent to ERP/MRP and inventory evaluation; evaluation only. Governance: John '
             'Quinn is an interested director (Exos is the offeror and Exos holds a $31.2K loan to SSLC). He abstains on all three '
             'motions; each is decided by the disinterested directors.')

# ---------- Slide 12 ----------
s = S[11]
set_text(s, 'Text 5', 'Board Motions 1–3')
set_text(s, 'Text 6', 'Requested of the SSLC Board')
set_text(s, 'Text 15', 'Definitive Agreement — Execution')
set_text(s, 'Text 16', 'Key terms, employee pool, earn-out detail; $1.0M EAI units awarded (target year-end 2026)')
set_text(s, 'Text 20', 'Closing — within 90 days of exclusivity')
set_text(s, 'Text 21', '① cash & debt relief paid; 5% escrow held 12 months (AAA §7)')
set_text(s, 'Text 27', 'Motions 1–3 are requested of the Board. Questions and open items welcome.')
set_notes(s, 'Sequence: (1) Board confirms §3 exclusivity, starting the 90-day window, and grants QB access; (2) diligence; '
             '(3) Definitive Agreement executed, $1.0M EAI units awarded (target year-end 2026); (4) closing within 90 days of '
             'exclusivity (AAA §6), extension not unreasonably withheld (§3); (5) targeted RTO ~6 months post-financing, not assured.')

# ---------- New slide: Clarifications (cloned from slide 9 layout) ----------
src = S[8]
new = p.slides.add_slide(src.slide_layout)
for ph in list(new.placeholders):
    ph._element.getparent().remove(ph._element)
new.background.fill.solid()
new.background.fill.fore_color.rgb = src.background.fill.fore_color.rgb
for sh in src.shapes:
    el = copy.deepcopy(sh._element)
    new.shapes._spTree.append(el)
    if sh.shape_type == 13:
        img_part = src.part.related_part(sh._element.blipFill.blip.rEmbed)
        rid = new.part.relate_to(img_part, RT.IMAGE)
        new.shapes[-1]._element.blipFill.blip.rEmbed = rid

H = 3749040  # taller panels
for n in ('Shape 2', 'Shape 5'):
    shp(new, n).height = H
for n in ('Text 4', 'Text 7'):
    shp(new, n).height = H - 520000
    shp(new, n).top = 1408176
for n in ('Text 3', 'Text 6'):
    shp(new, n).top = 1060704
shp(new, 'Text 0').top = 274320

set_text(new, 'Text 0', 'Clarifications to the Offer Summary')
set_text(new, 'Text 3', 'Money & Timing')
set_text(new, 'Text 6', 'Earn-Outs & Context')
left = [
    '• Debts: Exos pays every verified SSLC debt in full, at face, at closing, incl. Microcosm and Wertz (10/8). ~$500K is the QuickBooks estimate; final figure set in diligence.',
    '• $5.36M total = $2.51M cash + $60K costs + $790K stake credit (non-cash) + ~$500K debts + $500K WC bridge + $1.0M EAI units.',
    '• Exos stock: $1.0M EAI units awarded at execution, targeted by year-end 2026 (10/10 update; replaces "at financing close").',
    '• Closing: within 90 days of exclusivity (AAA §6), about mid-January 2027 if confirmed mid-October; extension not unreasonably withheld (§3).',
    '• Holdback: 5% escrow, released at the 12-month anniversary (AAA §7).',
    '• 5-yr High is $9.46M; the "$10.0M" in the 10/8 email was rounded up.',
]
right = [
    '• Tank earn-out: on Intuitive Machines tank revenue, FY27–FY31, cap $300K/yr; modeled 3% / 5% / 7% = $750K / $1.25M / $1.5M. Final rate set in the Definitive Agreement.',
    '• Stock earn-out: $625K / $1.5M are at listing value ($250M / $300M). At the 409A: $0 / $424K / $848K.',
    '• Key-employee option pool: set in the Definitive Agreement.',
    '• Balance-sheet context (slide 4) is from SSLC QuickBooks. The Microcosm facility-cost offset is illustrative (no written cost-sharing agreement); the $864K "billed-ahead" balance is under review.',
    "• Excluded assets per the May 2025 AAA: Microcosm's PRESSURMAXX/resin rights and LOXair's non-aerospace license.",
]
set_text(new, 'Text 4', '\n'.join(left))
set_text(new, 'Text 7', '\n'.join(right))
for n in ('Text 4', 'Text 7'):
    for para in shp(new, n).text_frame.paragraphs:
        para.space_after = Pt(5)
        for r in para.runs:
            r.font.size = Pt(10.5)
set_notes(new, 'Fills gaps in what the board received, using the executed May 2025 AAA, the 10/8 and 10/10 board emails, and SSLC '
               'QuickBooks. Nothing here adds a new Exos commitment.')

# move new slide (last) to just after slide 10 (index 10)
lst = p.slides._sldIdLst
el = lst[-1]
lst.remove(el)
lst.insert(10, el)

# footers: drop 'DRAFT' wording on every slide
for sl in p.slides:
    for sh in sl.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip() == 'DRAFT — NEGOTIATING TERMS':
            sh.text_frame.paragraphs[0].runs[0].text = FOOT

p.save(OUT)
print('saved', OUT)
