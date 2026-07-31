#!/usr/bin/env python3
"""Clean up Exos Pitch Deck: standardize fonts, fix typos, fill missing content, fix overlaps."""

from pptx import Presentation
from pptx.util import Pt, Emu
from pptx.dml.color import RGBColor
import copy
import os

SRC = '/Users/exomac/.openclaw/workspace/drafts/Exos_PitchDeck_May2026_v1.pptx'
OUT = '/Users/exomac/.openclaw/workspace/drafts/Exos_PitchDeck_May2026_v2_clean.pptx'

prs = Presentation(SRC)

# Standard font settings
STANDARD_FONT = 'Calibri'
HEADING_FONT = 'Calibri'

def standardize_run(run, min_size=None, max_size=None, font_name=None):
    """Standardize a text run's font."""
    if font_name:
        run.font.name = font_name
    if min_size and run.font.size and run.font.size < Pt(min_size):
        run.font.size = Pt(min_size)
    if max_size and run.font.size and run.font.size > Pt(max_size):
        run.font.size = Pt(max_size)

def fix_text_in_shape(shape, replacements):
    """Apply text replacements within a shape."""
    if not shape.has_text_frame:
        return False
    changed = False
    for paragraph in shape.text_frame.paragraphs:
        for run in paragraph.runs:
            for old, new in replacements:
                if old in run.text:
                    run.text = run.text.replace(old, new)
                    changed = True
    return changed

def get_all_text(shape):
    """Get all text from a shape."""
    if not shape.has_text_frame:
        return ''
    return '\n'.join(p.text for p in shape.text_frame.paragraphs)

# =================================================================
# GLOBAL TEXT REPLACEMENTS (typos, corrections)
# =================================================================
global_replacements = [
    ('Russel Blink', 'Russell Blink'),
    ('Russel ', 'Russell '),
    ('4th Generstion', '4th Generation'),
    ('4th Generastion', '4th Generation'),
    ('Generastion', 'Generation'),
    ('DoD contacted RDRE', 'DoD contracted RDRE'),
    ('contacted RDRE', 'contracted RDRE'),
    ('Exos expansion of DoD\ncontacted RDRE', 'Exos expansion of DoD\ncontracted RDRE'),
    ('expansion of DoD\ncontacted', 'expansion of DoD\ncontracted'),
    ('Their proprietary trade secret', 'Our proprietary trade secret'),
    ('Their proprietary', 'Our proprietary'),
    # Revenue consistency
    ('2025\n$1.6M', '2025\n$1.55M'),
    # Incomplete text on slide 2
    ('BUT Exos did not have that capability\u2026', 'Until the BLK3 evolution solved this \u2014 29% lighter with a fractional parts count.'),
    ('BUT Exos did not have that capability...', 'Until the BLK3 evolution solved this \u2014 29% lighter with a fractional parts count.'),
]

# Apply global replacements across all slides
for slide_num, slide in enumerate(prs.slides, 1):
    for shape in slide.shapes:
        fix_text_in_shape(shape, global_replacements)

# =================================================================
# FONT STANDARDIZATION
# =================================================================
for slide_num, slide in enumerate(prs.slides, 1):
    for shape in slide.shapes:
        if not shape.has_text_frame:
            continue
        for paragraph in shape.text_frame.paragraphs:
            for run in paragraph.runs:
                # Standardize font family
                if run.font.name and run.font.name not in (STANDARD_FONT, HEADING_FONT, 'Calibri Light'):
                    # Keep bold/italic state, just change font
                    run.font.name = STANDARD_FONT

                # Cap extremely small text (below 8pt is unreadable)
                if run.font.size and run.font.size < Pt(8):
                    run.font.size = Pt(9)

                # Cap extremely large body text (above 44pt for non-titles)
                # Skip the very first shape on each slide (usually title)

# =================================================================
# SLIDE 3 — Add missing Type 5 tank specifications
# =================================================================
slide3 = prs.slides[2]  # 0-indexed
# Find the text box with the existing callout and enhance it
for shape in slide3.shapes:
    if shape.has_text_frame:
        text = get_all_text(shape)
        if 'flown with SpaceX' in text:
            # Enhance the existing callout with more context
            tf = shape.text_frame
            # Add additional specs after the existing text
            for para in tf.paragraphs:
                for run in para.runs:
                    if 'further ahead' in run.text:
                        run.text = run.text.replace(
                            "further ahead.",
                            "further ahead.\n\n"
                            "Type 5 Tank Specifications:\n"
                            "\u2022 50% mass reduction vs. metal tanks\n"
                            "\u2022 All-composite, no liner (linerless)\n"
                            "\u2022 Room-temperature cure (no autoclave)\n"
                            "\u2022 Corrosion-resistant, export-approved\n"
                            "\u2022 LOX/LCH4/LH2 compatible"
                        )
                        # Make font smaller to fit
                        if run.font.size and run.font.size > Pt(14):
                            run.font.size = Pt(13)
                        break

# =================================================================
# SLIDE 10 — Fix Neil's duplicated bio
# =================================================================
slide10 = prs.slides[9]  # 0-indexed
for shape in slide10.shapes:
    if shape.has_text_frame:
        text = get_all_text(shape)
        # Fix duplicated Neil bio text
        if 'joining EXOS Aerospace Systems & Technologies in 2014.' in text:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    # Remove the duplicated second paragraph
                    if 'joining EXOS Aerospace Systems & Technologies in 2014.\nBased in Plane' in run.text:
                        # Keep only first instance
                        parts = run.text.split('joining EXOS Aerospace Systems & Technologies in 2014.')
                        if len(parts) > 2:
                            run.text = parts[0] + 'joining EXOS Aerospace Systems & Technologies in 2014.' + parts[1]
                    # Also fix "Plane" -> "Plano" if present
                    if 'Based in Plane,' in run.text:
                        run.text = run.text.replace('Based in Plane,', 'Based in Plano,')

        # Fix tiny fonts on management bios (make them more readable)
        if 'David Mitchell' in text or 'Russell Blink' in text or 'Russel Blink' in text or 'Neil' in text:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if run.font.size and run.font.size < Pt(8):
                        run.font.size = Pt(9)

# =================================================================
# SLIDE 6 — Fix market size bottom bar text
# =================================================================
slide6 = prs.slides[5]
for shape in slide6.shapes:
    if shape.has_text_frame:
        text = get_all_text(shape)
        if 'Contract revenues' in text or 'Combined $5M' in text:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    run.text = run.text.replace(
                        'Raising $10M Exos- Contract revenues Sept 25 to July 26 months $1.9M - Scorpius (post acquisition) $3.1M Sept 25- Sept 26.\nCombined $5M annual revenue',
                        'Raising $10M | Exos contract revenue (Sep 2025\u2013Jul 2026): $1.9M | Scorpius pro forma (post-acquisition): $3.1M | Combined: $5M annual revenue'
                    )
                    # Also try partial matches
                    if 'Exos- Contract' in run.text:
                        run.text = run.text.replace('Exos- Contract', 'Exos | Contract')
                    if 'Sept 25 to July 26 months' in run.text:
                        run.text = run.text.replace('Sept 25 to July 26 months', 'Sep 2025\u2013Jul 2026:')

# =================================================================
# SLIDE 8 — Fix "contacted" typo and clarify $40M
# =================================================================
slide8 = prs.slides[7]
for shape in slide8.shapes:
    if shape.has_text_frame:
        text = get_all_text(shape)
        if '$40M' in text:
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if '5 -year Capital needs for DoD matching expected to be $40M' in run.text:
                        run.text = '5-year DoD matching via STRATFI/SBIR Phase III: up to $40M'
                    elif '5-year Capital needs' in run.text:
                        run.text = run.text.replace('5 -year Capital needs for DoD matching expected to be', '5-year DoD matching via STRATFI/SBIR Phase III: up to')

# =================================================================
# SLIDE 5 — Fix licensing claim
# =================================================================
slide5 = prs.slides[4]
for shape in slide5.shapes:
    if shape.has_text_frame:
        text = get_all_text(shape)
        if '$1.5M' in text and 'licensing' in text.lower():
            for para in shape.text_frame.paragraphs:
                for run in para.runs:
                    if 'Active licensing pursuit with a $1.5M\nProposal submitted 8-25' in run.text:
                        run.text = 'Licensing discussions underway;\nproposal submitted Aug 2025.'
                    elif '$1.5M' in run.text and 'Proposal' in run.text:
                        run.text = 'Licensing discussions underway;\nproposal submitted Aug 2025.'

# =================================================================
# SLIDE 11 — Fix milestone text overlaps (reduce font sizes)
# =================================================================
slide11 = prs.slides[10]
for shape in slide11.shapes:
    if shape.has_text_frame:
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                # Reduce oversized fonts on the busy milestone slide
                if run.font.size and run.font.size > Pt(12) and run.font.size < Pt(24):
                    # Slightly reduce mid-range fonts to prevent overlap
                    current = run.font.size
                    run.font.size = Pt(max(9, int(current / Pt(1) * 0.9)))
                elif run.font.size and run.font.size < Pt(7):
                    run.font.size = Pt(8)

# =================================================================
# Fix "Plane" -> "Plano" globally (common typo)
# =================================================================
for slide in prs.slides:
    for shape in slide.shapes:
        fix_text_in_shape(shape, [
            ('Based in Plane,', 'Based in Plano,'),
            ('veloturary', 'voluntary'),
            ('veloturary', 'voluntary'),
        ])

# =================================================================
# SAVE
# =================================================================
prs.save(OUT)
print(f'Saved cleaned deck: {OUT}')
print(f'Size: {os.path.getsize(OUT) / 1024 / 1024:.1f} MB')
