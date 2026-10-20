"""Coordinate Studio — web version (Flask).

This is the entry point Vercel (and any WSGI host) looks for: the top-level ``app`` object.
The page in ``web/index.html`` draws the graphs in the browser with Plotly.js and asks
``/api/compute`` for the maths.

Run locally with:  flask --app app run      (or)  gunicorn app:app
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from flask import Flask, Response, jsonify, request

from coordinate.parser import MAX_LINE_LENGTH, MAX_LINES
from coordinate.service import EXAMPLES_2D, EXAMPLES_3D, cards, figure_json, prepare, relations

# Vercel rejects function responses above 4.5 MB; plotting keeps figures far smaller, this is a safety net.
MAX_RESPONSE_BYTES = 4_000_000

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024  # requests are small JSON documents

_PAGE = (Path(__file__).resolve().parent / "web" / "index.html").read_text(encoding="utf-8")
_PAGE = _PAGE.replace("__CONFIG__", json.dumps({
    "examples": {"3d": EXAMPLES_3D, "2d": EXAMPLES_2D},
    "maxChars": MAX_LINES * (MAX_LINE_LENGTH + 1),
}).replace("</", "<\\/"))


def _number(value, default: float, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return min(max(number, low), high) if math.isfinite(number) else default


@app.get("/")
def index() -> Response:
    return Response(_PAGE, mimetype="text/html")


@app.get("/api/health")
def health():
    return jsonify(status="ok")


@app.post("/api/compute")
def compute():
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return jsonify(error="Expected a JSON object"), 400
    text = body.get("text", "")
    if not isinstance(text, str):
        return jsonify(error="'text' must be a string"), 400
    text = text[: MAX_LINES * (MAX_LINE_LENGTH + 1)]
    is_3d = body.get("mode") != "2d"
    rng = _number(body.get("range"), 10.0, 2.0, 50.0)
    opacity = _number(body.get("opacity"), 0.8, 0.2, 1.0) if is_3d else 1.0
    show_extra = bool(body.get("showExtra", True))

    prep = prepare(text, is_3d)
    errors = list(prep.errors)
    try:
        figure = figure_json(text, is_3d, rng, opacity, show_extra)
    except Exception:  # keep the rest of the page working even if one graph cannot be drawn
        figure = "null"
        errors.append("Could not draw the graph for this input.")

    result = {
        "errors": errors,
        "warnings": prep.warnings,
        "cards": cards(prep),
        "relations": relations(prep),
    }
    payload = json.dumps(result)
    if len(payload) + len(figure) > MAX_RESPONSE_BYTES:
        figure = "null"
        result["errors"] = [*errors, "The graph is too detailed to send — remove some equations."]
        payload = json.dumps(result)
    # The figure is already JSON (and cached), so splice it in rather than decoding and re-encoding megabytes.
    return Response(payload[:-1] + ', "figure": ' + figure + "}", mimetype="application/json")


if __name__ == "__main__":
    app.run(debug=True)
