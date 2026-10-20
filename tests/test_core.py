import pytest
import sympy as sp

from coordinate.analysis import PLANE, analyse_2d, analyse_3d
from coordinate.parser import Axis, Equation, ParseError, Point, Vector, parse_line, parse_lines, x, y, z
from coordinate.plotting import figure_2d, figure_3d


def said(info):
    return " ".join(info.sentences)


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


def test_plane_analysis():
    info = analyse_3d(parse_line("2x + 4y + 6z = 12"))
    assert info.kind == PLANE
    assert "crosses the X axis at x = 6, the Y axis at y = 3 and the Z axis at z = 2" in said(info)


def test_sphere_analysis():
    info = analyse_3d(parse_line("x^2 + y^2 + z^2 - 2x = 8"))
    assert info.kind == "Sphere (ball)"
    assert "centre is at (1, 0, 0)" in said(info) and "radius" in said(info) and "is 3." in said(info)


def test_surface_without_equals_is_z_of_xy():
    info = analyse_3d(parse_line("x^2 - y^2"))
    assert info.explicit_var == z and info.explicit == x ** 2 - y ** 2


def test_line_analysis():
    info = analyse_2d(parse_line("2x + 4y = 8"))
    assert info.kind == "Straight line"
    assert "crosses the X axis at x = 4 and the Y axis at y = 2" in said(info)
    assert "goes down 0.5" in said(info)


def test_circle_and_parabola():
    assert analyse_2d(parse_line("x^2 + y^2 = 16")).kind == "Circle"
    para = analyse_2d(parse_line("y = x^2 - 4x + 3"))
    assert para.kind == "Parabola (U shape)"
    assert "lowest point is at (2, -1)" in said(para)
    assert "crosses the X axis at x = 1 and x = 3" in said(para)


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


def test_value_lines_are_not_supported():
    # The "plug in numbers" feature was removed: "x = 1, y = 2" is no longer special.
    with pytest.raises(ParseError):
        parse_line("x = 1, y = 2, z = 3")
    # A single assignment is still an equation (the plane / line x = 1).
    assert isinstance(parse_line("x = 1"), Equation)


@pytest.mark.parametrize("bad", ["x^999999", "9^9^9^9", "((x^20)^20)^20", "1/0", "log(0)", "99999999999999999999"])
def test_rejects_expensive_or_undefined_input(bad):
    with pytest.raises(ParseError):
        parse_line(bad)


def test_input_limits():
    _, errors = parse_lines("x + y = 1\n" * 30)
    assert any("first" in e for e in errors)
    _, errors = parse_lines("x + " * 100 + "1")
    assert errors


def test_non_polynomial_curve_is_still_analysed():
    info = analyse_2d(parse_line("y = sin(x) + x"))
    assert info.explicit is not None and "crosses the X axis" not in said(info)
    assert analyse_2d(parse_line("y = x^3 - x")).sentences


@pytest.mark.parametrize("text", ["0 = 0", "1 = 2"])
def test_equations_without_variables(text):
    with pytest.raises(ValueError):
        analyse_2d(parse_line(text))
    with pytest.raises(ValueError):
        analyse_3d(parse_line(text))



def test_3d_view_has_y_up_and_labelled_axes():
    fig = figure_3d([("A", parse_line("A(1, 2, 3)"))], 10)
    camera = fig.layout.scene.camera
    assert (camera.up.x, camera.up.y, camera.up.z) == (0, 1, 0)  # Y points up, as in the 2D view
    assert camera.projection.type == "orthographic"
    texts = {t for trace in fig.data if trace.text for t in trace.text}
    assert {"<b>+X</b>", "<b>+Y</b>", "<b>+Z</b>"} <= texts


def test_2d_view_labels_positive_axes():
    fig = figure_2d([("A", parse_line("A(1, 2)"))], 8)
    assert {"<b>+X</b>", "<b>+Y</b>"} <= {a.text for a in fig.layout.annotations}


@pytest.mark.parametrize("text, name", [("x", "x"), ("Y", "y"), ("z", "z"), ("x axis", "x"), ("the Y-axis", "y")])
def test_axis_lines(text, name):
    item = parse_line(text)
    assert isinstance(item, Axis) and item.name == name


def test_axis_is_drawn_horizontal_or_vertical():
    fig = figure_2d([("x", parse_line("x")), ("y", parse_line("y"))], 8)
    x_axis, y_axis = [t for t in fig.data if t.name in ("x", "y")]
    assert set(x_axis.y) == {0} and len(set(x_axis.x)) == 2  # horizontal
    assert set(y_axis.x) == {0} and len(set(y_axis.y)) == 2  # vertical


@pytest.mark.parametrize("text, words", [
    ("x = 3", "vertical line"), ("y = 2", "horizontal line"), ("y = 2x", "passes through the centre point (0, 0)"),
    ("x^2 + 4y^2 = 16", "oval"), ("x^2 - y^2 = 4", "hyperbola"), ("y = x^2 + 1", "never crosses the X axis"),
    ("xy = 1", "curved shape"),
])
def test_2d_explanations(text, words):
    assert words in said(analyse_2d(parse_line(text)))


@pytest.mark.parametrize("text, words", [
    ("x = 3", "never crosses the Y and Z axes"), ("2x + 4y = 0", "The Z axis lies inside it"),
    ("z = x^2 - y", "For every x and y, the surface is at z = x^2 - y"),
])
def test_3d_explanations(text, words):
    assert words in said(analyse_3d(parse_line(text)))
