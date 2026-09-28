#!/usr/bin/env python3
"""Exos 'Report a Concern' breakroom poster (letter, print-friendly) — Handbook Sec. 2.5.

Companion to the official DoD Hotline poster (DFARS 252.203-7004). QR code -> MC report tool.
"""
import qrcode
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

WS = "/Users/exomac/.openclaw/workspace"
OUT = f"{WS}/process-library/05-human-resources/posters/Exos_Report_a_Concern_Poster_Letter.pdf"
LOGO = f"{WS}/drafts/_exos_black_official.png"
URL = "https://mc.exosaero.space/report.html"
ORANGE, GREY = HexColor("#F26A21"), HexColor("#4A4A4A")

W, H = letter
c = canvas.Canvas(OUT, pagesize=letter)
M = 50

logo = ImageReader(LOGO)
lw, lh = logo.getSize()
c.drawImage(logo, M, H - 40 - 60, width=60 * lw / lh, height=60, mask="auto")
c.setFillColor(ORANGE)
c.rect(M, H - 115, W - 2 * M, 5, stroke=0, fill=1)

c.setFillColor(black)
c.setFont("Helvetica-Bold", 40)
c.drawString(M, H - 170, "SEE SOMETHING WRONG?")
c.setFont("Helvetica-Bold", 30)
c.setFillColor(ORANGE)
c.drawString(M, H - 208, "REPORT IT. YOU ARE PROTECTED.")

c.setFillColor(GREY)
c.setFont("Helvetica", 13)
y = H - 245
for line in ["Fraud, false claims, or mischarging  •  Bribery, kickbacks, or conflicts of interest",
             "Waste or mismanagement of government funds  •  Falsified time, test, or inspection records",
             "Export control / CUI / security violations  •  Safety dangers  •  Retaliation"]:
    c.drawString(M, y, line); y -= 19

# internal channel box
y -= 12
c.setStrokeColor(black); c.setLineWidth(1.5)
c.rect(M, y - 175, W - 2 * M, 175, stroke=1, fill=0)
c.setFillColor(black); c.setFont("Helvetica-Bold", 17)
c.drawString(M + 16, y - 30, "INSIDE EXOS")
c.setFont("Helvetica", 12.5)
yy = y - 54
for line in ["• Any supervisor or manager, HR, or the CEO",
             "• Mission Control → 🛡 Report a Concern  (anonymous option)",
             "   mc.exosaero.space/report.html",
             "• You never have to report inside Exos first."]:
    c.drawString(M + 16, yy, line.replace("🛡 ", "")); yy -= 20
img = qrcode.make(URL, box_size=10, border=1).get_image()
c.drawImage(ImageReader(img), W - M - 16 - 130, y - 150, width=130, height=130)
c.setFont("Helvetica", 9); c.setFillColor(GREY)
c.drawCentredString(W - M - 16 - 65, y - 164, "Scan to report")

# external box
y = y - 190
c.setFillColor(black)
c.rect(M, y - 175, W - 2 * M, 175, stroke=0, fill=1)
c.setFillColor(white); c.setFont("Helvetica-Bold", 17)
c.drawString(M + 16, y - 30, "DIRECTLY TO THE GOVERNMENT")
c.setFont("Helvetica-Bold", 15); c.setFillColor(ORANGE)
c.drawString(M + 16, y - 60, "DoD Hotline: 1-800-424-9098   •   dodig.mil/hotline")
c.drawString(M + 16, y - 84, "NASA OIG Hotline: 1-800-424-9183   •   oig.nasa.gov/hotline")
c.setFillColor(white); c.setFont("Helvetica", 11.5)
yy = y - 108
for line in ["Also: a Member of Congress, GAO, the Contracting Officer, DOJ / law enforcement,",
             "the SEC, EEOC, OSHA, or NLRB. No notice to Exos is required.",
             "Government hotlines accept fully anonymous reports.",
             "Do not include CUI or export-controlled data except through an IG hotline."]:
    c.drawString(M + 16, yy, line); yy -= 17

c.setFillColor(black); c.setFont("Helvetica-Bold", 12)
c.drawString(M, 92, "Retaliation is prohibited by law and by Exos policy.")
c.setFont("Helvetica", 10); c.setFillColor(GREY)
c.drawString(M, 72, "10 U.S.C. § 4701  •  41 U.S.C. § 4712  •  File reprisal complaints with the agency IG within 3 years.")
c.drawString(M, 58, "Exos Employee Handbook, Section 2.5 — Whistleblower Protection & Reporting of Misconduct (Rev. 2026-09-28)")
c.setFillColor(ORANGE); c.rect(M, 44, W - 2 * M, 3, stroke=0, fill=1)
c.save()
print(OUT)
