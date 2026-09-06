# Tiled PDF Generator

Turns any title + list of points into a print-ready A4 PDF with 6 copies
tiled on one page (3 columns × 2 rows, landscape, cut lines included).
Text is bold, centered, and auto-sized to fill each tile as much as
possible without spilling onto a second page — same style as the
"प्रार्थना विषय" card.

## Project Structure

```
├── app.py                  # Flask web app entry point
├── pdf/                    # PDF generation module
│   ├── __init__.py
│   ├── generator.py        # Web PDF logic (fpdf2 + HarfBuzz)
│   └── cli.py              # Standalone CLI generator (wkhtmltopdf)
├── static/fonts/           # Font assets
│   └── NotoSansDevanagari-Bold.ttf
├── templates/              # Jinja2 HTML templates
│   └── index.html
├── data/                   # Sample data files
│   └── sample_points.txt
├── requirements.txt
├── Procfile
└── README.md
```

## Setup (one-time)

```bash
sudo apt-get install -y wkhtmltopdf poppler-utils   # CLI generator only
pip3 install --break-system-packages -r requirements.txt
```

The font `NotoSansDevanagari-Bold.ttf` lives in `static/fonts/` and supports
Hindi/Devanagari text. For other scripts/languages, pass your own bold font
with `--font`.

## Web App

```bash
python3 app.py
# → open http://localhost:8080
```

## CLI Usage

**1. Interactive** — just run it and answer the prompts:
```bash
python3 -m pdf.cli
```

**2. From a text file** — first line is the title, every line after is a point:
```bash
python3 -m pdf.cli --input data/sample_points.txt --output out.pdf
```

**3. Fully via command line:**
```bash
python3 -m pdf.cli \
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
