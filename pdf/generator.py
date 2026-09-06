#!/usr/bin/env python3
"""
pdf/generator.py – PDF generation logic for the Flask web frontend.

Produces a tiled, print-ready PDF with identical prayer-cards arranged in a
configurable grid.  Uses fpdf2 with HarfBuzz text shaping for proper
Devanagari script rendering.
"""

from __future__ import annotations

import io
import os

from fpdf import FPDF

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_PATH = os.path.join(PROJECT_ROOT, "static", "fonts",
                         "NotoSansDevanagari-Bold.ttf")
FONT_NAME = "NotoDevanagari"


# ---------------------------------------------------------------------------
# PDF generation helpers
# ---------------------------------------------------------------------------

def _count_lines(pdf: FPDF, text: str, font_name: str, font_size: float,
                 max_width: float) -> int:
    """Estimate how many lines *text* will occupy when wrapped at *max_width*,
    using actual glyph-width measurements from the font."""
    pdf.set_font(font_name, size=font_size)
    if not text.strip():
        return 1

    words = text.split()
    lines = 1
    current_w = 0.0
    space_w = pdf.get_string_width(" ")

    for word in words:
        word_w = pdf.get_string_width(word)
        needed = word_w + (space_w if current_w > 0 else 0)
        if current_w > 0 and current_w + needed > max_width:
            lines += 1
            current_w = word_w
        else:
            current_w += needed

    return max(1, lines)


def _content_height(pdf: FPDF, font_name: str,
                    title: str, points: list[str], max_width: float,
                    title_size: float, body_size: float,
                    title_leading: float, body_leading: float,
                    gap: float) -> float:
    """Compute the total height of the card content (title + gap + points)."""
    h = _count_lines(pdf, title, font_name, title_size, max_width) * title_leading
    h += gap
    for i, pt in enumerate(points, 1):
        h += _count_lines(pdf, f"{i}- {pt}", font_name, body_size, max_width) * body_leading
    return h


def _auto_shrink(pdf: FPDF, font_name: str,
                 title: str, points: list[str],
                 usable_w: float, usable_h: float,
                 start_title: float, start_body: float,
                 gap: float, min_size: float = 8) -> tuple[float, float]:
    """Return the largest (title_size, body_size) that fit the cell."""
    ratio = start_title / start_body if start_body > 0 else 1.636
    body = start_body

    while body >= min_size:
        ts = body * ratio
        h = _content_height(pdf, font_name, title, points, usable_w,
                            ts, body, ts * 1.35, body * 1.55, gap)
        if h <= usable_h:
            return ts, body
        body -= 1

    return min_size * ratio, min_size


def _draw_card(pdf: FPDF, font_name: str,
               cx: float, cy: float, cell_w: float, cell_h: float,
               title: str, points: list[str],
               title_size: float, body_size: float, gap: float):
    """Draw one card (title + numbered points) centred inside the rectangle
    (cx, cy, cell_w, cell_h) where (cx, cy) is the top-left corner."""

    pad_x, pad_y = 17, 14          # ≈6 mm, ≈5 mm (in points)
    usable_w = cell_w - 2 * pad_x
    usable_h = cell_h - 2 * pad_y
    title_leading = title_size * 1.35
    body_leading  = body_size * 1.55

    # Total height for vertical centering
    total_h = _content_height(pdf, font_name, title, points, usable_w,
                              title_size, body_size,
                              title_leading, body_leading, gap)
    start_y = cy + pad_y + max(0, (usable_h - total_h) / 2)
    left_x  = cx + pad_x

    # ---- Title (centred) ----
    pdf.set_font(font_name, size=title_size)
    pdf.set_xy(left_x, start_y)
    pdf.multi_cell(w=usable_w, h=title_leading, text=title, align="C")
    cur_y = pdf.get_y() + gap

    # ---- Points (centred) ----
    pdf.set_font(font_name, size=body_size)
    for i, pt in enumerate(points, 1):
        pdf.set_xy(left_x, cur_y)
        pdf.multi_cell(w=usable_w, h=body_leading, text=f"{i}- {pt}", align="C")
        cur_y = pdf.get_y()


def generate_pdf(title: str, points: list[str], cols: int = 3, rows: int = 2,
                 page_size_name: str = "A4", orientation_name: str = "landscape",
                 title_size: float | None = None, body_size: float | None = None,
                 title_gap: float | None = None) -> io.BytesIO:
    """Generate a tiled PDF and return it as an in-memory BytesIO buffer."""

    orient = "L" if orientation_name == "landscape" else "P"
    fmt = page_size_name if page_size_name in ("A4", "Letter") else "A4"

    pdf = FPDF(orientation=orient, unit="pt", format=fmt)
    pdf.add_page()
    pdf.set_auto_page_break(auto=False)
    pdf.set_margin(0)

    # Register the Devanagari font
    font_name = FONT_NAME
    if os.path.isfile(FONT_PATH):
        pdf.add_font(font_name, "", FONT_PATH)
    else:
        font_name = "Helvetica"

    # Enable HarfBuzz text shaping for proper Devanagari conjuncts
    try:
        pdf.set_text_shaping(True)
    except Exception:
        pass  # graceful fallback if uharfbuzz is not available

    page_w, page_h = pdf.w, pdf.h
    cell_w = page_w / cols
    cell_h = page_h / rows

    pad_x, pad_y = 17, 14
    usable_w = cell_w - 2 * pad_x
    usable_h = cell_h - 2 * pad_y

    ts  = float(title_size) if title_size else 36.0
    bs  = float(body_size)  if body_size  else 22.0
    gap = float(title_gap)  if title_gap is not None else bs * 0.6

    # Always auto-shrink so content fits the cell
    ts, bs = _auto_shrink(pdf, font_name, title, points,
                          usable_w, usable_h, ts, bs, gap)

    # ---- Dashed cut-lines ----
    pdf.set_draw_color(150, 150, 150)
    pdf.set_dash_pattern(dash=4, gap=4)
    pdf.set_line_width(0.5)
    for c in range(1, cols):
        x = c * cell_w
        pdf.line(x, 0, x, page_h)
    for r in range(1, rows):
        y = r * cell_h
        pdf.line(0, y, page_w, y)

    # ---- Cards ----
    pdf.set_text_color(0, 0, 0)
    for idx in range(cols * rows):
        col = idx % cols
        row = idx // cols
        _draw_card(pdf, font_name,
                   col * cell_w, row * cell_h, cell_w, cell_h,
                   title, points, ts, bs, gap)

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf
