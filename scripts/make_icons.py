"""Draw the app icon (X red horizontal, Y green vertical, Z blue diagonal) at every size a PWA needs."""
import math
import sys
from PIL import Image, ImageDraw

# Usage: python scripts/make_icons.py [output folder, default web/icons]  (needs Pillow)
OUT = sys.argv[1] if len(sys.argv) > 1 else "web/icons"
S = 1024  # draw large, then downsample for smooth edges


def gradient(size):
    top, bottom = (49, 46, 129), (11, 16, 32)
    img = Image.new("RGB", (size, size))
    d = ImageDraw.Draw(img)
    for yy in range(size):
        t = yy / (size - 1)
        d.line([(0, yy), (size, yy)], fill=tuple(int(a + (b - a) * t) for a, b in zip(top, bottom)))
    return img


def arrow(d, start, end, color, width):
    """A line ending in a triangular head whose tip is exactly at ``end``."""
    ang = math.atan2(end[1] - start[1], end[0] - start[0])
    head = width * 2.4
    base = (end[0] - head * math.cos(ang), end[1] - head * math.sin(ang))
    d.line([start, base], fill=color, width=width)
    side = head * 0.62
    left = (base[0] + side * math.sin(ang), base[1] - side * math.cos(ang))
    right = (base[0] - side * math.sin(ang), base[1] + side * math.cos(ang))
    d.polygon([end, left, right], fill=color)


def icon(scale, rounded):
    """``scale`` shrinks the drawing towards the centre (maskable icons need a safe zone)."""
    img = gradient(S).convert("RGBA")
    d = ImageDraw.Draw(img)
    c = S / 2
    L = 300 * scale
    o = (c - 0.215 * L, c + 0.25 * L)  # origin, placed so the three arrows sit centred
    w = int(44 * scale)
    arrow(d, o, (o[0] - L * 0.62, o[1] + L * 0.50), (59, 130, 246), w)    # Z: down-left, towards the viewer
    arrow(d, (o[0] - L * 0.55, o[1]), (o[0] + L * 1.05, o[1]), (239, 68, 68), w)    # X: horizontal
    arrow(d, (o[0], o[1] + L * 0.55), (o[0], o[1] - L * 1.05), (34, 197, 94), w)    # Y: vertical
    r = w * 0.9
    d.ellipse([o[0] - r, o[1] - r, o[0] + r, o[1] + r], fill=(255, 255, 255))
    if rounded:
        mask = Image.new("L", (S, S), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, S, S], radius=int(S * 0.22), fill=255)
        img.putalpha(mask)
    return img


standard = icon(1.15, rounded=True)
maskable = icon(0.78, rounded=False)    # full-bleed background, artwork inside the 80% safe zone
apple = icon(0.95, rounded=False)        # iOS rounds the corners itself
for name, img, size in [("icon-192.png", standard, 192), ("icon-512.png", standard, 512),
                        ("maskable-512.png", maskable, 512), ("apple-touch-icon.png", apple, 180),
                        ("favicon-32.png", standard, 32)]:
    img.resize((size, size), Image.LANCZOS).save(f"{OUT}/{name}", optimize=True)
    print(name, size)
