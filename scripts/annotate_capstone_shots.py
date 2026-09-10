#!/usr/bin/env python3
"""Annotate the UTD capstone student-view screenshots with numbered callouts,
a title banner, and a plain-English key strip. One-off deliverable for Lizi/John.
Reads drafts/capstone_shots/*.png -> writes drafts/capstone_shots/annotated/*.png
Coordinates are in ORIGINAL (full-res) pixels."""
from PIL import Image, ImageDraw, ImageFont
import os

SRC = "drafts/capstone_shots"
OUT = os.path.join(SRC, "annotated")
os.makedirs(OUT, exist_ok=True)

FB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FR = "/System/Library/Fonts/Supplemental/Arial.ttf"

NAVY = (10, 26, 47)
BLUE = (37, 99, 235)
WHITE = (255, 255, 255)
LGRAY = (176, 196, 222)
INK = (17, 24, 39)

def font(path, size):
    return ImageFont.truetype(path, size)

def wrap(draw, text, fnt, maxw):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def draw_pin(draw, x, y, num, r, nfnt):
    # white halo ring for contrast on any background
    draw.ellipse([x - r - 5, y - r - 5, x + r + 5, y + r + 5], fill=WHITE)
    draw.ellipse([x - r, y - r, x + r, y + r], fill=BLUE, outline=WHITE, width=max(2, r // 10))
    s = str(num)
    tw = draw.textlength(s, font=nfnt)
    bb = draw.textbbox((0, 0), s, font=nfnt)
    th = bb[3] - bb[1]
    draw.text((x - tw / 2, y - th / 2 - bb[1]), s, font=nfnt, fill=WHITE)

def annotate(fname, title, subtitle, pins, keys):
    """pins: list of (num, x, y). keys: list of (num, short, long)."""
    img = Image.open(os.path.join(SRC, fname)).convert("RGB")
    W, H = img.size
    scale = W / 2640.0
    # sizing with floors so the small login shot stays legible
    t_size = max(int(60 * scale), 30)
    s_size = max(int(38 * scale), 20)
    k_size = max(int(34 * scale), 20)
    pin_r = max(int(38 * scale), 20)
    n_size = max(int(42 * scale), 22)
    pad = max(int(40 * scale), 20)

    ftitle, fsub, fkey, fkeyb, fnum = (font(FB, t_size), font(FR, s_size),
                                       font(FR, k_size), font(FB, k_size), font(FB, n_size))

    # banner text wraps to image width; tag sits on its own line so it never collides
    tmp0 = ImageDraw.Draw(img)
    tag = "Exos × UTD EXO3 Payload Capstone · Student View"
    sub_lines = wrap(tmp0, subtitle, fsub, W - pad * 2)
    s_line_h = int(s_size * 1.28)
    top_h = pad * 2 + t_size + int(8 * scale) + len(sub_lines) * s_line_h + s_line_h

    # measure key strip height
    tmp = ImageDraw.Draw(img)
    line_h = int(k_size * 1.35)
    keyw = W - pad * 2
    num_col = max(int(70 * scale), 44)
    entries = []
    for num, short, lng in keys:
        text = f"{short} — {lng}" if lng else short
        lines = wrap(tmp, text, fkey, keyw - num_col)
        entries.append((num, lines))
    key_body = sum(len(ls) * line_h + int(14 * scale) for _, ls in entries)
    bot_h = pad * 2 + int(k_size * 1.4) + key_body

    canvas = Image.new("RGB", (W, top_h + H + bot_h), NAVY)
    canvas.paste(img, (0, top_h))
    d = ImageDraw.Draw(canvas)

    # top banner
    d.text((pad, pad), title, font=ftitle, fill=WHITE)
    yb = pad + t_size + int(8 * scale)
    for ln in sub_lines:
        d.text((pad, yb), ln, font=fsub, fill=LGRAY)
        yb += s_line_h
    d.text((pad, yb), tag, font=fsub, fill=BLUE)
    d.line([(0, top_h - 1), (W, top_h - 1)], fill=BLUE, width=max(3, int(4 * scale)))

    # pins on the screenshot region (offset y by top_h)
    for num, x, y in pins:
        draw_pin(d, int(x), int(y) + top_h, num, pin_r, fnum)

    # bottom key panel
    ky = top_h + H
    d.rectangle([0, ky, W, ky + bot_h], fill=(248, 250, 252))
    d.line([(0, ky), (W, ky)], fill=BLUE, width=max(3, int(4 * scale)))
    yy = ky + pad
    d.text((pad, yy), "WHAT YOU'RE LOOKING AT", font=fkeyb, fill=BLUE)
    yy += int(k_size * 1.5)
    for num, lines in entries:
        # mini numbered chip
        cr = int(k_size * 0.62)
        cx, cy = pad + cr, yy + cr
        d.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=BLUE)
        ns = str(num)
        d.text((cx - d.textlength(ns, font=fkeyb) / 2, cy - k_size * 0.62 + int(2 * scale)),
               ns, font=fkeyb, fill=WHITE)
        tx = pad + num_col
        for i, ln in enumerate(lines):
            d.text((tx, yy + i * line_h), ln, font=(fkeyb if i == 0 and "—" not in ln else fkey), fill=INK)
        yy += len(lines) * line_h + int(14 * scale)

    outp = os.path.join(OUT, fname.replace(".png", "_annotated.png"))
    canvas.save(outp)
    print("wrote", outp, canvas.size)

# ---------------- SCREEN 1: LOGIN (896x800) ----------------
annotate(
    "1_login.png",
    "Screen 1 — Signing In",
    "Two gates get you to your board: Cloudflare Access (UTD email + code), then your Mission Control login.",
    pins=[(1, 448, 358), (2, 448, 513), (3, 448, 629)],
    keys=[
        (1, "Email", "First a Cloudflare Access page asks for your @utdallas.edu email and emails you a one-time code. Then this screen: enter that same email."),
        (2, "Password", "Enter the Exos-provided Mission Control password. It's temporary on first login — you'll be prompted to set your own."),
        (3, "Sign In", "Opens your board, scoped to Payload Sales only. Nothing else in Mission Control is visible to you."),
    ],
)

# ---------------- SCREEN 2: TASK BOARD (2640x3300) ----------------
annotate(
    "2_taskboard.png",
    "Screen 2 — Your Task Board",
    "The live Kanban board — the day-to-day work surface, scoped to Payload Sales.",
    pins=[(1, 1473, 63), (2, 1240, 63), (3, 292, 215), (4, 1000, 363),
          (5, 2470, 561), (6, 150, 710), (7, 300, 960)],
    keys=[
        (1, "EARLY ADOPTER", "Your role badge. It scopes your access — you see and manage Payload Sales tasks only."),
        (2, "Welcome Guide", "Reopens the onboarding guide (Screen 3) any time."),
        (3, "Live counters", "Total / To Do / In Progress / Done / Overdue across your project, updated live."),
        (4, "Filter & search", "Filter by owner, status, project, or keyword; sort by Mission Score or due date."),
        (5, "+ Add", "Type a task title and hit Add (or Enter) to create a new task in your project."),
        (6, "Three columns", "Work flows left to right: To Do → In Progress → Done. Drag cards or use the quick buttons."),
        (7, "Quick-move buttons", "One-click In Progress / Done on each card. The purple 'Payload Sales' tag confirms scope."),
    ],
)

# ---------------- SCREEN 3: WELCOME GUIDE (2640x4886) ----------------
annotate(
    "3_welcome.png",
    "Screen 3 — Welcome Guide",
    "The first thing you land on: what you can do, the guardrails, and how to command Exo with @Exobot.",
    pins=[(1, 881, 834), (2, 830, 1174), (3, 869, 1749),
          (4, 815, 2447), (5, 952, 3133), (6, 844, 4045), (7, 1315, 4560)],
    keys=[
        (1, "Your Account", "Confirms your Role (Early Adopter) and Project scope (Payload Sales)."),
        (2, "What You Can Do", "View, create, and update tasks; post notes; filter and search — all inside Payload Sales."),
        (3, "Usage Guidelines", "The guardrails: Payload Sales only; no deletes; confidential preview; don't share credentials or screenshots externally."),
        (4, "Getting Started", "Five steps from opening the board to creating and moving your first task."),
        (5, "Commanding Exo with @Exobot", "In any task's note box, type @Exobot + a plain-English request; Exo acts within ~2 min and posts a confirmation. Click the ? for the command list."),
        (6, "Good to Know", "End a note with a question mark and Exo auto-answers it on the task (no @Exobot needed); a plain statement just logs. Anything external or sensitive is drafted and held for approval — never sent automatically."),
        (7, "Go to Mission Control", "The button that takes you into the live task board (Screen 2)."),
    ],
)

# ---------------- SCREEN 4a: TRACKER — FUNNEL (2640x1650) ----------------
annotate(
    "4a_tracker_funnel.png",
    "Screen 4a — Capstone Tracker: Goal & Funnel",
    "Your daily starting point. The mission up top, then your three-stage sales funnel with live counts.",
    pins=[(1, 436, 73), (2, 640, 772), (3, 1181, 766), (4, 455, 1214), (5, 1848, 1214)],
    keys=[
        (1, "← Mission Control", "Jumps back to your task board (Screen 2)."),
        (2, "Bay capacity", "The prize: 135 kg of open payload mass to fill on BLK3 Flight 2."),
        (3, "Launch-reward gate", "Team progress toward the 100 kg booked gate that unlocks the launch trip."),
        (4, "NEW → RESEARCHING → READY", "Your funnel with live counts. Your job is to push leads to the right."),
        (5, "READY", "A lead is READY when the POC is found AND a draft is written — then it hands off to Lizi to review and send."),
    ],
)

# ---------------- SCREEN 4b: TRACKER — WORK QUEUE (2640x3100) ----------------
annotate(
    "4b_tracker_queue.png",
    "Screen 4b — Capstone Tracker: Prioritized Work Queue",
    "Your ranked to-do list of leads. Work it by rank — it's already sorted best-first.",
    pins=[(1, 574, 171), (2, 2248, 369), (3, 837, 411), (4, 775, 453), (5, 1628, 364)],
    keys=[
        (1, "Prioritized Work Queue", "Work by RANK, not alphabetically. Already sorted best-first — don't re-sort it."),
        (2, "Priority score", "0–100 opportunity quality = funding signal + named POC + leverage. Higher = work it first."),
        (3, "Why it's ranked here", "The one-line rationale for the lead's position, so you know what makes it strong."),
        (4, "Next action", "Exactly what to do next: find the POC, research funding/programs, or prepare the draft."),
        (5, "Current stage", "Where the lead sits (NEW / RESEARCHING / READY). Do the action, then advance the stage."),
    ],
)

# ---------------- SCREEN 4c: TRACKER — GATES & GRADING (2640x4442) ----------------
annotate(
    "4c_tracker_grading.png",
    "Screen 4c — Capstone Tracker: Weekly Gates & Grading",
    "The 15-week roadmap, how you're graded, the AI-vs-Hybrid challenge, and your weekly scorecard.",
    pins=[(1, 555, 309), (2, 322, 2600), (3, 510, 2766), (4, 1376, 2766), (5, 377, 3674), (6, 322, 3918)],
    keys=[
        (1, "Weekly gates", "The 15-week timeline of what's due each week (Week 3 is the challenge kickoff)."),
        (2, "How You're Graded", "Two lenses — the real dollars you move, and how effectively you wield the AI fleet."),
        (3, "Graded on real payload $", "Qualified pipeline $, high-probability opps, and kg advanced — not slideware."),
        (4, "AI effectiveness", "Leverage ratio, AI-assisted reply rate, human-vs-AI attribution, cost per opportunity."),
        (5, "The Challenge", "AI-only (fleet autonomous) vs Hybrid (you directing the fleet) on matched cohorts, head-to-head."),
        (6, "Weekly Scorecard", "Week-over-week trend on the graded metrics; populates once outreach begins."),
    ],
)

print("done")
