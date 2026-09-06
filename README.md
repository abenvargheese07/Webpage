# Tiled PDF Generator

Turns any title + list of points into a print-ready A4 PDF with 6 copies
tiled on one page (3 columns × 2 rows, landscape, cut lines included).
Text is bold, centered, and auto-sized to fill each tile as much as
possible without spilling onto a second page — same style as the
"प्रार्थना विषय" card.

## Setup (one-time)

```bash
sudo apt-get install -y wkhtmltopdf poppler-utils
pip install --break-system-packages -r requirements.txt   # (no extra deps needed, stdlib only)
```

Keep `NotoSansDevanagari-Bold.ttf` in the same folder as the script (already
included here) — it supports Hindi/Devanagari text. For other scripts/languages,
pass your own bold font with `--font`.

## Usage

**1. Interactive** — just run it and answer the prompts:
```bash
python3 generate_tiled_pdf.py
```

**2. From a text file** — first line is the title, every line after is a point:
```bash
python3 generate_tiled_pdf.py --input sample_points.txt --output out.pdf
```

**3. Fully via command line:**
```bash
python3 generate_tiled_pdf.py \
  --title "प्रार्थना विषय" \
  --line "देश की उन्नति के लिए प्रार्थना करें" \
  --line "जवान पीढ़ी को रोजगार मिलने पाये" \
  --output out.pdf
```

## Useful options

| Flag             | Meaning                                          | Default    |
|-------------------|---------------------------------------------------|------------|
| `--cols`          | tiles per row                                      | 3          |
| `--rows`          | tile rows                                          | 2          |
| `--orientation`   | `landscape` or `portrait`                          | landscape  |
| `--page-size`     | `A4`, `Letter`, etc.                               | A4         |
| `--font`          | path to a bold .ttf/.otf font                      | bundled Devanagari font |
| `--title-size`    | starting title font size (px), auto-shrinks if needed | 40      |
| `--body-size`     | starting body font size (px), auto-shrinks if needed  | 26      |

Points don't need numbers — they're auto-numbered "1- ", "2- " etc. unless
they already start with a number.

The script always renders, checks the page count, and — if the text
overflowed to a 2nd page — shrinks the font by 1px and tries again, until
everything fits on a single page.
