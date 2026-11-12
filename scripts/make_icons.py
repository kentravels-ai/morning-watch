#!/usr/bin/env python3
"""Draw the Morning Watch icon: a dot-matrix globe on black with two glowing alert dots.

Run once by hand (not part of the daily task):
    python scripts/make_icons.py path/to/land-110m.json
land-110m.json comes from https://cdn.jsdelivr.net/npm/world-atlas@2.0.2/land-110m.json
Writes favicon.svg, favicon.ico, apple-touch-icon.png, icon-192.png, icon-512.png
and icon-maskable-512.png to the repo root. Needs Pillow.
"""
import json
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
LON0, LAT0 = -45.0, 24.0          # globe centre: Americas, Atlantic, Europe and Africa
LAND = "#6f8bb0"
ALERTS = [(-121.0, 37.5, "#ff9f1a"),   # amber: the California coast (home)
          (36.0, 33.0, "#ff3b3b")]     # red: eastern Mediterranean / Middle East


def load_rings(path):
    topo = json.loads(Path(path).read_text(encoding="utf-8"))
    sx, sy = topo["transform"]["scale"]
    tx, ty = topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx; y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(ids):
        out = []
        for i in ids:
            pts = arcs[i] if i >= 0 else arcs[~i][::-1]
            out.extend(pts if not out else pts[1:])
        return out

    rings = []
    for g in topo["objects"]["land"]["geometries"]:
        polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        for poly in polys:
            rings.extend(ring(r) for r in poly)
    return rings


def on_land(lon, lat, rings):
    if lat < -60:
        return False
    inside = False
    for r in rings:
        j = len(r) - 1
        for i in range(len(r)):
            xi, yi = r[i]; xj, yj = r[j]
            if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
                inside = not inside
            j = i
    return inside


def inverse(x, y):
    """Unit-disk point (y up) -> lon, lat, cos(c) for an orthographic globe."""
    p0, l0 = math.radians(LAT0), math.radians(LON0)
    rho = math.hypot(x, y)
    if rho == 0:
        return LON0, LAT0, 1.0
    c = math.asin(min(1.0, rho))
    lat = math.asin(math.cos(c) * math.sin(p0) + y * math.sin(c) * math.cos(p0) / rho)
    lon = l0 + math.atan2(x * math.sin(c), rho * math.cos(c) * math.cos(p0) - y * math.sin(c) * math.sin(p0))
    return math.degrees(lon), math.degrees(lat), math.cos(c)


def forward(lon, lat):
    p0, l0 = math.radians(LAT0), math.radians(LON0)
    p, l = math.radians(lat), math.radians(lon)
    x = math.cos(p) * math.sin(l - l0)
    y = math.cos(p0) * math.sin(p) - math.sin(p0) * math.cos(p) * math.cos(l - l0)
    return x, y


def design(n, rings):
    """Return dots for an n-across grid, in a 0..1 square. Globe radius 0.44 at the centre."""
    R, step = 0.44, 0.88 / n
    dots = []
    for j in range(n + 1):
        for i in range(n + 1):
            x = -1 + (i + 0.5) * 2 / (n + 1)
            y = 1 - (j + 0.5) * 2 / (n + 1)
            if x * x + y * y > 0.97:
                continue
            lon, lat, cc = inverse(x, y)
            if on_land(lon, lat, rings):
                r = step * 0.36 * (0.55 + 0.45 * math.sqrt(cc))
                dots.append((0.5 + x * R, 0.5 - y * R, r))
    alerts = []
    for lon, lat, col in ALERTS:
        x, y = forward(lon, lat)
        alerts.append((0.5 + x * R, 0.5 - y * R, col))
    return dots, alerts, R, step


def svg(n, rings):
    dots, alerts, R, step = design(n, rings)
    s = 100
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {s} {s}">',
           '<defs><radialGradient id="g"><stop offset="0" stop-color="#fff" stop-opacity=".9"/>'
           '<stop offset=".25" stop-color="currentColor" stop-opacity=".85"/>'
           '<stop offset="1" stop-color="currentColor" stop-opacity="0"/></radialGradient></defs>',
           f'<rect width="{s}" height="{s}" rx="22" fill="#000"/>',
           f'<circle cx="50" cy="50" r="{R*s+3:.1f}" fill="#0a1220" stroke="#22324a" stroke-width="1.2"/>']
    out += [f'<circle cx="{x*s:.2f}" cy="{y*s:.2f}" r="{r*s:.2f}" fill="{LAND}"/>' for x, y, r in dots]
    for x, y, col in alerts:
        out.append(f'<circle cx="{x*s:.2f}" cy="{y*s:.2f}" r="{step*s*1.9:.2f}" fill="url(#g)" color="{col}"/>')
        out.append(f'<circle cx="{x*s:.2f}" cy="{y*s:.2f}" r="{step*s*0.55:.2f}" fill="{col}"/>')
    out.append("</svg>")
    return "\n".join(out)


def png(size, n, rings, rounded=False, pad=0.0):
    k = 4                                   # supersample
    S = size * k
    dots, alerts, R, step = design(n, rings)
    inner = 1 - 2 * pad

    def P(v):
        return (pad + v * inner) * S

    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.22), fill="#000")
    else:
        d.rectangle([0, 0, S, S], fill="#000")
    rr = (R + 0.03) * inner * S
    d.ellipse([S/2 - rr, S/2 - rr, S/2 + rr, S/2 + rr], fill="#0a1220", outline="#22324a", width=max(1, int(S * 0.012)))
    for x, y, r in dots:
        r *= inner * S
        d.ellipse([P(x) - r, P(y) - r, P(x) + r, P(y) + r], fill=LAND)
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    for x, y, col in alerts:
        r = step * 2.0 * inner * S
        g.ellipse([P(x) - r, P(y) - r, P(x) + r, P(y) + r], fill=col)
    glow = glow.filter(ImageFilter.GaussianBlur(step * 1.5 * inner * S))
    img = Image.alpha_composite(Image.alpha_composite(img, glow), glow)
    d = ImageDraw.Draw(img)
    for x, y, col in alerts:
        r = step * 0.75 * inner * S
        d.ellipse([P(x) - r, P(y) - r, P(x) + r, P(y) + r], fill=col)
        r *= 0.35
        d.ellipse([P(x) - r, P(y) - r, P(x) + r, P(y) + r], fill="#ffffffcc")
    return img.resize((size, size), Image.LANCZOS)


def main():
    rings = load_rings(sys.argv[1])
    (ROOT / "favicon.svg").write_text(svg(26, rings), encoding="utf-8")
    png(512, 34, rings).save(ROOT / "icon-512.png")
    png(512, 34, rings, pad=0.10).save(ROOT / "icon-maskable-512.png")
    png(192, 26, rings).save(ROOT / "icon-192.png")
    png(180, 26, rings).save(ROOT / "apple-touch-icon.png")
    small = [png(sz, n, rings, rounded=True) for sz, n in ((16, 9), (32, 14), (48, 18))]
    small[2].save(ROOT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)], append_images=small[:2])
    print("icons written")


if __name__ == "__main__":
    main()
