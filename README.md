# 📐 Coordinate Studio

An interactive **2D and 3D coordinate system** app written in Python.
Type equations, points, vectors or just `x`, `y`, `z`, and see them drawn in a rotatable 3D space or on a
2D plane — each one explained automatically in simple English for students.

## Features

- **3D Space** — planes, spheres and any surface (`z = f(x, y)` or implicit `F(x, y, z) = c`), shown in a
  textbook view for students: **X to the right, Y straight up, Z towards you**, with numbered, coloured axes,
  realistic lighting, intercept markers, points with guide lines to the floor and vector arrows.
  Drag to rotate, scroll to zoom.
- **2D Plane** — lines, parabolas, circles, conics, trig curves, points and vectors on a grid.
- **Explanation in simple English** for everything typed, for example:
  - `x` → "This is the X axis. It runs left to right (horizontal). Every point on it has y = 0 …"
  - `2x + 4y + 6z = 12` → "This is a flat surface (a plane). It crosses the X axis at x = 6, the Y axis at y = 3 …"
  - `y = x^2 - 4x + 3` → "This is a U-shaped curve (a parabola). It opens upwards. Its lowest point is at (2, -1) …"
  - `A(3, 4, 5)` → "To reach it, start at the centre (0, 0, 0) and go 3 to the right, 4 up and 5 towards you."
- Distances between points and angles between vectors, also in plain English.

## Install it as an app (PC, Android, iPhone)

The website is a Progressive Web App, so it can be installed and used like a normal app:

- **PC (Chrome or Edge)**: open the site and click **⬇️ Install app** in the sidebar, or the install icon at the
  right of the address bar.
- **Android (Chrome)**: tap **⬇️ Install app**, or the browser menu **⋮ → Install app**.
- **iPhone / iPad (Safari)**: tap the **Share** button, then **Add to Home Screen**.

The installed app opens in its own window with its own icon, and starts instantly. It needs the internet to
draw new graphs; when offline it opens and says so. On phones, the graph is locked while you scroll the page:
tap it to turn or zoom it, then tap **✓ Done**.

## Input syntax (one item per line)

| You type | Meaning |
|---|---|
| `x`, `y`, `z` (or `x axis`) | highlight that axis: X horizontal, Y vertical, Z towards you |
| `2x + 4y + 6z = 12` | plane |
| `2x + 4y + 6z` | same as `2x + 4y + 6z = 0` |
| `z = x^2 - y^2` or `x^2 - y^2` | surface `z = f(x, y)` |
| `x^2 + y^2 + z^2 = 9` | sphere |
| `y = 2x + 1`, `2x + 4y = 8`, `x^2 + y^2 = 16` | 2D curves |
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
web/index.html             the web page (Plotly.js graphs)
web/manifest.webmanifest   app name, icons and colours, so the site can be installed
web/sw.js                  service worker: the installed app opens instantly, even offline
web/icons/                 app icons (made by scripts/make_icons.py)
streamlit_app.py           Streamlit version of the same app
coordinate/parser.py       turns text into equations, points, vectors and values (SymPy)
coordinate/analysis.py     classifies equations and explains them in plain English
coordinate/plotting.py     builds the interactive Plotly 2D / 3D figures
coordinate/service.py      shared logic used by both versions
tests/                     unit, web API and Streamlit app tests
Dockerfile, Procfile       deployment entry points
```
