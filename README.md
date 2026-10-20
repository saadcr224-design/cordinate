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
tests/                  unit tests
```
