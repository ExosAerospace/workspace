'use strict';
const pptxgen = require('pptxgenjs');
const path = require('path');
const { applyTheme } = require('/Users/exomac/.claude/skills/synced/e8583422-24a3-4d46-9183-3cf04d4ad99e_76085f6a-8320-4035-ad98-42f52f43a083/pptx/scripts/apply_theme.js');

const OUT = path.resolve(__dirname, '../drafts/Exos_SSLC_Board_Offer_Overview_2026-10-10.pptx');
const ASSETS = path.resolve(__dirname, '../drafts');

// Brand constants
const BLK  = '111111';
const DARK = '1A1A1A';
const ORG  = 'F26A21';
const WHT  = 'FFFFFF';
const GRY  = '888888';
const LGR  = 'CCCCCC';
const GRN  = '2ECC71';
const RED  = 'C0392B';

const THEME = {
  name: 'Exos Aerospace',
  headFontFace: 'Cambria',
  bodyFontFace: 'Calibri',
  colors: {
    dk1: '111111', lt1: 'FFFFFF', dk2: '1A1A1A', lt2: 'F5F5F5',
    accent1: 'F26A21', accent2: '888888', accent3: '2ECC71',
    accent4: 'C0392B', accent5: '555555', accent6: '333333',
    hlink: 'F26A21', folHlink: 'AAAAAA'
  }
};

const LOGO_W = path.join(ASSETS, '_exos_white_official.png');
const HERO_BG = path.join(ASSETS, '_exos_hero_bg.png');
const CHART_IMG = path.join(ASSETS, 'SSLC_OptionB_Total_Compensation_5yr_2026-10-07.png');

const pres = new pptxgen();
pres.layout = 'LAYOUT_16x9'; // 10" x 5.625"

// ---------- helper to add footer / logo to every dark slide ----------
function addFooterLogo(slide) {
  slide.addImage({ path: LOGO_W, x: 0.25, y: 5.2, w: 1.3, h: 0.28, isTextBox: false });
  slide.addText('DRAFT — NEGOTIATING TERMS', {
    x: 1.7, y: 5.25, w: 6.6, h: 0.25,
    fontSize: 7, color: GRY, italic: true, align: 'center', isTextBox: true
  });
  slide.addText('CONFIDENTIAL', {
    x: 8.5, y: 5.25, w: 1.25, h: 0.25,
    fontSize: 7, color: GRY, italic: true, align: 'right', isTextBox: true
  });
}

function darkBg(slide) {
  slide.background = { color: BLK };
}

// ============================================================
// SLIDE 1 — TITLE
// ============================================================
const s1 = pres.addSlide();
darkBg(s1);
s1.addImage({ path: HERO_BG, x: 0, y: 0, w: 10, h: 5.625, transparency: 30 });
// Orange top bar
s1.addShape(pres.ShapeType.rect, { x: 0, y: 0, w: 10, h: 0.06, fill: { color: ORG }, line: { type: 'none' } });
// Title
s1.addText('EXOS OFFER TO\nSCORPIUS SPACE LAUNCH COMPANY', {
  x: 0.6, y: 0.55, w: 8.8, h: 2.0,
  fontSize: 38, bold: true, color: WHT, fontFace: 'Cambria',
  align: 'center', valign: 'middle', isTextBox: true, margin: 0
});
// Subtitle
s1.addText('Board Overview', {
  x: 0.6, y: 2.45, w: 8.8, h: 0.55,
  fontSize: 22, bold: false, color: ORG, fontFace: 'Calibri',
  align: 'center', isTextBox: true
});
// Orange divider
s1.addShape(pres.ShapeType.rect, { x: 3.5, y: 3.1, w: 3.0, h: 0.04, fill: { color: ORG }, line: { type: 'none' } });
// Author / date
s1.addText('John M. Quinn  |  Cofounder & CEO, Exos Aerospace', {
  x: 0.6, y: 3.25, w: 8.8, h: 0.38,
  fontSize: 14, color: LGR, align: 'center', isTextBox: true
});
s1.addText('October 10, 2026', {
  x: 0.6, y: 3.62, w: 8.8, h: 0.3,
  fontSize: 13, color: GRY, align: 'center', isTextBox: true
});
s1.addText('CONFIDENTIAL — DRAFT — NEGOTIATING TERMS', {
  x: 0.6, y: 4.05, w: 8.8, h: 0.28,
  fontSize: 10, color: ORG, align: 'center', italic: true, isTextBox: true
});
s1.addImage({ path: LOGO_W, x: 4.1, y: 4.6, w: 1.8, h: 0.38 });
s1.addNotes('This is a draft offer overview for the SSLC board. All figures are from the Option B Offer Summary (2026-10-07). The offer is subject to negotiation and board acceptance. Not a final or binding offer.');

// ============================================================
// SLIDE 2 — THE DECISION
// ============================================================
const s2 = pres.addSlide();
darkBg(s2);
s2.addText('The Decision', {
  x: 0.5, y: 0.35, w: 9.0, h: 0.55,
  fontSize: 13, bold: true, color: ORG, fontFace: 'Calibri', isTextBox: true
});
s2.addText('The Board is asked to confirm §3 exclusivity under the May 2025 Asset Acquisition Agreement.', {
  x: 0.5, y: 1.05, w: 9.0, h: 1.8,
  fontSize: 34, bold: true, color: WHT, fontFace: 'Cambria',
  align: 'left', valign: 'top', isTextBox: true
});
// Details box
s2.addShape(pres.ShapeType.rect, { x: 0.5, y: 3.1, w: 9.0, h: 1.8, fill: { color: '1E1E1E' }, line: { color: '333333', pt: 1 } });
s2.addText([
  { text: 'Exclusivity period: ', options: { bold: true, color: ORG } },
  { text: '90 days from board confirmation; extension not unreasonably withheld (§3)\n', options: { color: LGR } },
  { text: 'Holdback: ', options: { bold: true, color: ORG } },
  { text: '5% escrow, released at 12-month anniversary (§7)\n', options: { color: LGR } },
  { text: 'Agreement basis: ', options: { bold: true, color: ORG } },
  { text: 'May 2025 Asset Acquisition Agreement — §3 exclusivity trigger', options: { color: LGR } },
], {
  x: 0.7, y: 3.2, w: 8.6, h: 1.6,
  fontSize: 14, isTextBox: true, valign: 'top'
});
addFooterLogo(s2);
s2.addNotes('The sole action requested of the SSLC board at this meeting is confirmation of the §3 exclusivity provision in the existing May 2025 Asset Acquisition Agreement. Once exclusivity is confirmed, both parties have 90 days to negotiate and execute the definitive agreement and advance to financing close.');

// ============================================================
// SLIDE 3 — WHERE SSLC STANDS
// ============================================================
const s3 = pres.addSlide();
darkBg(s3);
s3.addText('Where SSLC Stands Today', {
  x: 0.5, y: 0.35, w: 9.0, h: 0.52,
  fontSize: 22, bold: true, color: WHT, fontFace: 'Cambria', isTextBox: true
});
s3.addShape(pres.ShapeType.rect, { x: 0.5, y: 0.88, w: 1.5, h: 0.04, fill: { color: ORG }, line: { type: 'none' } });

// Three stat boxes
const stats = [
  { val: '$198K', label: 'Cash on hand', sub: 'Current working capital' },
  { val: '$713K', label: 'Last quarter revenue', sub: 'Most recent reported quarter' },
  { val: '~$1.46M/qtr', label: 'Required to hit $5.1M', sub: 'M1 milestone threshold' },
];
stats.forEach((s, i) => {
  const x = 0.4 + i * 3.1;
  s3.addShape(pres.ShapeType.rect, { x, y: 1.2, w: 2.8, h: 2.2, fill: { color: '1E1E1E' }, line: { color: '333333', pt: 1 } });
  s3.addText(s.val, {
    x: x + 0.1, y: 1.35, w: 2.6, h: 0.95,
    fontSize: i === 2 ? 26 : 34, bold: true, color: i === 2 ? ORG : WHT, align: 'center', isTextBox: true
  });
  s3.addText(s.label, {
    x: x + 0.1, y: 2.3, w: 2.6, h: 0.45,
    fontSize: 13, bold: true, color: LGR, align: 'center', isTextBox: true
  });
  s3.addText(s.sub, {
    x: x + 0.1, y: 2.75, w: 2.6, h: 0.45,
    fontSize: 11, color: GRY, align: 'center', isTextBox: true
  });
});

s3.addShape(pres.ShapeType.rect, { x: 0.5, y: 3.65, w: 9.0, h: 1.15, fill: { color: '1A1200' }, line: { color: ORG, pt: 1 } });
s3.addText('A $5.1M fiscal year requires approximately $1.46M per quarter — nearly double last quarter\'s pace of $713K — starting now. Exos\'s offer removes that funding risk and gives SSLC holders direct upside.', {
  x: 0.7, y: 3.75, w: 8.6, h: 0.95,
  fontSize: 13, color: LGR, italic: true, align: 'left', valign: 'middle', isTextBox: true
});
addFooterLogo(s3);
s3.addNotes('These are SSLC\'s own numbers, presented factually and respectfully. The $198K cash figure is from the email draft. The $713K last quarter is from the offer summary. The $5.1M milestone (M1) requires nearly double that quarterly pace starting immediately — this is the context for why the Exos offer provides meaningful value through financing close and earn-out structure.');

// ============================================================
// SLIDE 4 — WHAT SSLC HOLDERS RECEIVE AT CLOSE
// ============================================================
const s4 = pres.addSlide();
darkBg(s4);
s4.addText('What SSLC Holders Receive', {
  x: 0.5, y: 0.35, w: 9.0, h: 0.52,
  fontSize: 22, bold: true, color: WHT, fontFace: 'Cambria', isTextBox: true
});
s4.addShape(pres.ShapeType.rect, { x: 0.5, y: 0.88, w: 1.5, h: 0.04, fill: { color: ORG }, line: { type: 'none' } });

// Waterfall blocks
const wfItems = [
  { label: 'Cash at close', val: '$2.51M', color: '2A2A2A' },
  { label: 'SSLC transaction costs', val: '$60K', color: '222222' },
  { label: 'Exos stake credit (non-cash)', val: '$790K', color: '222222' },
  { label: 'SSLC debts paid at face', val: '~$500K', color: '222222' },
  { label: 'Working-capital bridge', val: '$500K', color: '222222' },
];

let yPos = 1.1;
const itemH = 0.46;
wfItems.forEach((item) => {
  s4.addShape(pres.ShapeType.rect, { x: 1.0, y: yPos, w: 6.2, h: itemH - 0.03, fill: { color: item.color }, line: { color: '333333', pt: 1 } });
  s4.addText(item.label, { x: 1.1, y: yPos + 0.04, w: 4.0, h: itemH - 0.08, fontSize: 13, color: LGR, valign: 'middle', isTextBox: true });
  s4.addText(item.val, { x: 6.0, y: yPos + 0.04, w: 1.1, h: itemH - 0.08, fontSize: 13, color: WHT, bold: true, align: 'right', valign: 'middle', isTextBox: true });
  yPos += itemH;
});
// Subtotal ①
s4.addShape(pres.ShapeType.rect, { x: 0.8, y: yPos + 0.04, w: 6.6, h: 0.52, fill: { color: '2A1800' }, line: { color: ORG, pt: 1.5 } });
s4.addText('① Cash & debt relief at close', { x: 0.95, y: yPos + 0.1, w: 4.2, h: 0.4, fontSize: 15, bold: true, color: ORG, valign: 'middle', isTextBox: true });
s4.addText('$4.36M', { x: 5.9, y: yPos + 0.1, w: 1.3, h: 0.4, fontSize: 18, bold: true, color: ORG, align: 'right', valign: 'middle', isTextBox: true });
yPos += 0.62;

// Plus equity
s4.addShape(pres.ShapeType.rect, { x: 1.0, y: yPos, w: 6.2, h: 0.44, fill: { color: '202020' }, line: { color: '444444', pt: 1 } });
s4.addText('+ Exos equity — EAI units at 409A (Rule 504, ~0.59%)', { x: 1.1, y: yPos + 0.04, w: 4.2, h: 0.36, fontSize: 13, color: LGR, valign: 'middle', isTextBox: true });
s4.addText('$1.0M', { x: 6.0, y: yPos + 0.04, w: 1.1, h: 0.36, fontSize: 14, bold: true, color: WHT, align: 'right', valign: 'middle', isTextBox: true });
yPos += 0.52;

// Total ②
s4.addShape(pres.ShapeType.rect, { x: 0.8, y: yPos, w: 6.6, h: 0.58, fill: { color: '0A2800' }, line: { color: '2ECC71', pt: 2 } });
s4.addText('② Total at financing close', { x: 0.95, y: yPos + 0.09, w: 4.2, h: 0.4, fontSize: 16, bold: true, color: GRN, valign: 'middle', isTextBox: true });
s4.addText('$5.36M', { x: 5.8, y: yPos + 0.09, w: 1.4, h: 0.4, fontSize: 20, bold: true, color: GRN, align: 'right', valign: 'middle', isTextBox: true });

// Right-side note
s4.addText('Issued at financing close\nRestricted at issuance (Rule 504)\nPart of RTO public float\nFreely tradeable at listing', {
  x: 7.55, y: 1.15, w: 2.2, h: 3.8,
  fontSize: 11, color: GRY, isTextBox: true, valign: 'top'
});
addFooterLogo(s4);
s4.addNotes('All three scenarios (Low/Base/High) have identical at-close values: ① $4.36M, ② $5.36M with stock. The $4.36M breaks down as: $2.51M cash + $60K transaction costs + $790K stake credit (non-cash) + ~$500K SSLC debts at face + $500K WC bridge. The $1.0M EAI units are issued at financing close, not at board acceptance, and count toward the Rule 504 $10M rolling cap.');

// ============================================================
// SLIDE 5 — EARN-OUTS & MILESTONES
// ============================================================
const s5 = pres.addSlide();
darkBg(s5);
s5.addText('How Value Grows: Earn-Outs & Milestones', {
  x: 0.5, y: 0.3, w: 9.0, h: 0.5,
  fontSize: 22, bold: true, color: WHT, fontFace: 'Cambria', isTextBox: true
});
s5.addShape(pres.ShapeType.rect, { x: 0.5, y: 0.82, w: 1.5, h: 0.04, fill: { color: ORG }, line: { type: 'none' } });

// Table header
const colX = [0.35, 4.0, 5.75, 7.35];
const colW = [3.55, 1.6, 1.55, 2.3];
const hdrs = ['Earn-Out', 'Low', 'Base', 'High'];
hdrs.forEach((h, i) => {
  s5.addShape(pres.ShapeType.rect, { x: colX[i], y: 1.0, w: colW[i], h: 0.38, fill: { color: '2A1000' }, line: { color: ORG, pt: 1 } });
  s5.addText(h, { x: colX[i] + 0.05, y: 1.03, w: colW[i] - 0.1, h: 0.3, fontSize: 12, bold: true, color: ORG, align: i === 0 ? 'left' : 'center', isTextBox: true });
});

const rows = [
  { label: 'Tank earn-out (5 yrs, IM revenue)', low: '$750K', base: '$1,250K', high: '$1,500K' },
  { label: 'M1: FY2026-27 revenue ≥ $5.1M', low: '$200K', base: '$200K', high: '$200K' },
  { label: 'M2: Nebula/OTV production contract signed', low: '—', base: '$200K', high: '$200K' },
  { label: 'M3: SSLC annual revenue ≥ $10M', low: '—', base: '$250K', high: '$250K' },
  { label: 'M4: SSLC annual revenue ≥ $20M', low: '—', base: '—', high: '$250K' },
  { label: 'M5: BLK3 tank qualification complete', low: '—', base: '—', high: '$200K' },
  { label: 'Stock earn-out at listing (additional equity)', low: '$0\n(0.0%)', base: '$625K\n(0.25%)', high: '$1,500K\n(0.50%)' },
];

rows.forEach((row, ri) => {
  const y = 1.43 + ri * 0.46;
  const bg = ri % 2 === 0 ? '1C1C1C' : '222222';
  colX.forEach((cx, ci) => {
    const txt = ci === 0 ? row.label : (ci === 1 ? row.low : ci === 2 ? row.base : row.high);
    const clr = txt === '—' ? GRY : ci > 0 ? (txt.includes('$0') ? GRY : WHT) : LGR;
    s5.addShape(pres.ShapeType.rect, { x: cx, y, w: colW[ci], h: 0.43, fill: { color: bg }, line: { color: '2A2A2A', pt: 1 } });
    s5.addText(txt, { x: cx + 0.07, y: y + 0.03, w: colW[ci] - 0.1, h: 0.37, fontSize: ci === 0 ? 11 : 12, color: clr, align: ci === 0 ? 'left' : 'center', valign: 'middle', isTextBox: true });
  });
});

// Quote
s5.addShape(pres.ShapeType.rect, { x: 0.35, y: 4.67, w: 9.3, h: 0.72, fill: { color: '150B00' }, line: { color: ORG, pt: 1 } });
s5.addText('"The up-front price reflects what the numbers support today; the earn-outs are how that value grows as goals are met."  — John M. Quinn', {
  x: 0.5, y: 4.73, w: 9.0, h: 0.6,
  fontSize: 12, color: LGR, italic: true, align: 'center', valign: 'middle', isTextBox: true
});
addFooterLogo(s5);
s5.addNotes('Tank earn-out: 5 years, 3%/5%/7% of IM revenue (Low/Base/High), $300K/yr cap. M1 pays FY28 Q1 if verified. M2 pays at contract execution any year FY27-30. M3 pays first year threshold hit (est. FY29 at base/high). M4 pays first year threshold hit (est. FY31 at high). M5 pays at Exos BLK3 tank certification (est. FY27-28). Stock earn-out: 0.0%/0.25%/0.50% additional FD equity at RTO, with the same lockup as Exos principals. Each milestone is independently verifiable; none pays unless the trigger is met.');

// ============================================================
// SLIDE 6 — TOTAL VALUE
// ============================================================
const s6 = pres.addSlide();
darkBg(s6);
s6.addText('Total Offer Value', {
  x: 0.5, y: 0.3, w: 9.0, h: 0.5,
  fontSize: 22, bold: true, color: WHT, fontFace: 'Cambria', isTextBox: true
});
s6.addShape(pres.ShapeType.rect, { x: 0.5, y: 0.82, w: 1.5, h: 0.04, fill: { color: ORG }, line: { type: 'none' } });

// ③ Total 5-yr boxes
const scenarios = [
  { label: 'Low', v3: '$6.3M', v4: '$12.0M' },
  { label: 'Base', v3: '$7.9M', v4: '$15.8M' },
  { label: 'High', v3: '$9.5M', v4: '$19.4M' },
];

s6.addText('③  5-Year Total (earn-outs realized)', {
  x: 0.5, y: 1.0, w: 4.8, h: 0.35,
  fontSize: 13, bold: true, color: GRN, isTextBox: true
});

scenarios.forEach((sc, i) => {
  const x = 0.5 + i * 1.55;
  s6.addShape(pres.ShapeType.rect, { x, y: 1.38, w: 1.45, h: 1.35, fill: { color: '0A2800' }, line: { color: '2ECC71', pt: 1.5 } });
  s6.addText(sc.label, { x, y: 1.42, w: 1.45, h: 0.32, fontSize: 12, color: GRN, bold: true, align: 'center', isTextBox: true });
  s6.addText(sc.v3, { x, y: 1.73, w: 1.45, h: 0.65, fontSize: 26, bold: true, color: GRN, align: 'center', isTextBox: true });
  s6.addShape(pres.ShapeType.rect, { x: x + 0.1, y: 2.38, w: 1.25, h: 0.28, fill: { color: '143000' }, line: { type: 'none' } });
  s6.addText('5-yr realized', { x, y: 2.4, w: 1.45, h: 0.24, fontSize: 9, color: GRY, align: 'center', isTextBox: true });
});

// Divider
s6.addShape(pres.ShapeType.line, { x: 5.15, y: 1.0, w: 0, h: 3.6, line: { color: '333333', pt: 1 } });

// ④ If-held
s6.addText('④  If Exos Stock Held to 2031  (projection)', {
  x: 5.35, y: 1.0, w: 4.4, h: 0.35,
  fontSize: 13, bold: true, color: ORG, isTextBox: true
});
scenarios.forEach((sc, i) => {
  const x = 5.35 + i * 1.52;
  s6.addShape(pres.ShapeType.rect, { x, y: 1.38, w: 1.44, h: 1.35, fill: { color: '1A0A00' }, line: { color: ORG, pt: 1.5 } });
  s6.addText(sc.label, { x, y: 1.42, w: 1.44, h: 0.32, fontSize: 12, color: ORG, bold: true, align: 'center', isTextBox: true });
  s6.addText(sc.v4, { x, y: 1.73, w: 1.44, h: 0.65, fontSize: 22, bold: true, color: ORG, align: 'center', isTextBox: true });
  s6.addShape(pres.ShapeType.rect, { x: x + 0.07, y: 2.38, w: 1.3, h: 0.28, fill: { color: '2A1000' }, line: { type: 'none' } });
  s6.addText('if held to 2031', { x, y: 2.4, w: 1.44, h: 0.24, fontSize: 9, color: GRY, align: 'center', isTextBox: true });
});

// Chart
s6.addImage({ path: CHART_IMG, x: 0.35, y: 2.85, w: 9.3, h: 2.4 });

// Disclaimer
// (Already covered by chart itself mostly, but add a note)
s6.addShape(pres.ShapeType.rect, { x: 0.35, y: 2.78, w: 9.3, h: 0.16, fill: { color: '222200' }, line: { type: 'none' } });
s6.addText('④ is a forward-looking projection, not a guarantee; an alternative to ③ — not added to it. RTO may not close.', {
  x: 0.4, y: 2.79, w: 9.2, h: 0.13,
  fontSize: 8, color: GRY, italic: true, isTextBox: true
});
addFooterLogo(s6);
s6.addNotes('③ 5-yr total is ② ($5.36M) + earn-outs. Low = $6.31M / Base = $7.885M (shown as $7.9M) / High = $9.46M (shown as $9.5M). These are rounded for board presentation. ④ TOTAL IF STOCK HELD TO 2031: Low $12.0M / Base $15.8M / High $19.4M — this replaces and is not additive to ③. It assumes RTO completion, ~30% dilution, and management-projected valuations. Forward-looking statements subject to SEC Rule 10b-5. The chart shows the year-by-year compensation build from close through FY31.');

// ============================================================
// SLIDE 7 — THE EXOS STOCK
// ============================================================
const s7 = pres.addSlide();
darkBg(s7);
s7.addText('The Exos Stock', {
  x: 0.5, y: 0.3, w: 9.0, h: 0.52,
  fontSize: 22, bold: true, color: WHT, fontFace: 'Cambria', isTextBox: true
});
s7.addShape(pres.ShapeType.rect, { x: 0.5, y: 0.84, w: 1.5, h: 0.04, fill: { color: ORG }, line: { type: 'none' } });

const stockItems = [
  { title: 'Instrument', body: '$1.0M EAI units at the current 409A valuation (~$169.7M); ~0.59% fully diluted at issuance.' },
  { title: 'Offering', body: 'Part of Exos\'s Rule 504 Regulation D offering. U.S. persons only. Counts toward the $10M rolling 12-month cap.' },
  { title: 'Restricted at issuance', body: 'Units carry a restrictive legend at issuance (Rule 504 Reg D). Not freely tradeable prior to the RTO listing.' },
  { title: 'Public float at RTO', body: 'Structured to be part of the public float at going public. No principals\' lockup applies to these units; locked-up shares would not count as float.' },
  { title: 'Freely tradeable at listing', body: 'Becomes freely tradeable at the RTO listing (no lockup on the up-front units). Covered by the RTO resale registration.' },
  { title: 'Timeline', body: 'Units issued at financing close. Targeted RTO ~6 months post-financing. Not assured — RTO may not close.' },
];

stockItems.forEach((item, i) => {
  const row = Math.floor(i / 2);
  const col = i % 2;
  const x = 0.4 + col * 4.7;
  const y = 1.05 + row * 1.4;
  s7.addShape(pres.ShapeType.rect, { x, y, w: 4.4, h: 1.28, fill: { color: '1C1C1C' }, line: { color: '333333', pt: 1 } });
  s7.addText(item.title, { x: x + 0.15, y: y + 0.08, w: 4.1, h: 0.32, fontSize: 13, bold: true, color: ORG, isTextBox: true });
  s7.addText(item.body, { x: x + 0.15, y: y + 0.38, w: 4.1, h: 0.82, fontSize: 12, color: LGR, isTextBox: true });
});
addFooterLogo(s7);
s7.addNotes('The $1.0M EAI units are issued at financing close (not at board acceptance). At the 409A valuation of ~$169.7M, this represents ~0.59% fully diluted. Earn-out stock (0.0%/0.25%/0.50% additional) issued post-RTO brings total equity to ~0.59%–1.09%. The Japan round EAI units are Reg S and must remain separate from the Rule 504 domestic offering. See model EAI Lockup & Liquidity sheet for full detail.');

// ============================================================
// SLIDE 8 — SSLC PEOPLE
// ============================================================
const s8 = pres.addSlide();
darkBg(s8);
s8.addText('SSLC Employees', {
  x: 0.5, y: 0.3, w: 9.0, h: 0.52,
  fontSize: 22, bold: true, color: WHT, fontFace: 'Cambria', isTextBox: true
});
s8.addShape(pres.ShapeType.rect, { x: 0.5, y: 0.84, w: 1.5, h: 0.04, fill: { color: ORG }, line: { type: 'none' } });

// Two big blocks
s8.addShape(pres.ShapeType.rect, { x: 0.4, y: 1.1, w: 4.5, h: 3.0, fill: { color: '1C1C1C' }, line: { color: '333333', pt: 1 } });
s8.addText('Employment Offer', { x: 0.55, y: 1.18, w: 4.2, h: 0.4, fontSize: 16, bold: true, color: ORG, isTextBox: true });
s8.addText('Exos shall offer employment to SSLC employees — including management, support, engineering, and other technical and manufacturing employees — on terms no less favorable than their current terms with SSLC, including compensation and benefits.\n\nSubject to each employee satisfying Exos\'s standard hiring policies and Exos\'s completion of confirmatory due diligence.', {
  x: 0.55, y: 1.62, w: 4.2, h: 2.35,
  fontSize: 13, color: LGR, isTextBox: true, valign: 'top'
});

s8.addShape(pres.ShapeType.rect, { x: 5.1, y: 1.1, w: 4.5, h: 3.0, fill: { color: '1C1C1C' }, line: { color: '333333', pt: 1 } });
s8.addText('Key-Employee Option Pool', { x: 5.25, y: 1.18, w: 4.2, h: 0.4, fontSize: 16, bold: true, color: ORG, isTextBox: true });
s8.addText('Exos will establish an option pool for key SSLC employees. The size and structure will be mutually agreed in the Definitive Agreement.\n\nDesigned to retain the talent that drives SSLC\'s mission continuity and milestones — including the programs that underpin the earn-out triggers.', {
  x: 5.25, y: 1.62, w: 4.2, h: 2.35,
  fontSize: 13, color: LGR, isTextBox: true, valign: 'top'
});
addFooterLogo(s8);
s8.addNotes('This language is verbatim from the offer email (Exos_SSLC_Offer_Briefing_Email_DRAFT_2026-10-09.docx) and the Key Terms section of the offer summary PDF. The exact terms — option pool size, vesting schedule — will be negotiated in the Definitive Agreement. IM program continuity: Exos-SSLC continues the Intuitive Machines contract with no delivery interruption.');

// ============================================================
// SLIDE 9 — NEXT STEPS
// ============================================================
const s9 = pres.addSlide();
darkBg(s9);
s9.addImage({ path: HERO_BG, x: 0, y: 0, w: 10, h: 5.625, transparency: 45 });
s9.addText('Path to Close', {
  x: 0.5, y: 0.3, w: 9.0, h: 0.52,
  fontSize: 22, bold: true, color: WHT, fontFace: 'Cambria', isTextBox: true
});
s9.addShape(pres.ShapeType.rect, { x: 0.5, y: 0.84, w: 1.5, h: 0.04, fill: { color: ORG }, line: { type: 'none' } });

const steps = [
  { num: '1', title: 'Board Confirms Exclusivity', sub: 'Today — action requested at this meeting' },
  { num: '2', title: '90-Day Exclusivity Window', sub: 'Negotiation and diligence period begins' },
  { num: '3', title: 'Definitive Agreement', sub: 'Key terms, employee pool, earn-out detail finalized' },
  { num: '4', title: 'Financing Close', sub: 'Cash at close + EAI units issued; ① + stock = ②' },
  { num: '5', title: 'Targeted RTO', sub: '~6 months post-financing; units tradeable at listing (not assured)' },
];

steps.forEach((step, i) => {
  const y = 1.0 + i * 0.76;
  // Connector line (except last)
  if (i < steps.length - 1) {
    s9.addShape(pres.ShapeType.line, { x: 1.12, y: y + 0.56, w: 0, h: 0.22, line: { color: ORG, pt: 1.5 } });
  }
  // Circle
  s9.addShape(pres.ShapeType.ellipse, { x: 0.6, y, w: 0.56, h: 0.56, fill: { color: i === 0 ? ORG : '2A2A2A' }, line: { color: ORG, pt: 1.5 } });
  s9.addText(step.num, { x: 0.6, y: y + 0.07, w: 0.56, h: 0.42, fontSize: 15, bold: true, color: i === 0 ? BLK : ORG, align: 'center', isTextBox: true });
  // Title
  s9.addText(step.title, { x: 1.35, y: y + 0.02, w: 7.5, h: 0.3, fontSize: 14, bold: true, color: WHT, isTextBox: true });
  // Sub
  s9.addText(step.sub, { x: 1.35, y: y + 0.31, w: 7.5, h: 0.26, fontSize: 11, color: GRY, isTextBox: true });
});

// Ask
s9.addShape(pres.ShapeType.rect, { x: 0.4, y: 4.82, w: 9.2, h: 0.44, fill: { color: '2A1000' }, line: { color: ORG, pt: 1.5 } });
s9.addText('The Board is asked to confirm §3 exclusivity. Questions and open items welcome.', {
  x: 0.55, y: 4.86, w: 9.0, h: 0.36,
  fontSize: 13, bold: true, color: ORG, align: 'center', valign: 'middle', isTextBox: true
});
s9.addNotes('The one action needed today is board confirmation of §3 exclusivity in the May 2025 Asset Acquisition Agreement. Once confirmed, the 90-day exclusivity period begins and both teams can proceed to diligence and the definitive agreement. The financing close triggers ② ($5.36M). The RTO is targeted ~6 months post-financing close but is not assured. All earn-out and milestone payments are independent and verifiable.');

// ============================================================
// WRITE FILE
// ============================================================
(async () => {
  await pres.writeFile({ fileName: OUT });
  console.log('Written:', OUT);
  await applyTheme(OUT, THEME);
  console.log('Theme applied.');
})();
