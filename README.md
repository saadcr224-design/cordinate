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

The app comes in two versions that share the same maths (`coordinate/`):

| Version | File | Use it for |
|---|---|---|
| **Web app** (Flask + Plotly.js) | `app.py` | Deploying: Vercel, Render, Railway, Heroku, Docker |
| Streamlit app | `streamlit_app.py` | Running locally, or on Streamlit Community Cloud |

```bash
# Web app (http://localhost:5000)
pip install -r requirements.txt
flask --app app run

# Streamlit app (http://localhost:8501)
pip install -r requirements-streamlit.txt
streamlit run streamlit_app.py
```

## Deploy

**Vercel**: import the repository at [vercel.com/new](https://vercel.com/new) and click *Deploy*. No settings
are needed: Vercel finds `app.py`, which exports the Flask `app`, and installs `requirements.txt`.

> Why not Streamlit on Vercel? Vercel runs Python as short-lived serverless functions, while Streamlit
> needs a long-running server with a WebSocket connection, and Streamlit with its dependencies is larger
> than Vercel's function size limit. That is why `requirements.txt` holds only the web app's dependencies.

**Render**: *New → Web Service* → connect this repo.
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`

(or choose *Docker* and Render uses the included `Dockerfile`).

**Railway / Heroku**: connect the repo; the included `Procfile` starts the web app on the platform's `$PORT`.

**Docker** (Fly.io, Google Cloud Run, a VPS, ...):

```bash
docker build -t coordinate-studio .
docker run -p 8000:8000 coordinate-studio          # then open http://localhost:8000
```

The container listens on `$PORT` (default 8000) and has a health check at `/api/health`.

**Streamlit Community Cloud**: in the app settings choose main file `streamlit_app.py`, and add
`streamlit==1.66.0` to `requirements.txt` in that deployment (it is left out on purpose for Vercel).

**Built-in protections for public use**: input is limited to 20 lines of 200 characters; expressions that
would hang the server (huge powers such as `x^999999`, power towers such as `9^9^9^9`) are rejected with a
friendly message; API requests are validated and size-limited; gunicorn stops any request running over 60 s.

## Tests

```bash
pip install -r requirements-streamlit.txt pytest
python -m pytest
```

(With only `requirements.txt` installed, the Streamlit tests are skipped automatically.)

## Project layout

```
app.py                     web app (Flask) — the entry point for Vercel and other hosts
web/index.html             the web page: Plotly.js graphs, KaTeX maths
streamlit_app.py           Streamlit version of the same app
coordinate/parser.py       turns text into equations, points, vectors and values (SymPy)
coordinate/analysis.py     classifies equations and computes their properties
coordinate/plotting.py     builds the interactive Plotly 2D / 3D figures
coordinate/service.py      shared logic used by both versions
tests/                     unit, web API and Streamlit app tests
Dockerfile, Procfile       deployment entry points
```
