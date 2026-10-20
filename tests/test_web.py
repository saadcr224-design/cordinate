"""The Flask web app (app.py) that Vercel and the other hosts run."""

import pytest

import app as web


@pytest.fixture()
def client():
    return web.app.test_client()


def post(client, **body):
    response = client.post("/api/compute", json=body)
    assert response.status_code == 200
    return response.get_json()


def test_vercel_entrypoint_exports_app():
    # Vercel's Python runtime requires a top-level "app" (or "application" / "handler") in app.py.
    from flask import Flask
    assert isinstance(web.app, Flask)


def test_page_and_health(client):
    page = client.get("/")
    assert page.status_code == 200 and b"Coordinate Studio" in page.data
    assert b"__CONFIG__" not in page.data
    assert client.get("/api/health").get_json() == {"status": "ok"}


def test_compute_3d_example(client):
    data = post(client, text="2x + 4y + 6z\nA(1, 2, 3)", mode="3d")
    assert data["explanations"][0]["kind"] == "Plane (flat surface)"
    assert "Point A is at x = 1, y = 2, z = 3" in data["explanations"][1]["sentences"][0]
    assert data["figure"]["data"] and not data["errors"]


def test_plug_in_feature_is_removed(client):
    data = post(client, text="2x + 4y + 6z", mode="3d")
    assert not {"evaluations", "values", "typedValues"} & data.keys()
    assert not any("★" in (trace.get("name") or "") for trace in data["figure"]["data"])
    page = client.get("/").data.decode()
    assert "Plug in numbers" not in page


def test_syntax_help_and_examples_are_removed(client):
    page = client.get("/").data.decode()
    assert "Syntax" not in page and "Load example" not in page and "katex" not in page


def test_typing_x_and_y_explains_the_axes(client):
    data = post(client, text="x\ny\nz", mode="2d")
    kinds = [c["kind"] for c in data["explanations"]]
    assert kinds == ["Axis", "Axis"]  # z only exists in 3D
    assert "left to right (horizontal)" in data["explanations"][0]["sentences"][0]
    assert "up and down (vertical)" in data["explanations"][1]["sentences"][0]
    assert any("only exists in 3D" in w for w in data["warnings"])


def test_compute_2d_with_points_and_vectors(client):
    data = post(client, text="y = x^2\nA(1, 1)\nB(4, 5)\n<3, 4>\n<1, 0>", mode="2d")
    assert data["explanations"][0]["kind"] == "Parabola (U shape)"
    assert any("distance from A to B is 5" in m for m in data["measurements"])
    assert any("angle between v1 and v2" in m for m in data["measurements"])


@pytest.mark.parametrize("text", ["x^999999", "9^9^9^9", "1/0", "0 = 0", "foo(", "(1,2,3,4)", "x" * 10000])
def test_bad_input_is_reported_not_crashed(client, text):
    data = post(client, text=text, mode="3d")
    assert data["errors"] or data["warnings"]


@pytest.mark.parametrize("body", [
    {"text": 5}, {"values": {"x": "nan"}, "text": "x"}, {"range": "huge", "text": "x"}, {"values": [1, 2], "text": "x"},
    {"values": {"x": 1e308}, "text": "1/x"},
])
def test_malformed_requests(client, body):
    response = client.post("/api/compute", json=body)
    assert response.status_code in (200, 400)


def test_non_json_request(client):
    assert client.post("/api/compute", data="hello").status_code == 400


@pytest.mark.parametrize("mode, text", [
    ("3d", "\n".join(f"x^2 + y^2 + z^2 = {k}" for k in range(1, 21))),
    ("3d", "\n".join([f"x^2 + y^2 + z^2 = {k}" for k in range(1, 11)] + [f"z = x^2/{k} - y" for k in range(1, 11)])),
    ("2d", "\n".join(f"x^2 + y^2 = {k}" for k in range(1, 21))),
])
def test_response_fits_vercel_limit(client, mode, text):
    # Vercel rejects function responses larger than 4.5 MB.
    response = client.post("/api/compute", json={"text": text, "mode": mode, "range": 50})
    assert response.status_code == 200
    assert len(response.data) < 3_000_000
    assert response.get_json()["figure"] is not None


def test_oversized_figure_is_dropped_with_message(client, monkeypatch):
    monkeypatch.setattr(web, "MAX_RESPONSE_BYTES", 1000)
    data = post(client, text="x^2 + y^2 + z^2 = 9", mode="3d")
    assert data["figure"] is None and "too detailed" in data["errors"][-1]
