"""Coordinate Studio — an interactive 2D / 3D coordinate system.

Run with:  streamlit run streamlit_app.py

The web version for Vercel and other hosts is ``app.py``; both use ``coordinate.service``.
"""

from __future__ import annotations

import html

import streamlit as st

from coordinate.parser import MAX_LINE_LENGTH, MAX_LINES
from coordinate.service import STARTING_TEXT, build_figure, explanations, measurements, prepare

st.set_page_config(page_title="Coordinate Studio", page_icon="📐", layout="wide")

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
    .card p { margin: .35rem 0; line-height: 1.6; }
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
      <p>Type in the box below. Everything you type is drawn on the graph and explained in simple English.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------------------------------------------------------- sidebar

with st.sidebar:
    st.markdown("### ⚙️ View")
    mode = st.radio("Coordinate system", ["3D Space", "2D Plane"], horizontal=True, label_visibility="collapsed")
    is_3d = mode == "3D Space"

    rng = st.slider("Axis range  (±)", 2, 50, 10 if is_3d else 8)
    if is_3d:
        opacity = st.slider("Surface opacity", 0.2, 1.0, 0.8, 0.05)
        show_axes = st.toggle("Show coloured X / Y / Z axes", True)
    else:
        show_grid = st.toggle("Show grid", True)

# ----------------------------------------------------------------------------- input

key = f"input_{mode}"
if key not in st.session_state:
    st.session_state[key] = STARTING_TEXT["3d" if is_3d else "2d"]

text = st.text_area("Type here — one thing per line", key=key, height=130,
                    max_chars=MAX_LINES * (MAX_LINE_LENGTH + 1))


prep = prepare(text, is_3d)
for err in prep.errors:
    st.error(err, icon="⚠️")
for warning in prep.warnings:
    st.warning(warning, icon="ℹ️")

# ----------------------------------------------------------------------------- layout

plot_col, info_col = st.columns([2.2, 1], gap="large")

with plot_col:
    try:
        fig = build_figure(text, is_3d, rng, opacity if is_3d else 1.0, show_axes if is_3d else show_grid)
        st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "scrollZoom": True})
    except Exception as exc:  # keep the app alive on an unplottable expression
        st.error(f"Could not draw the graph: {exc}")
    st.caption("X → right · Y ↑ up · Z ↙ towards you  ·  🖱️ Drag to rotate · scroll to zoom · double-click to reset"
               if is_3d else "🖱️ Drag to pan · scroll to zoom · double-click to reset")

with info_col:
    st.markdown("### 💬 Explanation")
    if not prep.plot_items:
        st.info("Type something in the box to see it explained here.")

    for card in explanations(prep, is_3d):
        st.markdown(
            f'<div class="card"><h4 style="color:{card["color"]}">{html.escape(card["label"])}'
            f'<span class="chip" style="background:{card["color"]}">{card["kind"]}</span></h4>'
            + "".join(f"<p>{html.escape(sentence)}</p>" for sentence in card["sentences"]) + "</div>",
            unsafe_allow_html=True,
        )

    if sentences := measurements(prep):
        st.markdown("#### 📏 Measurements")
        for sentence in sentences:
            st.markdown(f"<p>{html.escape(sentence)}</p>", unsafe_allow_html=True)
