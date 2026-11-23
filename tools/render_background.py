#!/usr/bin/env python3
"""
Generate the static background: near-black, a very faint amber grid, and a
soft amber vignette. Rendered at full panel resolution and embedded as one
RGB565 image behind the LVGL widgets.

Run:  python3 tools/render_background.py
"""
import math
import os

from PIL import Image, ImageChops, ImageDraw

from palette import BG, AMBER

W, H = 480, 320
OUT = os.path.join(os.path.dirname(__file__), "..", "firmware", "assets", "ui-background.png")


def main():
    img = Image.new("RGB", (W, H), BG)
    px = img.load()
    cx, cy = W / 2, H / 2
    diag = math.hypot(cx, cy)

    # Edge-only vignette: flat dark center, smooth falloff to near-black at
    # the corners. No additive warm circle, so nothing reads as a center dot.
    def smoothstep(edge0, edge1, x):
        t = max(0.0, min(1.0, (x - edge0) / (edge1 - edge0)))
        return t * t * (3.0 - 2.0 * t)

    for y in range(H):
        for x in range(W):
            r = min(1.0, math.hypot(x - cx, y - cy) / diag)
            f = 1.0 - 0.55 * smoothstep(0.42, 1.0, r)
            px[x, y] = tuple(max(0, min(255, int(c * f))) for c in BG)

    # grid overlay, 16 px minor / 64 px major, drawn at very low alpha.
    # Build line masks first so crossings take the max alpha instead of
    # doubling it -- doubled crossings read as bright dots on the panel.
    minor = Image.new("L", (W, H), 0)
    major = Image.new("L", (W, H), 0)
    md = ImageDraw.Draw(minor)
    Md = ImageDraw.Draw(major)
    for x in range(0, W, 16):
        (Md if x % 64 == 0 else md).line([(x, 0), (x, H)], fill=255, width=1)
    for y in range(0, H, 16):
        (Md if y % 64 == 0 else md).line([(0, y), (W, y)], fill=255, width=1)
    alpha = ImageChops.lighter(minor.point(lambda v: 9 if v else 0),
                               major.point(lambda v: 17 if v else 0))
    grid = Image.new("RGBA", (W, H), (*AMBER, 0))
    grid.putalpha(alpha)
    img = Image.alpha_composite(img.convert("RGBA"), grid).convert("RGB")

    out = os.path.abspath(OUT)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    main()
