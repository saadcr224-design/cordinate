"""Turn user text such as ``2x + 4y + 6z = 12`` or ``A(1, 2, 3)`` into SymPy objects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor,
    implicit_multiplication_application,
    parse_expr,
    standard_transformations,
)

x, y, z = sp.symbols("x y z", real=True)
SYMBOLS = {"x": x, "y": y, "z": z}

_FUNCTIONS = {
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "sqrt": sp.sqrt, "exp": sp.exp, "log": sp.log, "ln": sp.log,
    "abs": sp.Abs, "pi": sp.pi, "e": sp.E,
}
_LOCALS = {**SYMBOLS, **_FUNCTIONS}
_TRANSFORMS = standard_transformations + (implicit_multiplication_application, convert_xor)

# Only maths characters are allowed through to the SymPy parser.
_SAFE = re.compile(r"^[0-9a-zA-Z\s\.\+\-\*/\^\(\)=,]*$")
_WORD = re.compile(r"[a-zA-Z_]+")
_POINT = re.compile(r"^\s*([A-Za-z]\w*)?\s*\(\s*([^()]*)\)\s*$")
_VECTOR = re.compile(r"^\s*([A-Za-z]\w*)?\s*(?:=\s*)?<\s*([^<>]*)>\s*$")

_REPLACEMENTS = {"−": "-", "–": "-", "×": "*", "·": "*", "÷": "/", "²": "^2", "³": "^3", "π": "pi"}


class ParseError(ValueError):
    """Raised when the input cannot be understood."""


@dataclass
class Equation:
    text: str
    lhs: sp.Expr
    rhs: sp.Expr
    has_equals: bool

    @property
    def implicit(self) -> sp.Expr:
        """The equation rearranged as ``F(x, y, z) = 0``."""
        return sp.simplify(self.lhs - self.rhs)


@dataclass
class Point:
    text: str
    label: str
    coords: tuple[float, ...]


@dataclass
class Vector:
    text: str
    label: str
    components: tuple[float, ...]
    origin: tuple[float, ...] = field(default_factory=tuple)


def _clean(text: str) -> str:
    for old, new in _REPLACEMENTS.items():
        text = text.replace(old, new)
    return text.strip()


def parse_expression(text: str) -> sp.Expr:
    text = _clean(text)
    if not text:
        raise ParseError("Empty expression")
    if not _SAFE.match(text):
        raise ParseError(f"Unsupported character in '{text}'")
    for word in _WORD.findall(text):
        # Words are either known names or runs of x/y/z such as "xy" (= x*y).
        if word not in _LOCALS and not set(word) <= set("xyz"):
            raise ParseError(f"Unknown name '{word}' — use x, y, z, numbers and functions like sin, sqrt")
    try:
        expr = parse_expr(text, local_dict=dict(_LOCALS), transformations=_TRANSFORMS, evaluate=True)
    except Exception as exc:  # SymPy raises many different error types
        raise ParseError(f"Could not read '{text}'") from exc
    if not isinstance(expr, sp.Expr):
        raise ParseError(f"'{text}' is not a mathematical expression")
    return expr


def _parse_numbers(body: str, text: str) -> tuple[float, ...]:
    parts = [p for p in body.split(",") if p.strip()]
    if len(parts) not in (2, 3):
        raise ParseError(f"'{text}' needs 2 or 3 comma-separated numbers")
    values = []
    for part in parts:
        value = parse_expression(part)
        if value.free_symbols:
            raise ParseError(f"Coordinates in '{text}' must be numbers")
        values.append(float(value))
    return tuple(values)


def parse_line(text: str, index: int = 0) -> Equation | Point | Vector:
    """Parse one line of user input into an equation, point or vector.

    ``index`` numbers the default label (P1, v1, ...) of unnamed points and vectors.
    """
    raw = _clean(text)
    if vec := _VECTOR.match(raw):
        label = vec.group(1) or f"v{index + 1}"
        return Vector(raw, label, _parse_numbers(vec.group(2), raw))
    if (pt := _POINT.match(raw)) and "," in pt.group(2):
        label = pt.group(1) or f"P{index + 1}"
        if label in _FUNCTIONS:
            raise ParseError(f"'{raw}' looks like a function call, not a point")
        return Point(raw, label, _parse_numbers(pt.group(2), raw))

    if raw.count("=") > 1:
        raise ParseError(f"'{raw}' has more than one '='")
    if "=" in raw:
        left, right = raw.split("=")
        return Equation(raw, parse_expression(left), parse_expression(right), True)
    return Equation(raw, parse_expression(raw), sp.Integer(0), False)


def parse_lines(text: str) -> tuple[list[Equation | Point | Vector], list[str]]:
    """Parse multi-line input. Returns the parsed items and any error messages."""
    items, errors = [], []
    for i, line in enumerate(text.splitlines()):
        line = line.split("#", 1)[0]
        if not line.strip():
            continue
        kind = Vector if _VECTOR.match(_clean(line)) else Point
        try:
            items.append(parse_line(line, sum(isinstance(item, kind) for item in items)))
        except ParseError as exc:
            errors.append(f"Line {i + 1}: {exc}")
    return items, errors


def evaluate(expr: sp.Expr, values: dict[str, float]) -> tuple[str, float]:
    """Substitute values into ``expr``; return the substituted working and the result."""
    subs = {SYMBOLS[k]: v for k, v in values.items() if k in SYMBOLS}
    working = sp.latex(expr.subs({s: sp.Symbol(f"({_fmt(v)})") for s, v in subs.items()}, simultaneous=True))
    result = expr.subs(subs)
    return working, float(sp.N(result)) if result.is_number else float("nan")


def _fmt(value: float) -> str:
    return f"{value:g}"
