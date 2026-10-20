"""Everything the user interfaces need, independent of the UI framework.

Both the Flask web app (``app.py``, used on Vercel and other hosts) and the Streamlit app
(``streamlit_app.py``) call these functions, so they always show the same results.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from itertools import combinations

import numpy as np
import sympy as sp

from .analysis import Analysis, analyse_2d, analyse_3d
from .parser import Equation, Point, Values, Vector, evaluate, parse_lines
from .plotting import PALETTE, figure_2d, figure_3d

EXAMPLES_3D = {
    "Plane  2x + 4y + 6z = 12": "2x + 4y + 6z = 12\nA(1, 1, 1)",
    "Your example  2x + 4y + 6z": "2x + 4y + 6z\nx = 1, y = 2, z = 3",
    "Sphere": "x^2 + y^2 + z^2 = 16\nP(0, 0, 4)",
    "Saddle  z = x² − y²": "z = (x^2 - y^2) / 4",
    "Ripple": "z = 2 sin(sqrt(x^2 + y^2))",
    "Two planes + vectors": "x + y + z = 3\nx - y = 0\n<3, 0, 2>\nu = <0, 4, 1>",
    "Points & distance": "A(1, 2, 3)\nB(-3, 4, -2)\nC(4, -4, 1)",
}
EXAMPLES_2D = {
    "Line  2x + 4y = 8": "2x + 4y = 8\nx = 2, y = 1",
    "Parabola": "y = x^2 - 4x + 3",
    "Circle": "x^2 + y^2 = 16\n(0, 4)",
    "Sine wave": "y = 3 sin(x)",
    "Lines & points": "y = 2x + 1\ny = -x + 4\nA(1, 3)\nB(-2, -3)",
    "Vectors": "<3, 4>\nw = <-2, 3>",
    "Hyperbola": "x^2 - y^2 = 4",
}
DEFAULT_VALUES = {"x": 1.0, "y": 2.0, "z": 3.0}
MAX_VALUE = 1e6


@dataclass(frozen=True)
class Prepared:
    errors: list[str]
    warnings: list[str]
    plot_items: list[tuple[str, object]]   # (label, Analysis | Point | Vector) in input order
    analysed: list[tuple[Equation, Analysis]]
    typed_values: dict[str, float]         # from lines such as "x = 1, y = 2, z = 3"


@lru_cache(maxsize=256)
def prepare(text: str, is_3d: bool) -> Prepared:
    """Parse and analyse the input. Cached, so changing a slider does not redo the maths."""
    items, errors = parse_lines(text)
    warnings, plot_items, analysed, typed_values = [], [], [], {}
    for item in items:
        if isinstance(item, Values):
            typed_values.update(item.values)
        elif isinstance(item, Equation):
            try:
                info = analyse_3d(item) if is_3d else analyse_2d(item)
            except ValueError as exc:
                warnings.append(f"'{item.text}' {exc}")
                continue
            except Exception:  # never let one odd equation take the whole page down
                warnings.append(f"'{item.text}' could not be analysed")
                continue
            plot_items.append((item.text, info))
            analysed.append((item, info))
        elif not is_3d and len(getattr(item, "coords", getattr(item, "components", ()))) == 3:
            warnings.append(f"'{item.text}' has 3 numbers — switch to 3D Space to plot it")
        else:
            plot_items.append((item.text, item))
    return Prepared(errors, warnings, plot_items, analysed, typed_values)


def clamp_value(value: float) -> float:
    return min(max(float(value), -MAX_VALUE), MAX_VALUE)


def build_figure(text: str, is_3d: bool, rng: float, opacity: float, show_extra: bool, coords: tuple):
    """The Plotly figure, with the plugged-in point drawn as a highlighted star."""
    star = ("★ (" + ", ".join(f"{v:g}" for v in coords) + ")", Point("plug", "★", coords, highlight=True))
    items = [*prepare(text, is_3d).plot_items, star]
    return figure_3d(items, rng, opacity, show_extra) if is_3d else figure_2d(items, rng, show_extra)


@lru_cache(maxsize=32)
def figure_json(text: str, is_3d: bool, rng: float, opacity: float, show_extra: bool, coords: tuple) -> str:
    return build_figure(text, is_3d, rng, opacity, show_extra, coords).to_json()


def show(value: float) -> str:
    return r"\text{undefined}" if math.isnan(value) else f"{value:.6g}"


def _colors(prep: Prepared) -> dict[str, str]:
    return {label: PALETTE[i % len(PALETTE)] for i, (label, _) in enumerate(prep.plot_items)}


def evaluations(prep: Prepared, values: dict[str, float]) -> list[dict]:
    """Each equation worked out at the given values, e.g. 2x + 4y + 6z = 2·(1) + 4·(2) + 6·(3) = 28."""
    colors = _colors(prep)
    rows = []
    for eq, info in prep.analysed:
        lhs_work, lhs_val = evaluate(eq.lhs, values)
        working = f"{sp.latex(eq.lhs)} \\;=\\; {lhs_work} \\;=\\; \\mathbf{{{show(lhs_val)}}}"
        if eq.has_equals:
            _, rhs_val = evaluate(eq.rhs, values)
            working += f"\\qquad \\text{{(right side }} = {show(rhs_val)}\\text{{)}}"
        residual = evaluate(info.implicit, values)[1]
        rows.append({
            "text": eq.text,
            "color": colors[eq.text],
            "working": working,
            "on_graph": not math.isnan(residual) and abs(residual) < 1e-9,
        })
    return rows


def cards(prep: Prepared) -> list[dict]:
    """The analysis of each equation: its kind (line, plane, sphere, ...) and key facts as LaTeX."""
    colors = _colors(prep)
    return [{"label": label, "kind": entry.kind, "color": colors[label], "facts": [list(f) for f in entry.facts]}
            for label, entry in prep.plot_items if isinstance(entry, Analysis)]


def relations(prep: Prepared) -> list[dict]:
    """Distances between points and dot / cross products of vectors. Each row is (label, LaTeX)."""
    points = [e for _, e in prep.plot_items if isinstance(e, Point)]
    vectors = [e for _, e in prep.plot_items if isinstance(e, Vector)]
    sections = []

    if len(points) >= 2:
        rows = []
        for a, b in combinations(points, 2):
            pa, pb = np.array(a.coords), np.array(b.coords)
            if len(pa) != len(pb):
                continue
            mid = ", ".join(f"{v:g}" for v in (pa + pb) / 2)
            rows.append((f"{a.label}{b.label}", f"\\text{{distance}} = {float(np.linalg.norm(pa - pb)):.4g},"
                                                f"\\quad \\text{{midpoint}} = ({mid})"))
        sections.append({"title": "📏 Between points", "rows": rows})

    if vectors:
        rows = []
        for a, b in combinations(vectors, 2):
            va, vb = np.array(a.components, float), np.array(b.components, float)
            if len(va) != len(vb):
                continue
            dot = float(va @ vb)
            na, nb = np.linalg.norm(va), np.linalg.norm(vb)
            angle = math.degrees(math.acos(max(-1.0, min(1.0, dot / (na * nb))))) if na and nb else float("nan")
            rows.append((f"{a.label} · {b.label}", f"{dot:g}, \\quad \\text{{angle}} = {show(angle)}^\\circ"))
            if len(va) == 3:
                cross = ", ".join(f"{v:g}" for v in np.cross(va, vb))
                rows.append((f"{a.label} × {b.label}", f"\\langle {cross} \\rangle"))
        rows += [(f"|{v.label}|", f"{float(np.linalg.norm(v.components)):.4g}") for v in vectors]
        sections.append({"title": "➡️ Vectors", "rows": rows})
    return sections
