"""Coordinate Studio — an interactive 2D / 3D coordinate system.

Run with:  streamlit run app.py
"""

from __future__ import annotations

import math
from itertools import combinations

import numpy as np
import sympy as sp
import streamlit as st

from coordinate.analysis import analyse_2d, analyse_3d
from coordinate.parser import Equation, Point, Values, Vector, evaluate, parse_lines
from coordinate.plotting import PALETTE, figure_2d, figure_3d

st.set_page_config(page_title="Coordinate Studio", page_icon="📐", layout="wide")

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

# ----------------------------------------------------------------------------- styling

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background: radial-gradient(circle at 15% 0%, #1e1b4b 0%, #0b1020 45%, #050814 100%); }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #111827 0%, #0b1020 100%);
        border-right: 1px solid #1f2937; }
    .hero { padding: 1.2rem 1.6rem; border-radius: 18px; margin-bottom: 1rem;
        background: linear-gradient(135deg, rgba(56,189,248,.18), rgba(192,132,252,.18));
        border: 1px solid rgba(148,163,184,.25); box-shadow: 0 10px 40px rgba(0,0,0,.35); }
    .hero h1 { margin: 0; font-weight: 800; font-size: 2.3rem;
        background: linear-gradient(90deg, #38bdf8, #c084fc, #f472b6);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .hero p { margin: .3rem 0 0 0; color: #cbd5e1; }
    .card { background: rgba(15,23,42,.75); border: 1px solid #1f2937; border-radius: 14px;
        padding: .9rem 1.1rem; margin-bottom: .8rem; box-shadow: 0 4px 20px rgba(0,0,0,.25); }
    .card h4 { margin: 0 0 .3rem 0; font-size: 1rem; }
    .chip { display: inline-block; padding: 2px 10px; border-radius: 999px; font-size: .75rem;
        font-weight: 600; color: #0b1020; margin-left: 6px; }
    .stTextArea textarea { font-family: 'JetBrains Mono', Consolas, monospace; font-size: 1.05rem;
        background: #0f172a; color: #e2e8f0; border-radius: 12px; }
    div[data-testid="stMetric"] { background: rgba(15,23,42,.75); border: 1px solid #1f2937;
        border-radius: 12px; padding: .5rem .8rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>📐 Coordinate Studio</h1>
      <p>Type equations like <code>2x + 4y + 6z = 12</code>, points like <code>A(1, 2, 3)</code> or vectors like
      <code>&lt;3, 4, 5&gt;</code> — see them in a live, rotatable 3D space or on a 2D plane.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------- sidebar

with st.sidebar:
    st.markdown("### ⚙️ View")
    mode = st.radio("Coordinate system", ["3D Space", "2D Plane"], horizontal=True, label_visibility="collapsed")
    is_3d = mode == "3D Space"
    examples = EXAMPLES_3D if is_3d else EXAMPLES_2D

    rng = st.slider("Axis range  (±)", 2, 50, 10 if is_3d else 8)
    if is_3d:
        opacity = st.slider("Surface opacity", 0.2, 1.0, 0.8, 0.05)
        show_axes = st.toggle("Show coloured X / Y / Z axes", True)
    else:
        show_grid = st.toggle("Show grid", True)

    st.markdown("### ✨ Examples")
    choice = st.selectbox("Load an example", list(examples), label_visibility="collapsed")
    if st.button("Load example", width="stretch"):
        st.session_state[f"input_{mode}"] = examples[choice]

    st.markdown("### 📝 Syntax")
    st.markdown(
        """
- `2x + 4y + 6z = 12` → plane
- `2x + 4y + 6z` → same as `… = 0`
- `z = x^2 + y^2`, `y = sin(x)`
- `x^2 + y^2 + z^2 = 9` → sphere
- `x = 1, y = 2, z = 3` → numbers to plug in
- `A(1, 2, 3)` or `(1, 2)` → point
- `<1, 2, 3>` or `v = <1, 2>` → vector
- Functions: `sin cos tan sqrt exp ln abs`, constant `pi`
- `#` starts a comment
        """
    )

# ----------------------------------------------------------------------------- input

key = f"input_{mode}"
if key not in st.session_state:
    st.session_state[key] = list(examples.values())[0]

text = st.text_area("Equations, points, vectors and values — one per line", key=key, height=130)
items, errors = parse_lines(text)
for err in errors:
    st.error(err, icon="⚠️")

# Values typed as "x = 1, y = 2, z = 3" fill the plug-in boxes below.
typed_values = {}
for item in items:
    if isinstance(item, Values):
        typed_values.update(item.values)

# Analyse equations and keep the plottable items in input order.
plot_items, analysed = [], []
for item in items:
    if isinstance(item, Equation):
        try:
            info = analyse_3d(item) if is_3d else analyse_2d(item)
        except (ValueError, NotImplementedError, TypeError) as exc:
            st.warning(f"`{item.text}` — {exc}", icon="ℹ️")
            continue
        plot_items.append((item.text, info))
        analysed.append((item, info))
    elif isinstance(item, Point):
        if not is_3d and len(item.coords) == 3:
            st.warning(f"`{item.text}` has 3 coordinates — switch to 3D Space to plot it.", icon="ℹ️")
            continue
        plot_items.append((item.text, item))
    elif isinstance(item, Vector):
        if not is_3d and len(item.components) == 3:
            st.warning(f"`{item.text}` has 3 components — switch to 3D Space to plot it.", icon="ℹ️")
            continue
        plot_items.append((item.text, item))

# ----------------------------------------------------------------------------- plug in numbers

with st.container(border=True):
    st.markdown("#### 🧮 Plug in numbers")
    st.caption("Type values here, or write a line like `x = 1, y = 2" + (", z = 3" if is_3d else "") +
               "` above. Each equation is worked out step by step and the point ★ is drawn on the graph.")
    names = ["x", "y", "z"] if is_3d else ["x", "y"]
    defaults = {"x": 1.0, "y": 2.0, "z": 3.0}
    cols = st.columns(len(names))
    # The widget is keyed by its typed value, so editing the text box resets the box to that value.
    values = {n: col.number_input(n, value=float(typed_values.get(n, defaults[n])), step=1.0, format="%g",
                                  key=f"plug_{mode}_{n}_{typed_values.get(n)}")
              for n, col in zip(names, cols)}

    if not analysed:
        st.info("Add an equation above (e.g. `2x + 4y + 6z`) to see it evaluated.")
    labels = [label for label, _ in plot_items]
    for eq, info in analysed:
        color = PALETTE[labels.index(eq.text) % len(PALETTE)]
        c1, c2 = st.columns([4, 1], vertical_alignment="center")
        lhs_work, lhs_val = evaluate(eq.lhs, values)
        with c1:
            st.markdown(f'<span style="color:{color};font-weight:700">{eq.text}</span>', unsafe_allow_html=True)
            working = f"{sp.latex(eq.lhs)} \\;=\\; {lhs_work} \\;=\\; \\mathbf{{{lhs_val:.6g}}}"
            if eq.has_equals:
                _, rhs_val = evaluate(eq.rhs, values)
                working += f"\\qquad \\text{{(right side }} = {rhs_val:.6g}\\text{{)}}"
            st.latex(working)
        with c2:
            residual = evaluate(info.implicit, values)[1]
            if not math.isnan(residual) and abs(residual) < 1e-9:
                st.success("On the graph", icon="✅")
            else:
                st.caption("Point is not on the graph")

coords = tuple(values[n] for n in names)
plot_items.append(("★ (" + ", ".join(f"{v:g}" for v in coords) + ")", Point("plug", "★", coords, highlight=True)))

# ----------------------------------------------------------------------------- layout

plot_col, info_col = st.columns([2.2, 1], gap="large")

with plot_col:
    try:
        fig = (figure_3d(plot_items, rng, opacity, show_axes) if is_3d else figure_2d(plot_items, rng, show_grid))
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "scrollZoom": True})
    except Exception as exc:  # keep the app alive on an unplottable expression
        st.error(f"Could not draw the graph: {exc}")
    st.caption("🖱️ Drag to rotate / pan · scroll to zoom · double-click to reset · click legend items to hide them"
               if is_3d else "🖱️ Drag to pan · scroll to zoom · double-click to reset")

with info_col:
    st.markdown("### 🔍 Analysis")
    if not plot_items:
        st.info("Enter an equation, point or vector to get started.")

    for i, (label, entry) in enumerate(plot_items):
        color = PALETTE[i % len(PALETTE)]
        if not hasattr(entry, "kind"):
            continue
        st.markdown(
            f'<div class="card"><h4 style="color:{color}">{label}'
            f'<span class="chip" style="background:{color}">{entry.kind}</span></h4></div>',
            unsafe_allow_html=True,
        )
        for name, latex in entry.facts:
            st.markdown(f"**{name}:** ${latex}$")

    points = [e for _, e in plot_items if isinstance(e, Point) and not e.highlight]
    vectors = [e for _, e in plot_items if isinstance(e, Vector)]

    if len(points) >= 2:
        st.markdown("#### 📏 Between points")
        for a, b in combinations(points, 2):
            pa, pb = np.array(a.coords), np.array(b.coords)
            dist = float(np.linalg.norm(pa - pb))
            mid = ", ".join(f"{v:g}" for v in (pa + pb) / 2)
            st.markdown(f"**{a.label}{b.label}:** distance $= {dist:.4g}$, midpoint $({mid})$")

    if len(vectors) >= 2:
        st.markdown("#### ➡️ Vector operations")
        for a, b in combinations(vectors, 2):
            va, vb = np.array(a.components, float), np.array(b.components, float)
            dot = float(va @ vb)
            na, nb = np.linalg.norm(va), np.linalg.norm(vb)
            angle = math.degrees(math.acos(max(-1.0, min(1.0, dot / (na * nb))))) if na and nb else float("nan")
            st.markdown(f"**{a.label} · {b.label}** $= {dot:g}$, angle $= {angle:.2f}^\\circ$")
            if len(va) == 3:
                cross = ", ".join(f"{v:g}" for v in np.cross(va, vb))
                st.markdown(f"**{a.label} × {b.label}** $= \\langle {cross} \\rangle$")
    for v in vectors:
        st.markdown(f"**|{v.label}|** $= {float(np.linalg.norm(v.components)):.4g}$")
