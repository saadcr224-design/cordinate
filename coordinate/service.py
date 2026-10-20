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

from .analysis import Analysis, analyse_2d, analyse_3d, num
from .parser import Axis, Equation, Point, Vector, parse_lines
from .plotting import PALETTE, figure_2d, figure_3d

# What the box shows the first time: the axes themselves, explained in plain English.
STARTING_TEXT = {"3d": "x\ny\nz", "2d": "x\ny"}


@dataclass(frozen=True)
class Prepared:
    errors: list[str]
    warnings: list[str]
    plot_items: list[tuple[str, object]]   # (label, Analysis | Point | Vector | Axis) in input order


@lru_cache(maxsize=256)
def prepare(text: str, is_3d: bool) -> Prepared:
    """Parse and analyse the input. Cached, so changing a slider does not redo the maths."""
    items, errors = parse_lines(text)
    warnings, plot_items = [], []
    for item in items:
        if isinstance(item, Equation):
            try:
                info = analyse_3d(item) if is_3d else analyse_2d(item)
            except ValueError as exc:
                warnings.append(f"'{item.text}' {exc}")
                continue
            except Exception:  # never let one odd equation take the whole page down
                warnings.append(f"'{item.text}' could not be analysed")
                continue
            plot_items.append((item.text, info))
        elif not is_3d and isinstance(item, Axis) and item.name == "z":
            warnings.append("The Z axis only exists in 3D — switch to 3D Space to see it")
        elif not is_3d and len(getattr(item, "coords", getattr(item, "components", ()))) == 3:
            warnings.append(f"'{item.text}' has 3 numbers — switch to 3D Space to plot it")
        else:
            plot_items.append((item.text, item))
    return Prepared(errors, warnings, plot_items)


def build_figure(text: str, is_3d: bool, rng: float, opacity: float, show_extra: bool):
    items = prepare(text, is_3d).plot_items
    return figure_3d(items, rng, opacity, show_extra) if is_3d else figure_2d(items, rng, show_extra)


@lru_cache(maxsize=32)
def figure_json(text: str, is_3d: bool, rng: float, opacity: float, show_extra: bool) -> str:
    return build_figure(text, is_3d, rng, opacity, show_extra).to_json()


def _colors(prep: Prepared) -> dict[str, str]:
    return {label: PALETTE[i % len(PALETTE)] for i, (label, _) in enumerate(prep.plot_items)}


_AXIS_COLORS = {"x": "#ef4444", "y": "#22c55e", "z": "#3b82f6"}
_MOVES = {"x": ("to the right", "to the left"), "y": ("up", "down"), "z": ("towards you", "away from you")}


def _coords(values) -> str:
    return "(" + ", ".join(num(v) for v in values) + ")"


def _explain_axis(axis: Axis, is_3d: bool) -> list[str]:
    others = [n for n in ("xyz" if is_3d else "xy") if n != axis.name]
    direction = {"x": "left to right (horizontal)", "y": "up and down (vertical)",
                 "z": "towards you and away from you"}[axis.name]
    return [f"This is the {axis.name.upper()} axis. It runs {direction}.",
            f"Every point on it has {' and '.join(f'{n} = 0' for n in others)}.",
            {"x": "Numbers on it get bigger as you go to the right.",
             "y": "Numbers on it get bigger as you go up.",
             "z": "Numbers on it get bigger as they come towards you."}[axis.name]]


def _explain_point(point: Point) -> list[str]:
    names = "xyz"[: len(point.coords)]
    sentences = [f"Point {point.label} is at " + ", ".join(f"{n} = {num(v)}" for n, v in zip(names, point.coords)) + "."]
    moves = [f"{num(abs(v))} {_MOVES[n][0] if v > 0 else _MOVES[n][1]}" for n, v in zip(names, point.coords) if v != 0]
    centre = "(0, 0, 0)" if len(point.coords) == 3 else "(0, 0)"
    if moves:
        sentences.append(f"To reach it, start at the centre {centre} and go "
                         + (moves[0] if len(moves) == 1 else ", ".join(moves[:-1]) + " and " + moves[-1]) + ".")
    else:
        sentences.append("This is the centre point, where the axes meet (the origin).")
    return sentences


def _explain_vector(vector: Vector) -> list[str]:
    length = float(np.linalg.norm(vector.components))
    centre = "(0, 0, 0)" if len(vector.components) == 3 else "(0, 0)"
    return [f"Vector {vector.label} is an arrow from the centre {centre} to {_coords(vector.components)}.",
            f"Its length is {num(length)}."]


def explanations(prep: Prepared, is_3d: bool) -> list[dict]:
    """A plain-English explanation of everything typed, in the order it was typed."""
    colors = _colors(prep)
    cards = []
    for label, entry in prep.plot_items:
        if isinstance(entry, Analysis):
            kind, sentences, color = entry.kind, entry.sentences, colors[label]
        elif isinstance(entry, Axis):
            kind, sentences, color = "Axis", _explain_axis(entry, is_3d), _AXIS_COLORS[entry.name]
        elif isinstance(entry, Point):
            kind, sentences, color = "Point", _explain_point(entry), colors[label]
        else:
            kind, sentences, color = "Vector (arrow)", _explain_vector(entry), colors[label]
        cards.append({"label": label, "kind": kind, "color": color, "sentences": sentences})
    return cards


def measurements(prep: Prepared) -> list[str]:
    """Plain-English facts about pairs: distances between points and angles between vectors."""
    points = [e for _, e in prep.plot_items if isinstance(e, Point)]
    vectors = [e for _, e in prep.plot_items if isinstance(e, Vector)]
    sentences = []
    for a, b in combinations(points, 2):
        pa, pb = np.array(a.coords, float), np.array(b.coords, float)
        if len(pa) == len(pb):
            sentences.append(f"The distance from {a.label} to {b.label} is {num(np.linalg.norm(pa - pb))}. "
                             f"Halfway between them is {_coords((pa + pb) / 2)}.")
    for a, b in combinations(vectors, 2):
        va, vb = np.array(a.components, float), np.array(b.components, float)
        na, nb = np.linalg.norm(va), np.linalg.norm(vb)
        if len(va) == len(vb) and na and nb:
            angle = math.degrees(math.acos(max(-1.0, min(1.0, float(va @ vb) / (na * nb)))))
            sentences.append(f"The angle between {a.label} and {b.label} is {num(angle)}°.")
    return sentences
