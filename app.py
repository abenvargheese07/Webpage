#!/usr/bin/env python3
"""
app.py – Flask web frontend for the Church prayer-card PDF generator.

Serves a beautiful single-page UI where users enter a title + points,
configure grid/page settings, and download a print-ready tiled PDF.

PDF generation uses fpdf2 with HarfBuzz text shaping for proper
Devanagari script rendering.

Usage:
    python3 app.py
    # → open http://localhost:8080
"""

from __future__ import annotations

import os

from flask import Flask, render_template, request, send_file

from pdf.generator import generate_pdf

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    data = request.get_json(force=True)

    title = (data.get("title") or "").strip()
    raw_points = data.get("points", [])
    points = [p.strip() for p in raw_points if p.strip()]

    if not title:
        return {"error": "Title is required."}, 400
    if not points:
        return {"error": "At least one point is required."}, 400

    cols = int(data.get("cols", 3))
    rows = int(data.get("rows", 2))
    page_size = data.get("pageSize", "A4")
    orientation = data.get("orientation", "landscape")

    # Typography overrides from frontend (None → auto)
    title_size = data.get("titleSize")
    body_size = data.get("bodySize")
    title_gap = data.get("titleGap")
    if title_size is not None:
        title_size = float(title_size)
    if body_size is not None:
        body_size = float(body_size)
    if title_gap is not None:
        title_gap = float(title_gap)

    buf = generate_pdf(title, points, cols=cols, rows=rows,
                       page_size_name=page_size, orientation_name=orientation,
                       title_size=title_size, body_size=body_size,
                       title_gap=title_gap)

    return send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name="tiled_output.pdf")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 Prayer Card Generator running at http://localhost:{port}")
    app.run(debug=True, port=port)
