"""Classify equations (line, circle, plane, sphere, ...) and compute their key facts."""

from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from .parser import Equation, x, y, z


@dataclass
class Analysis:
    kind: str                       # e.g. "Line", "Plane", "Sphere", "Surface"
    implicit: sp.Expr               # F such that the graph is F = 0
    explicit: sp.Expr | None = None  # f such that y = f(x) (2D) or z = f(x, y) (3D)
    explicit_var: sp.Symbol | None = None
    facts: list[tuple[str, str]] = field(default_factory=list)  # (label, LaTeX)


def _num(value: sp.Expr) -> str:
    value = sp.nsimplify(value, rational=True) if value.is_number else value
    return sp.latex(value)


def _approx(value: sp.Expr) -> str:
    """Exact value, followed by a decimal approximation when it is not a whole number."""
    value = sp.nsimplify(value)
    return _num(value) if value.is_Integer else f"{_num(value)} \\approx {float(value):.4g}"


def _eq_latex(lhs: sp.Expr, rhs: sp.Expr) -> str:
    return f"{sp.latex(lhs)} = {sp.latex(rhs)}"


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


def _real_roots(f: sp.Expr) -> list[str]:
    """LaTeX for the real roots of f(x) = 0 — exact up to degree 4, numeric above, none if not a polynomial.

    General ``sp.solve`` is avoided: it can fail or run for minutes on inputs like sin(x) + x.
    """
    poly = _polynomial(f, (x,))
    if poly is None or poly.degree() < 1 or poly.free_symbols - {x}:
        return []
    if poly.degree() <= 4:
        roots = [r for r in sp.roots(poly, filter="R")]
        if roots or poly.degree() <= 2:
            return [_num(r) for r in sorted(roots, key=float)]
    return sorted({f"{complex(r).real:.4g}" for r in poly.nroots() if abs(complex(r).imag) < 1e-9}, key=float)


def _check_has_variables(implicit: sp.Expr) -> None:
    if not implicit.free_symbols:
        raise ValueError("is always true" if implicit == 0 else "has no solution — nothing to draw")


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
        info.facts.append(("Standard form", _eq_latex(a * x + b * y, -c)))
        if b != 0:
            m, k = -a / b, -c / b
            info.facts.append(("Slope  m", _num(m)))
            info.facts.append(("y-intercept", f"(0,\\ {_num(k)})"))
            info.facts.append(("Angle with x-axis", f"{float(sp.deg(sp.atan(m))):.2f}^\\circ"))
        else:
            info.facts.append(("Slope  m", r"\text{undefined (vertical line)}"))
        if a != 0:
            info.facts.append(("x-intercept", f"({_num(-c / a)},\\ 0)"))
        info.facts.append(("Distance from origin", _approx(sp.Abs(c) / sp.sqrt(a ** 2 + b ** 2))))
    elif poly is not None and (circle := _quadric_sphere(poly, (x, y))):
        center, r2 = circle
        if r2 > 0:
            info.kind = "Circle"
            info.facts.append(("Centre", f"({_num(center[0])},\\ {_num(center[1])})"))
            info.facts.append(("Radius", _num(sp.sqrt(r2))))
            info.facts.append(("Area", _approx(sp.pi * r2)))
            info.facts.append(("Circumference", _approx(2 * sp.pi * sp.sqrt(r2))))
        else:
            info.kind = "Empty set / single point"
    elif poly is not None and poly.total_degree() == 2 and info.explicit_var == y:
        info.kind = "Parabola"
        f = info.explicit
        xv = sp.solve(sp.diff(f, x), x)
        if xv:
            info.facts.append(("Vertex", f"({_num(xv[0])},\\ {_num(f.subs(x, xv[0]))})"))
    elif poly is not None and poly.total_degree() == 2:
        info.kind = "Conic section"

    if info.explicit is not None and info.explicit_var == y:
        info.facts.insert(0, ("Explicit form", _eq_latex(y, info.explicit)))
        roots = _real_roots(info.explicit)
        if roots and info.kind != "Straight line":
            info.facts.append(("x-intercepts", ",\\ ".join(roots[:6])))
        if info.kind not in ("Straight line",):
            info.facts.append(("Derivative  dy/dx", sp.latex(sp.simplify(sp.diff(info.explicit, x)))))
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

    if sp.degree(implicit, z) == 1:
        a = implicit.coeff(z, 1)
        if z not in a.free_symbols:
            info.explicit = sp.simplify(-(implicit - a * z) / a)
            info.explicit_var = z

    if poly is not None and poly.total_degree() == 1:
        a, b, c = (poly.coeff_monomial(v) for v in (x, y, z))
        d = poly.coeff_monomial(1)
        info.kind = "Plane"
        info.facts.append(("Standard form", _eq_latex(a * x + b * y + c * z, -d)))
        info.facts.append(("Normal vector  n", f"\\langle {_num(a)},\\ {_num(b)},\\ {_num(c)} \\rangle"))
        norm = sp.sqrt(a ** 2 + b ** 2 + c ** 2)
        info.facts.append(("|n|", _approx(norm)))
        unit = [sp.nsimplify(v / norm) for v in (a, b, c)]
        info.facts.append(("Unit normal", r"\langle " + r",\ ".join(f"{float(u):.3f}" for u in unit) + r" \rangle"))
        for coeff, name in ((a, "x"), (b, "y"), (c, "z")):
            if coeff != 0:
                info.facts.append((f"{name}-intercept", _num(-d / coeff)))
        info.facts.append(("Distance from origin", _approx(sp.Abs(d) / norm)))
        angles = [float(sp.deg(sp.acos(sp.Abs(v) / norm))) for v in (a, b, c)]
        info.facts.append(("Angles of n with x, y, z axes", r",\ ".join(f"{t:.2f}^\\circ" for t in angles)))
    elif poly is not None and (sphere := _quadric_sphere(poly, (x, y, z))):
        center, r2 = sphere
        if r2 > 0:
            r = sp.sqrt(r2)
            info.kind = "Sphere"
            info.facts.append(("Centre", "(" + r",\ ".join(_num(c) for c in center) + ")"))
            info.facts.append(("Radius", _num(r)))
            info.facts.append(("Surface area", _approx(4 * sp.pi * r2)))
            info.facts.append(("Volume", _approx(sp.Rational(4, 3) * sp.pi * r ** 3)))
        else:
            info.kind = "Empty set / single point"
    elif poly is not None and poly.total_degree() == 2:
        info.kind = "Quadric surface"

    if info.explicit is not None:
        info.facts.insert(0, ("Explicit form", _eq_latex(z, info.explicit)))
        if info.kind != "Plane":
            gx, gy = sp.diff(info.explicit, x), sp.diff(info.explicit, y)
            info.facts.append(("Gradient  ∇z", f"\\langle {sp.latex(sp.simplify(gx))},\\ {sp.latex(sp.simplify(gy))} \\rangle"))
    return info
