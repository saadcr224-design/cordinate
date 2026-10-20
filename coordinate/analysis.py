"""Classify equations (line, circle, plane, sphere, ...) and explain them in plain English."""

from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from .parser import Equation, x, y, z


PLANE = "Plane (flat surface)"


@dataclass
class Analysis:
    kind: str                       # e.g. "Straight line", "Plane (flat surface)", "Sphere (ball)"
    implicit: sp.Expr               # F such that the graph is F = 0
    explicit: sp.Expr | None = None  # f such that y = f(x) (2D) or z = f(x, y) (3D)
    explicit_var: sp.Symbol | None = None
    sentences: list[str] = field(default_factory=list)  # easy English explanation for students


def num(value) -> str:
    """A number as students write it: whole numbers stay whole, others get at most 2 decimals."""
    value = round(float(value), 2)
    return f"{value:g}" if value != 0 else "0"


def plain(expr: sp.Expr) -> str:
    """An expression written the way it is typed, e.g. x^2 - 4x + 3."""
    return sp.sstr(expr).replace("**", "^").replace("*", "")


def _polynomial(expr: sp.Expr, gens: tuple[sp.Symbol, ...]) -> sp.Poly | None:
    try:
        return sp.Poly(sp.expand(expr), *gens)
    except sp.PolynomialError:
        return None


def _quadric_sphere(poly: sp.Poly, gens: tuple[sp.Symbol, ...]):
    """Detect a(x² + y² [+ z²]) + linear terms + c = 0 and return (center, radius²)."""
    if poly.total_degree() != 2:
        return None
    a = poly.coeff_monomial(gens[0] ** 2)
    if a == 0 or any(poly.coeff_monomial(g ** 2) != a for g in gens):
        return None
    for i, gi in enumerate(gens):
        for gj in gens[i + 1:]:
            if poly.coeff_monomial(gi * gj) != 0:
                return None
    center = [-poly.coeff_monomial(g) / (2 * a) for g in gens]
    c = poly.coeff_monomial(1) / a
    r2 = sum(ci ** 2 for ci in center) - c
    return center, sp.nsimplify(r2)


def _real_roots(f: sp.Expr) -> list[float]:
    """Real roots of f(x) = 0 — exact up to degree 4, numeric above, none if f is not a polynomial.

    General ``sp.solve`` is avoided: it can fail or run for minutes on inputs like sin(x) + x.
    """
    poly = _polynomial(f, (x,))
    if poly is None or poly.degree() < 1 or poly.free_symbols - {x}:
        return []
    if poly.degree() <= 4:
        roots = [float(r) for r in sp.roots(poly, filter="R")]
        if roots or poly.degree() <= 2:
            return sorted(roots)
    return sorted({round(complex(r).real, 6) for r in poly.nroots() if abs(complex(r).imag) < 1e-9})


def _check_has_variables(implicit: sp.Expr) -> None:
    if not implicit.free_symbols:
        raise ValueError("is always true" if implicit == 0 else "has no solution — nothing to draw")


def _join(parts: list[str]) -> str:
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1]


def _point(values) -> str:
    return "(" + ", ".join(num(v) for v in values) + ")"


def analyse_2d(eq: Equation) -> Analysis:
    if z in (eq.lhs - eq.rhs).free_symbols or z in eq.lhs.free_symbols:
        raise ValueError("uses z — switch to the 3D view to plot it")

    # "2x + 3" without "=" means y = 2x + 3; "x^2 + y^2 - 9" means ... = 0.
    if not eq.has_equals and y not in eq.lhs.free_symbols:
        implicit = y - eq.lhs
    else:
        implicit = sp.expand(eq.lhs - eq.rhs)
    _check_has_variables(implicit)

    info = Analysis(kind="Curve", implicit=implicit)
    poly = _polynomial(implicit, (x, y))
    say = info.sentences.append

    # Explicit form y = f(x) when F is linear in y.
    if sp.degree(implicit, y) == 1:
        a = implicit.coeff(y, 1)
        if y not in a.free_symbols:
            info.explicit = sp.simplify(-(implicit - a * y) / a)
            info.explicit_var = y
    elif y not in implicit.free_symbols and sp.degree(implicit, x) == 1:
        info.explicit = sp.solve(implicit, x)[0]
        info.explicit_var = x

    if poly is not None and poly.total_degree() == 1:
        a, b, c = poly.coeff_monomial(x), poly.coeff_monomial(y), poly.coeff_monomial(1)
        info.kind = "Straight line"
        if b == 0:
            say("This is a straight line that goes straight up and down (a vertical line).")
            say(f"Every point on it has x = {num(-c / a)}.")
        elif a == 0:
            say("This is a straight line that goes straight left to right (a horizontal line).")
            say(f"Every point on it has y = {num(-c / b)}.")
        else:
            m = -a / b
            say("This is a straight line.")
            if c == 0:
                say("It passes through the centre point (0, 0).")
            else:
                say(f"It crosses the X axis at x = {num(-c / a)} and the Y axis at y = {num(-c / b)}.")
            say(f"Slope {num(m)}: for every 1 step to the right, the line goes "
                f"{'up' if m > 0 else 'down'} {num(abs(m))}.")
    elif poly is not None and (circle := _quadric_sphere(poly, (x, y))):
        center, r2 = circle
        if r2 > 0:
            info.kind = "Circle"
            say("This is a circle.")
            say(f"Its centre is at {_point(center)} and its radius (the distance from the centre "
                f"to the edge) is {num(sp.sqrt(r2))}.")
        elif r2 == 0:
            info.kind = "Single point"
            say(f"Only one point makes this true: {_point(center)}.")
        else:
            info.kind = "Nothing to draw"
            say("No point makes this equation true, so there is nothing to draw.")
    elif info.explicit_var == y and (p := _polynomial(info.explicit, (x,))) is not None and p.degree() == 2:
        info.kind = "Parabola (U shape)"
        f = info.explicit
        vx = sp.solve(sp.diff(f, x), x)[0]
        opens_up = p.LC() > 0
        say("This is a U-shaped curve (a parabola).")
        say(f"It opens {'upwards' if opens_up else 'downwards'}. Its {'lowest' if opens_up else 'highest'} "
            f"point is at {_point((vx, f.subs(x, vx)))}.")
    elif poly is not None and poly.total_degree() == 2 and {x, y} <= implicit.free_symbols:
        a, b = poly.coeff_monomial(x ** 2), poly.coeff_monomial(y ** 2)
        if poly.coeff_monomial(x * y) == 0 and a * b > 0:
            info.kind = "Ellipse (oval)"
            say("This is an oval shape (an ellipse), like a stretched circle.")
        elif poly.coeff_monomial(x * y) == 0 and a * b < 0:
            info.kind = "Hyperbola"
            say("This is a hyperbola: two curves that open away from each other.")
        else:
            info.kind = "Curved shape"
            say("This is a curved shape.")
        say(f"The graph shows every point (x, y) where {eq.text} is true.")
    else:
        say("This is a curve.")
        if info.explicit_var == y:
            say(f"For every x, the curve is at height y = {plain(info.explicit)}.")
        else:
            say(f"The graph shows every point (x, y) where {eq.text} is true.")

    if info.explicit_var == y and info.kind != "Straight line":
        roots = _real_roots(info.explicit)
        if roots:
            say(f"It crosses the X axis at {_join([f'x = {num(r)}' for r in roots[:6]])}.")
        elif _polynomial(info.explicit, (x,)) is not None:
            say("It never crosses the X axis.")
        y0 = info.explicit.subs(x, 0)
        if y0.is_real and y0.is_finite:
            say(f"It crosses the Y axis at y = {num(y0)}.")
    return info


def analyse_3d(eq: Equation) -> Analysis:
    # "x^2 - y^2" without "=" and without z means z = x² − y²; "2x + 4y + 6z" means ... = 0.
    if not eq.has_equals and z not in eq.lhs.free_symbols:
        implicit = z - eq.lhs
    else:
        implicit = sp.expand(eq.lhs - eq.rhs)
    _check_has_variables(implicit)

    info = Analysis(kind="Surface", implicit=implicit)
    poly = _polynomial(implicit, (x, y, z))
    say = info.sentences.append

    if sp.degree(implicit, z) == 1:
        a = implicit.coeff(z, 1)
        if z not in a.free_symbols:
            info.explicit = sp.simplify(-(implicit - a * z) / a)
            info.explicit_var = z

    if poly is not None and poly.total_degree() == 1:
        coeffs = {name: poly.coeff_monomial(v) for name, v in (("X", x), ("Y", y), ("Z", z))}
        d = poly.coeff_monomial(1)
        info.kind = PLANE
        say("This is a flat surface (a plane).")
        crossing = [name for name, c in coeffs.items() if c != 0]
        never = [name for name, c in coeffs.items() if c == 0]
        if d == 0:
            say("It passes through the centre point (0, 0, 0).")
        else:
            say("It crosses " + _join([f"the {n} axis at {n.lower()} = {num(-d / coeffs[n])}" for n in crossing]) + ".")
        if never and d == 0:
            say(f"The {_join(never)} axis{'es lie' if len(never) > 1 else ' lies'} inside it.")
        elif never:
            say(f"It never crosses the {_join(never)} {'axes' if len(never) > 1 else 'axis'} — "
                f"it runs alongside {'them' if len(never) > 1 else 'it'}.")
    elif poly is not None and (sphere := _quadric_sphere(poly, (x, y, z))):
        center, r2 = sphere
        if r2 > 0:
            info.kind = "Sphere (ball)"
            say("This is a ball shape (a sphere).")
            say(f"Its centre is at {_point(center)} and its radius (the distance from the centre "
                f"to the surface) is {num(sp.sqrt(r2))}.")
        elif r2 == 0:
            info.kind = "Single point"
            say(f"Only one point makes this true: {_point(center)}.")
        else:
            info.kind = "Nothing to draw"
            say("No point makes this equation true, so there is nothing to draw.")
    else:
        info.kind = "Curved surface"
        say("This is a curved surface.")
        if info.explicit is not None:
            say(f"For every x and y, the surface is at z = {plain(info.explicit)}.")
        else:
            say(f"It is made of every point (x, y, z) where {eq.text} is true.")
    return info
