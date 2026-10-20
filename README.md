# 📐 Coordinate Studio

An interactive **2D and 3D coordinate system** app written in Python.
Type equations, points and vectors, and see them drawn in a rotatable 3D space or on a 2D plane —
together with an automatic analysis and a step-by-step calculator.

## Features

- **3D Space** — planes, spheres and any surface (`z = f(x, y)` or implicit `F(x, y, z) = c`), with
  coloured X / Y / Z axes, realistic lighting, intercept markers, points with projection lines and vector arrows.
  Drag to rotate, scroll to zoom.
- **2D Plane** — lines, parabolas, circles, conics, trig curves, points and vectors on a grid.
- **Analysis** for every equation:
  - line → slope, intercepts, angle, distance from origin
  - plane → normal vector, unit normal, intercepts, distance from origin
  - circle / sphere → centre, radius, area / volume
  - parabola → vertex, roots, derivative
- **Plug in numbers** — enter x, y, z in the boxes, or type a line like `x = 1, y = 2, z = 3`, and see
  e.g. `2x + 4y + 6z = 2·(1) + 4·(2) + 6·(3) = 28`, whether the point lies on the graph, and the point ★ drawn on it.
- Distance and midpoint between points; dot product, cross product and angle between vectors.

## Input syntax (one item per line)

| You type | Meaning |
|---|---|
| `2x + 4y + 6z = 12` | plane |
| `2x + 4y + 6z` | same as `2x + 4y + 6z = 0` |
| `z = x^2 - y^2` or `x^2 - y^2` | surface `z = f(x, y)` |
| `x^2 + y^2 + z^2 = 9` | sphere |
| `y = 2x + 1`, `2x + 4y = 8`, `x^2 + y^2 = 16` | 2D curves |
| `x = 1, y = 2, z = 3` | numbers to plug in (a single `x = 1` is still the plane / line x = 1) |
| `A(1, 2, 3)` or `(1, 2)` | point |
| `<1, 2, 3>` or `v = <1, 2>` | vector from the origin |
| `sin cos tan sqrt exp ln abs`, `pi` | functions and constants |
| `# ...` | comment |

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser at http://localhost:8501.

## Deploy

The app is ready for any platform that runs Python or Docker. Versions are pinned in
`requirements.txt` (Python 3.11 – 3.13 supported, 3.12 recommended via `.python-version`).

**Streamlit Community Cloud** (free, easiest): go to [share.streamlit.io](https://share.streamlit.io),
click *Create app*, pick this repository, branch `main` and main file `app.py`, then *Deploy*.

**Render**: *New → Web Service* → connect this repo.
- Build command: `pip install -r requirements.txt`
- Start command: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`

Or choose *Docker* as the runtime and Render uses the included `Dockerfile`.

**Railway / Heroku**: connect the repo; the included `Procfile` starts the app on the platform's `$PORT`.

**Docker** (Fly.io, Google Cloud Run, Hugging Face Spaces, a VPS, ...):

```bash
docker build -t coordinate-studio .
docker run -p 8501:8501 coordinate-studio          # then open http://localhost:8501
```

The container listens on `$PORT` (default 8501) and exposes a health check at `/_stcore/health`.

**Built-in protections for public use**: input is limited to 20 lines of 200 characters, and expressions that
would hang the server (huge powers such as `x^999999`, power towers such as `9^9^9^9`) are rejected
with a friendly message. Results are cached, the developer menu is hidden and tracebacks are not shown to visitors.

## Tests

```bash
pip install pytest
python -m pytest
```

## Project layout

```
app.py                  Streamlit user interface
coordinate/parser.py    turns text into equations, points and vectors (SymPy)
coordinate/analysis.py  classifies equations and computes their properties
coordinate/plotting.py  builds the interactive Plotly 2D / 3D figures
tests/                  unit tests + headless app tests (streamlit AppTest)
Dockerfile, Procfile    deployment entry points
```
