#!/usr/bin/env python3
"""
generate_tiled_pdf.py

Takes a title + a list of text lines (e.g. prayer topics, notice points, etc.)
from the user and produces a print-ready A4 landscape PDF with 6 identical
copies tiled in a 3x2 grid (cut lines included), matching the "prayer topics"
card style: bold Devanagari/Unicode text, centered, auto-sized to fill each
tile as much as possible without overflowing the page.

REQUIREMENTS (install once):
    sudo apt-get install -y wkhtmltopdf poppler-utils
    # poppler-utils gives us `pdfinfo` which is used to detect page overflow

USAGE

  1) Interactive (just run it and follow the prompts):
       python3 generate_tiled_pdf.py

  2) From a text file (first line = title, remaining lines = points):
       python3 generate_tiled_pdf.py --input points.txt --output out.pdf

  3) Fully via command line:
       python3 generate_tiled_pdf.py \
           --title "प्रार्थना विषय" \
           --line "देश की उन्नति के लिए प्रार्थना करें" \
           --line "जवान पीढ़ी को रोजगार मिलने पाये" \
           --output out.pdf

  4) Change grid / orientation / font:
       python3 generate_tiled_pdf.py --input points.txt --cols 2 --rows 3 \
           --orientation portrait --font /path/to/YourFont-Bold.ttf

Points don't need to be pre-numbered -- the script numbers them "1- ", "2- ",
etc. automatically unless they already start with a number.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_FONT = os.path.join(SCRIPT_DIR, "NotoSansDevanagari-Bold.ttf")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="hi">
<head>
<meta charset="UTF-8">
<style>
  @font-face {{
    font-family: 'TileFont';
    src: url('{font_path}');
  }}
  @page {{ size: {page_size} {orientation}; margin: 0; }}
  * {{ box-sizing: border-box; }}
  html, body {{ width: 100%; height: 100%; margin: 0; }}
  body {{
    font-family: 'TileFont', sans-serif;
    font-weight: bold;
    color: #000;
  }}
  .grid {{
    display: table;
    table-layout: fixed;
    width: 100%;
    height: 100%;
    border-collapse: collapse;
  }}
  .row {{ display: table-row; }}
  .cell {{
    display: table-cell;
    width: {cell_width_pct}%;
    border: 1px dashed #999;
    padding: 6mm 8mm;
    text-align: center;
    vertical-align: middle;
    overflow: hidden;
  }}
  .cell h1 {{ font-size: {title_size}px; margin: 0 0 {title_gap}px 0; }}
  .cell p {{ font-size: {body_size}px; line-height: 1.5; margin: 0 0 {body_gap}px 0; }}
</style>
</head>
<body>
  <div class="grid">
{rows_html}
  </div>
</body>
</html>
"""


def build_card_html(title, lines):
    """Build the inner HTML (title + numbered paragraphs) for one tile."""
    numbered = []
    for i, line in enumerate(lines, start=1):
        line = line.strip()
        if not line:
            continue
        # If the line doesn't already start with "1-", "1.", "1)" etc, number it.
        if re.match(r"^\d+[-.)]\s*", line):
            numbered.append(line)
        else:
            numbered.append(f"{i}- {line}")
    paras = "\n      ".join(f"<p>{escape_html(l)}</p>" for l in numbered)
    return f"<h1>{escape_html(title)}</h1>\n      {paras}"


def escape_html(text):
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_full_html(title, lines, cols, rows, font_path, page_size,
                     orientation, title_size, body_size):
    card_html = build_card_html(title, lines)
    cell_width_pct = round(100.0 / cols, 4)
    title_gap = max(6, int(title_size * 0.45))
    body_gap = max(4, int(body_size * 0.5))

    rows_html_parts = []
    for _r in range(rows):
        cells = "\n    ".join(
            f'<div class="cell">\n      {card_html}\n    </div>' for _c in range(cols)
        )
        rows_html_parts.append(f'    <div class="row">\n    {cells}\n    </div>')
    rows_html = "\n".join(rows_html_parts)

    return HTML_TEMPLATE.format(
        font_path=font_path,
        page_size=page_size,
        orientation=orientation,
        cell_width_pct=cell_width_pct,
        title_size=title_size,
        title_gap=title_gap,
        body_size=body_size,
        body_gap=body_gap,
        rows_html=rows_html,
    )


def render_pdf(html_path, pdf_path, page_size, orientation):
    o_flag = "Landscape" if orientation == "landscape" else "Portrait"
    cmd = [
        "wkhtmltopdf",
        "--enable-local-file-access",
        "--page-size", page_size,
        "-O", o_flag,
        "--margin-top", "0",
        "--margin-bottom", "0",
        "--margin-left", "0",
        "--margin-right", "0",
        "-q",
        html_path,
        pdf_path,
    ]
    subprocess.run(cmd, check=True)


def pdf_page_count(pdf_path):
    out = subprocess.run(["pdfinfo", pdf_path], capture_output=True, text=True, check=True)
    for line in out.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":")[1].strip())
    return 1


def generate(title, lines, output_path, cols=3, rows=2, font_path=DEFAULT_FONT,
             page_size="A4", orientation="landscape",
             start_title_size=40, start_body_size=26, min_size=10, verbose=True):
    """
    Build the tiled PDF, auto-shrinking text until everything fits on a
    single page (in case the text is long).
    """
    if not os.path.isfile(font_path):
        raise FileNotFoundError(
            f"Font not found at {font_path}. Pass --font /path/to/font.ttf "
            f"or place NotoSansDevanagari-Bold.ttf next to this script."
        )

    title_size = start_title_size
    body_size = start_body_size
    # keep the same ratio between title and body while shrinking
    ratio = start_title_size / start_body_size

    with tempfile.TemporaryDirectory() as tmp:
        html_path = os.path.join(tmp, "tile.html")
        tmp_pdf = os.path.join(tmp, "tile.pdf")

        while True:
            html = build_full_html(
                title, lines, cols, rows, font_path, page_size,
                orientation, int(title_size), int(body_size)
            )
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html)

            render_pdf(html_path, tmp_pdf, page_size, orientation)
            pages = pdf_page_count(tmp_pdf)

            if verbose:
                print(f"  tried title={int(title_size)}px body={int(body_size)}px -> {pages} page(s)")

            if pages <= 1 or body_size <= min_size:
                break

            body_size -= 1
            title_size = body_size * ratio

        shutil.copy(tmp_pdf, output_path)

    if verbose:
        print(f"Done -> {output_path}")
    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_input_file(path):
    with open(path, "r", encoding="utf-8") as f:
        raw_lines = [l.rstrip("\n") for l in f if l.strip() != ""]
    if not raw_lines:
        raise ValueError("Input file is empty")
    title = raw_lines[0].strip()
    lines = raw_lines[1:]
    return title, lines


def interactive_input():
    print("Enter the title (heading) for the card:")
    title = input("> ").strip()
    print("\nNow enter each point, one per line.")
    print("Press Enter on an empty line when you're done.\n")
    lines = []
    while True:
        line = input(f"{len(lines) + 1}. ")
        if line.strip() == "":
            break
        lines.append(line.strip())
    if not lines:
        print("No points entered, exiting.")
        sys.exit(1)
    return title, lines


def main():
    parser = argparse.ArgumentParser(description="Generate a 6-up tiled, print-ready PDF from text.")
    parser.add_argument("--title", help="Card title / heading")
    parser.add_argument("--line", action="append", dest="lines",
                         help="A single point/line of text. Repeat --line for each point.")
    parser.add_argument("--input", help="Path to a text file: first line = title, rest = points")
    parser.add_argument("--output", default="tiled_output.pdf", help="Output PDF path")
    parser.add_argument("--cols", type=int, default=3, help="Tiles per row (default 3)")
    parser.add_argument("--rows", type=int, default=2, help="Tile rows (default 2)")
    parser.add_argument("--orientation", choices=["landscape", "portrait"], default="landscape")
    parser.add_argument("--page-size", default="A4", help="Page size, e.g. A4, Letter (default A4)")
    parser.add_argument("--font", default=DEFAULT_FONT, help="Path to a bold TTF/OTF font file")
    parser.add_argument("--title-size", type=int, default=40, help="Starting title font size in px")
    parser.add_argument("--body-size", type=int, default=26, help="Starting body font size in px")
    args = parser.parse_args()

    if args.input:
        title, lines = parse_input_file(args.input)
    elif args.title and args.lines:
        title, lines = args.title, args.lines
    else:
        title, lines = interactive_input()

    generate(
        title=title,
        lines=lines,
        output_path=args.output,
        cols=args.cols,
        rows=args.rows,
        font_path=args.font,
        page_size=args.page_size,
        orientation=args.orientation,
        start_title_size=args.title_size,
        start_body_size=args.body_size,
    )


if __name__ == "__main__":
    main()
