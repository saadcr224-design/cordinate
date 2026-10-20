"""Build interactive Plotly figures for the 2D plane and 3D space."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
import sympy as sp

from .analysis import Analysis
from .parser import Point, Vector, x, y, z

PALETTE = ["#38bdf8", "#f472b6", "#a3e635", "#fbbf24", "#c084fc", "#fb7185", "#2dd4bf", "#f97316"]
HIGHLIGHT = "#facc15"  # the plugged-in point
AXIS_COLORS = {"x": "#ef4444", "y": "#22c55e", "z": "#3b82f6"}
SURFACE_SCALES = ["Ice", "Plotly3", "Viridis", "Sunsetdark", "Tealgrn", "Magenta", "Teal", "Oranges"]

# Arrays are sent to the browser as float32 to keep the page light (float64 doubles the payload).
F32 = np.float32

# How many numbers all shapes of one kind may send together. One shape gets full detail and many
# shapes share the budget, so a response stays well under Vercel's 4.5 MB limit however much is drawn.
BUDGET_2D_IMPLICIT = 300_000
BUDGET_3D_EXPLICIT = 150_000
BUDGET_3D_IMPLICIT = 250_000

BG = "#0b1020"
GRID = "rgba(148, 163, 184, 0.15)"
FONT = dict(family="Inter, Segoe UI, sans-serif", color="#e2e8f0")


def _lambdify(expr: sp.Expr, args):
    fn = sp.lambdify(args, expr, modules=["numpy"])

    def safe(*vals):
        with np.errstate(all="ignore"):
            out = fn(*vals)
        out = np.asarray(out, dtype=complex) if np.iscomplexobj(out) else np.asarray(out, dtype=float)
        if np.iscomplexobj(out):
            out = np.where(np.abs(out.imag) < 1e-9, out.real, np.nan)
        return np.broadcast_to(out, np.broadcast(*vals).shape).astype(float)

    return safe


# ----------------------------------------------------------------------------- 2D

def _resolution(budget: int, count: int, cost_power: int, low: int, high: int, per_point: int = 1) -> int:
    """Grid size n so that ``count`` shapes costing ``per_point * n**cost_power`` numbers each fit the budget."""
    if count <= 1:
        return high
    return int(min(high, max(low, (budget / (count * per_point)) ** (1 / cost_power))))


def _is_explicit(item, var) -> bool:
    return isinstance(item, Analysis) and item.explicit is not None and item.explicit_var == var


def figure_2d(items, rng: float, show_grid: bool = True) -> go.Figure:
    fig = go.Figure()
    implicit = sum(isinstance(item, Analysis) and item.explicit is None for _, item in items)
    n_implicit = _resolution(BUDGET_2D_IMPLICIT, implicit, 2, low=120, high=360)
    color_i = 0
    for label, item in items:
        color = PALETTE[color_i % len(PALETTE)]
        color_i += 1
        if isinstance(item, Analysis):
            _add_curve_2d(fig, item, label, color, rng, n_implicit)
        elif isinstance(item, Point):
            px, py = item.coords[:2]
            if item.highlight:
                color = HIGHLIGHT
            fig.add_trace(go.Scatter(
                x=[px, px, None, 0, px], y=[0, py, None, py, py], mode="lines",
                line=dict(color=color, width=1, dash="dot"), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter(
                x=[px], y=[py], mode="markers+text", name=label,
                marker=dict(size=20 if item.highlight else 12, color=color, symbol="star" if item.highlight else "circle",
                            line=dict(color="white", width=2)),
                text=[f"{item.label}({px:g}, {py:g})"], textposition="top right",
                textfont=dict(color=color, size=13),
                hovertemplate=f"{item.label}<br>x=%{{x}}<br>y=%{{y}}<extra></extra>"))
        elif isinstance(item, Vector):
            vx, vy = item.components[:2]
            fig.add_annotation(x=vx, y=vy, ax=0, ay=0, xref="x", yref="y", axref="x", ayref="y",
                               showarrow=True, arrowhead=3, arrowsize=1.4, arrowwidth=3, arrowcolor=color)
            fig.add_trace(go.Scatter(
                x=[vx], y=[vy], mode="text", name=label, text=[f"{item.label}⟨{vx:g}, {vy:g}⟩"],
                textposition="top center", textfont=dict(color=color, size=13),
                hovertemplate=f"{item.label}<br>|v| = {np.hypot(vx, vy):.4g}<extra></extra>"))

    axis = dict(
        range=[-rng, rng], showgrid=show_grid, gridcolor=GRID, zeroline=True, zerolinewidth=2,
        dtick=_nice_step(rng), minor=dict(showgrid=show_grid, gridcolor="rgba(148,163,184,0.06)"),
        tickfont=dict(color="#94a3b8"), showline=False,
    )
    fig.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG, font=FONT, height=680, margin=dict(l=10, r=10, t=30, b=10),
        # The x-axis is drawn by the y = 0 zero line and vice versa.
        xaxis=dict(axis, zerolinecolor=AXIS_COLORS["y"], title=dict(text="x", font=dict(color=AXIS_COLORS["x"]))),
        yaxis=dict(axis, zerolinecolor=AXIS_COLORS["x"], scaleanchor="x", scaleratio=1,
                   title=dict(text="y", font=dict(color=AXIS_COLORS["y"]))),
        legend=dict(bgcolor="rgba(15,23,42,0.7)", bordercolor="#334155", borderwidth=1, x=0.01, y=0.99),
        hoverlabel=dict(bgcolor="#1e293b", font=dict(color="white")),
        dragmode="pan",
    )
    return fig


def _add_curve_2d(fig: go.Figure, info: Analysis, label: str, color: str, rng: float, n_implicit: int) -> None:
    line = dict(color=color, width=3.5)
    if info.explicit is not None and info.explicit_var == y:
        xs = np.linspace(-rng * 1.5, rng * 1.5, 3000)
        ys = _lambdify(info.explicit, x)(xs)
        ys[np.abs(ys) > rng * 50] = np.nan
        # Break the line at vertical asymptotes instead of joining them.
        jumps = np.abs(np.diff(ys)) > rng * 2
        ys[1:][jumps] = np.nan
        fig.add_trace(go.Scatter(x=xs.astype(F32), y=ys.astype(F32), mode="lines", name=label, line=line,
                                 hovertemplate="x=%{x:.3f}<br>y=%{y:.3f}<extra></extra>"))
    elif info.explicit is not None and info.explicit_var == x:
        x0 = float(info.explicit)
        fig.add_trace(go.Scatter(x=[x0, x0], y=[-rng * 1.5, rng * 1.5], mode="lines", name=label, line=line))
    else:
        grid = np.linspace(-rng * 1.2, rng * 1.2, n_implicit)
        gx, gy = np.meshgrid(grid, grid)
        values = _lambdify(info.implicit, (x, y))(gx, gy)
        fig.add_trace(go.Contour(
            x=grid.astype(F32), y=grid.astype(F32), z=values.astype(F32), name=label, showlegend=True, showscale=False,
            contours=dict(start=0, end=0, size=1, coloring="lines"),
            colorscale=[[0, color], [1, color]], line=dict(width=3.5), hoverinfo="skip"))


def _nice_step(rng: float) -> float:
    raw = rng / 5
    mag = 10 ** np.floor(np.log10(raw))
    for m in (1, 2, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


# ----------------------------------------------------------------------------- 3D

def figure_3d(items, rng: float, opacity: float = 0.8, show_axes: bool = True) -> go.Figure:
    fig = go.Figure()
    if show_axes:
        _add_axes_3d(fig, rng)
    explicit = sum(_is_explicit(item, z) for _, item in items)
    implicit = sum(isinstance(item, Analysis) for _, item in items) - explicit
    detail = (_resolution(BUDGET_3D_EXPLICIT, explicit, 2, low=60, high=220),
              _resolution(BUDGET_3D_IMPLICIT, implicit, 3, low=14, high=40, per_point=4))
    for i, (label, item) in enumerate(items):
        color = PALETTE[i % len(PALETTE)]
        if isinstance(item, Analysis):
            _add_surface_3d(fig, item, label, i, color, rng, opacity, detail)
        elif isinstance(item, Point):
            px, py, pz = (*item.coords, 0.0)[:3]
            if item.highlight:
                color = HIGHLIGHT
            # Dashed projection lines down to the xy-plane and onto the axes.
            fig.add_trace(go.Scatter3d(
                x=[px, px, None, px, px, None, px, 0], y=[py, py, None, py, 0, None, py, py], z=[pz, 0, None, 0, 0, None, 0, 0],
                mode="lines", line=dict(color=color, width=3, dash="dash"), hoverinfo="skip", showlegend=False))
            fig.add_trace(go.Scatter3d(
                x=[px], y=[py], z=[pz], mode="markers+text", name=label,
                marker=dict(size=10 if item.highlight else 7, color=color,
                            symbol="diamond" if item.highlight else "circle", line=dict(color="white", width=2)),
                text=[f"{item.label}({px:g}, {py:g}, {pz:g})"], textposition="top center",
                textfont=dict(color=color, size=13),
                hovertemplate=f"{item.label}<br>x=%{{x}}<br>y=%{{y}}<br>z=%{{z}}<extra></extra>"))
        elif isinstance(item, Vector):
            vx, vy, vz = (*item.components, 0.0)[:3]
            length = float(np.sqrt(vx * vx + vy * vy + vz * vz)) or 1.0
            fig.add_trace(go.Scatter3d(
                x=[0, vx], y=[0, vy], z=[0, vz], mode="lines", name=label, line=dict(color=color, width=8),
                hovertemplate=f"{item.label}⟨{vx:g}, {vy:g}, {vz:g}⟩<br>|v| = {length:.4g}<extra></extra>"))
            fig.add_trace(go.Cone(
                x=[vx], y=[vy], z=[vz], u=[vx / length], v=[vy / length], w=[vz / length],
                sizemode="absolute", sizeref=rng * 0.08, anchor="tip", showscale=False,
                colorscale=[[0, color], [1, color]], hoverinfo="skip"))
            fig.add_trace(go.Scatter3d(
                x=[vx], y=[vy], z=[vz], mode="text", text=[f"{item.label}"], textposition="top center",
                textfont=dict(color=color, size=14), showlegend=False, hoverinfo="skip"))

    axis = dict(range=[-rng, rng], backgroundcolor="rgba(15,23,42,0.6)", gridcolor=GRID,
                showbackground=True, zeroline=False, tickfont=dict(color="#94a3b8"))
    fig.update_layout(
        paper_bgcolor=BG, font=FONT, height=720, margin=dict(l=0, r=0, t=30, b=0),
        scene=dict(
            xaxis=dict(axis, title=dict(text="X", font=dict(color=AXIS_COLORS["x"], size=16))),
            yaxis=dict(axis, title=dict(text="Y", font=dict(color=AXIS_COLORS["y"], size=16))),
            zaxis=dict(axis, title=dict(text="Z", font=dict(color=AXIS_COLORS["z"], size=16))),
            aspectmode="cube", camera=dict(eye=dict(x=1.6, y=1.4, z=1.0)),
        ),
        legend=dict(bgcolor="rgba(15,23,42,0.7)", bordercolor="#334155", borderwidth=1, x=0.01, y=0.99),
        hoverlabel=dict(bgcolor="#1e293b", font=dict(color="white")),
    )
    return fig


def _add_axes_3d(fig: go.Figure, rng: float) -> None:
    ends = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}
    for name, (ux, uy, uz) in ends.items():
        color = AXIS_COLORS[name]
        fig.add_trace(go.Scatter3d(
            x=[-rng * ux, rng * ux], y=[-rng * uy, rng * uy], z=[-rng * uz, rng * uz],
            mode="lines", line=dict(color=color, width=5), hoverinfo="skip", showlegend=False))
        fig.add_trace(go.Cone(
            x=[rng * ux], y=[rng * uy], z=[rng * uz], u=[ux], v=[uy], w=[uz], anchor="tip",
            sizemode="absolute", sizeref=rng * 0.07, colorscale=[[0, color], [1, color]],
            showscale=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter3d(
            x=[rng * ux * 1.08], y=[rng * uy * 1.08], z=[rng * uz * 1.08], mode="text", text=[f"<b>{name.upper()}</b>"],
            textfont=dict(color=color, size=18), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter3d(x=[0], y=[0], z=[0], mode="markers+text", text=["O"], textposition="bottom left",
                               marker=dict(size=4, color="white"), textfont=dict(color="#cbd5e1"),
                               hoverinfo="skip", showlegend=False))


def _add_surface_3d(fig, info: Analysis, label, i, color, rng, opacity, detail: tuple[int, int]) -> None:
    scale = SURFACE_SCALES[i % len(SURFACE_SCALES)]
    if info.explicit is not None and info.explicit_var == z:
        grid = np.linspace(-rng, rng, detail[0])
        gx, gy = np.meshgrid(grid, grid)
        gz = _lambdify(info.explicit, (x, y))(gx, gy)
        gz[(gz < -rng) | (gz > rng)] = np.nan  # clip to the visible cube
        fig.add_trace(go.Surface(
            x=grid.astype(F32), y=grid.astype(F32), z=gz.astype(F32), name=label, showlegend=True, showscale=False,
            opacity=opacity,
            colorscale=scale, cmin=-rng, cmax=rng,
            lighting=dict(ambient=0.55, diffuse=0.8, specular=0.35, roughness=0.5, fresnel=0.2),
            lightposition=dict(x=100, y=200, z=1000),
            contours=dict(z=dict(show=True, usecolormap=True, project_z=False, width=1)),
            hovertemplate="x=%{x:.2f}<br>y=%{y:.2f}<br>z=%{z:.2f}<extra>" + label + "</extra>"))
    else:
        grid = np.linspace(-rng, rng, detail[1])
        gx, gy, gz = np.meshgrid(grid, grid, grid, indexing="ij")
        values = _lambdify(info.implicit, (x, y, z))(gx, gy, gz)
        fig.add_trace(go.Isosurface(
            x=gx.ravel().astype(F32), y=gy.ravel().astype(F32), z=gz.ravel().astype(F32),
            value=values.ravel().astype(F32), isomin=0, isomax=0,
            surface_count=1, caps=dict(x_show=False, y_show=False, z_show=False), name=label,
            showlegend=True, showscale=False, opacity=opacity, colorscale=[[0, color], [1, color]],
            lighting=dict(ambient=0.5, diffuse=0.85, specular=0.4, roughness=0.4),
            hovertemplate="x=%{x:.2f}<br>y=%{y:.2f}<br>z=%{z:.2f}<extra>" + label + "</extra>"))

    if info.kind == "Plane":
        _add_plane_intercepts(fig, info, color, rng)


def _add_plane_intercepts(fig, info: Analysis, color, rng) -> None:
    pts = []
    for var, idx in ((x, 0), (y, 1), (z, 2)):
        others = {v: 0 for v in (x, y, z) if v != var}
        sol = sp.solve(info.implicit.subs(others), var)
        if len(sol) == 1 and sol[0].is_number and abs(float(sol[0])) <= rng:
            p = [0.0, 0.0, 0.0]
            p[idx] = float(sol[0])
            pts.append(p)
    if not pts:
        return
    xs, ys, zs = zip(*pts)
    fig.add_trace(go.Scatter3d(
        x=xs, y=ys, z=zs, mode="markers+text", showlegend=False,
        marker=dict(size=6, color=color, symbol="diamond", line=dict(color="white", width=1)),
        text=[f"({a:g}, {b:g}, {c:g})" for a, b, c in pts], textposition="top center",
        textfont=dict(color="#f8fafc", size=12),
        hovertemplate="intercept<br>(%{x}, %{y}, %{z})<extra></extra>"))
