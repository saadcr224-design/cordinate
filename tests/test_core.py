import math

import pytest
import sympy as sp

from coordinate.analysis import analyse_2d, analyse_3d
from coordinate.parser import Equation, ParseError, Point, Vector, evaluate, parse_line, parse_lines, x, y, z
from coordinate.plotting import figure_2d, figure_3d


def facts(info):
    return dict(info.facts)


def test_parses_implicit_multiplication_and_powers():
    eq = parse_line("2x + 4y + 6z = 12")
    assert isinstance(eq, Equation)
    assert sp.simplify(eq.lhs - (2 * x + 4 * y + 6 * z)) == 0
    assert parse_line("y = 3x^2").rhs == 3 * x ** 2
    assert parse_line("z = 2 sin(x)").rhs == 2 * sp.sin(x)


def test_points_and_vectors():
    p = parse_line("A(1, 2, 3)")
    assert isinstance(p, Point) and p.label == "A" and p.coords == (1, 2, 3)
    assert parse_line("(1, -2)").coords == (1, -2)
    v = parse_line("u = <3, 4>")
    assert isinstance(v, Vector) and v.label == "u" and v.components == (3, 4)


@pytest.mark.parametrize("bad", ["import os", "2x + __class__", "x == 2", "(1, 2, 3, 4)", "2x +"])
def test_rejects_bad_input(bad):
    with pytest.raises(ParseError):
        parse_line(bad)


def test_parse_lines_collects_errors():
    items, errors = parse_lines("2x + y = 1\n\n# comment\nfoo(\nA(1,2)")
    assert len(items) == 2 and len(errors) == 1


def test_evaluate_example():
    eq = parse_line("2x + 4y + 6z")
    _, value = evaluate(eq.lhs, {"x": 1, "y": 2, "z": 3})
    assert value == 28


def test_plane_analysis():
    info = analyse_3d(parse_line("2x + 4y + 6z = 12"))
    assert info.kind == "Plane"
    f = facts(info)
    assert f["x-intercept"] == "6" and f["y-intercept"] == "3" and f["z-intercept"] == "2"
    assert "2" in f["Normal vector  n"]


def test_sphere_analysis():
    info = analyse_3d(parse_line("x^2 + y^2 + z^2 - 2x = 8"))
    assert info.kind == "Sphere"
    assert facts(info)["Radius"] == "3"
    assert facts(info)["Centre"].startswith("(1")


def test_surface_without_equals_is_z_of_xy():
    info = analyse_3d(parse_line("x^2 - y^2"))
    assert info.explicit_var == z and info.explicit == x ** 2 - y ** 2


def test_line_analysis():
    info = analyse_2d(parse_line("2x + 4y = 8"))
    assert info.kind == "Straight line"
    f = facts(info)
    assert f["Slope  m"] == r"- \frac{1}{2}"
    assert f["x-intercept"] == "(4,\\ 0)"


def test_circle_and_parabola():
    assert analyse_2d(parse_line("x^2 + y^2 = 16")).kind == "Circle"
    para = analyse_2d(parse_line("y = x^2 - 4x + 3"))
    assert para.kind == "Parabola"
    assert facts(para)["Vertex"] == "(2,\\ -1)"


def test_2d_rejects_z():
    with pytest.raises(ValueError):
        analyse_2d(parse_line("x + z = 1"))


def test_figures_build():
    eqs = ["2x + 4y + 6z = 12", "x^2 + y^2 + z^2 = 9", "z = sin(x) cos(y)", "y = x^2"]
    items = [(e, analyse_3d(parse_line(e))) for e in eqs]
    items += [("A", parse_line("A(1,2,3)")), ("v", parse_line("<1,2,3>"))]
    assert len(figure_3d(items, 10).data) > len(items)

    eqs2 = ["y = 1/x", "x^2 + y^2 = 4", "x = 3", "2x + 3"]
    items2 = [(e, analyse_2d(parse_line(e))) for e in eqs2]
    items2 += [("A", parse_line("A(1,2)")), ("v", parse_line("<1,2>"))]
    assert len(figure_2d(items2, 8).data) >= len(items2)


def test_default_labels_count_per_kind():
    items, _ = parse_lines("x + y = 1\n(1, 2)\n<1, 2>\n(3, 4)\n<3, 4>")
    assert [i.label for i in items[1:]] == ["P1", "v1", "P2", "v2"]
