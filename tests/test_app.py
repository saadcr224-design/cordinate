"""Run the real Streamlit script headlessly and check that no input crashes the page."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parent.parent / "app.py"

INPUTS = [
    "2x + 4y + 6z = 12\nA(1, 1, 1)\nx = 1, y = 1, z = 1",
    "x^2 + y^2 + z^2 = 16\nz = sin(x) cos(y)\n<1, 2, 3>\n<0, 1, 1>\nA(1,2,3)\nB(3,2,1)",
    "y = sin(x) + x\ny = 1/x\nx^2 + y^2 = 4\n(1, 2)\n<3, 4>\nx = 0, y = 0",
    "x^999999\n9^9^9^9\n1/0\n0 = 0\nfoo(\n(1, 2, 3, 4)",
]


def run(text: str, mode: str) -> AppTest:
    at = AppTest.from_file(str(APP), default_timeout=60).run()
    at.radio[0].set_value(mode).run()
    at.text_area[0].set_value(text).run()
    return at


@pytest.mark.parametrize("mode", ["3D Space", "2D Plane"])
@pytest.mark.parametrize("text", INPUTS)
def test_app_renders_without_exceptions(text, mode):
    at = run(text, mode)
    assert not at.exception, [e.value for e in at.exception]


def test_plug_in_values_from_text():
    at = run("2x + 4y + 6z\nx = 1, y = 2, z = 3", "3D Space")
    assert [n.value for n in at.number_input] == [1, 2, 3]
    assert any("28" in latex.value for latex in at.latex)
