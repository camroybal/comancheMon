#!/usr/bin/env python3
"""
Render the Jeep Comanche turntable and the two attitude views.

The source model lives in comanche_model.py and is dimensioned from the
published MJ long-bed specs.  Outputs are 8-bit alpha masks; the firmware
recolours them amber with LVGL's image `recolor` style, so each pixel costs one
byte instead of the three an RGB565+alpha image would cost.
"""
import math
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from comanche_model import (  # noqa: E402
    SPEC, build, mask_to_rgba, render_mask, turntable_ring, view_fit,
)
from palette import AMBER, BG  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "firmware", "assets")
GAUGES = os.path.join(ASSETS, "gauges")
TRUCK = os.path.join(ASSETS, "truck")
DOCS = os.path.join(ROOT, "docs")

# Hero turntable: 120 frames = 3 degrees per frame at 24 fps for 5 seconds.
FRAMES = 120
HERO_W, HERO_H = 140, 78
HERO_ELEV = math.radians(16.0)
HERO_SS = 4
HERO_HIDDEN = 0.20
HERO_OFFSET = math.radians(30.0)

# Attitude views.  A front view is nearly square; a side view is 3:1.  Using
# the same 90x36 box for both (as the old renderer did) squashed the front.
FRONT_W, FRONT_H = 56, 48
SIDE_W, SIDE_H = 116, 40
VIEW_SS = 4


def compose(mask: Image.Image, color=AMBER) -> Image.Image:
    im = Image.new("RGBA", mask.size, (*color, 0))
    im.putalpha(mask.convert("L"))
    return im


def render_hero_frames():
    os.makedirs(TRUCK, exist_ok=True)
    model = build()
    ring = turntable_ring()
    yaws = [2 * math.pi * f / FRAMES + HERO_OFFSET for f in range(FRAMES)]
    scale, cx, cy = view_fit([model.verts, ring], yaws, HERO_W, HERO_H,
                             HERO_ELEV, margin=3.0)

    for f, yaw in enumerate(yaws):
        mask = render_mask(
            model, HERO_W, HERO_H, yaw, HERO_ELEV, scale, cx, cy,
            ss=HERO_SS, hidden_alpha=HERO_HIDDEN,
            ring_pts=ring, ring_yaw=0.0,
        )
        mask_to_rgba(mask).save(os.path.join(TRUCK, f"frame_{f:03d}.png"),
                                optimize=True)

    # 10 x 12 contact sheet.
    cols, rows = 10, 12
    sheet = Image.new("RGB", (HERO_W * cols, HERO_H * rows), BG)
    for f in range(FRAMES):
        im = Image.open(os.path.join(TRUCK, f"frame_{f:03d}.png")).convert("RGBA")
        sheet.paste(compose(im.getchannel("A")), ((f % cols) * HERO_W,
                                                 (f // cols) * HERO_H),
                    compose(im.getchannel("A")))
    sheet.save(os.path.join(DOCS, "truck-contact-sheet.png"), optimize=True)

    # A larger single hero frame for the README / design docs.
    hw, hh = 280, 156
    hs, hcx, hcy = view_fit([model.verts, ring], [HERO_OFFSET + math.radians(24)],
                            hw, hh, HERO_ELEV, margin=6.0)
    hero_mask = render_mask(model, hw, hh, HERO_OFFSET + math.radians(24),
                            HERO_ELEV, hs, hcx, hcy, ss=3,
                            hidden_alpha=0.22, ring_pts=ring, ring_yaw=0.0)
    hero_bg = Image.new("RGBA", (hw, hh), (*BG, 255))
    hero = compose(hero_mask)
    hero_bg.alpha_composite(hero)
    hero_bg.convert("RGB").save(os.path.join(DOCS, "jeep-comanche-hero.png"),
                                optimize=True)
    print(f"hero: {FRAMES} frames {HERO_W}x{HERO_H}, "
          f"{len(model.verts)} vertices / {len(model.edges)} edges / "
          f"{len(model.faces)} shell faces")
    return model


def render_attitude_views():
    os.makedirs(GAUGES, exist_ok=True)
    model = build()

    # Front view: camera in front of the truck, no camera elevation.
    scale, cx, cy = view_fit([model.verts], [-math.pi / 2], FRONT_W, FRONT_H,
                             math.radians(0.0), margin=2.0)
    mask = render_mask(model, FRONT_W, FRONT_H, -math.pi / 2, 0.0,
                       scale, cx, cy, ss=VIEW_SS, hidden_alpha=0.0)
    mask_to_rgba(mask).save(os.path.join(GAUGES, "front.png"), optimize=True)

    # Side view: right-hand profile, nose to the right.
    scale, cx, cy = view_fit([model.verts], [0.0], SIDE_W, SIDE_H,
                             math.radians(0.0), margin=2.0)
    mask = render_mask(model, SIDE_W, SIDE_H, 0.0, 0.0,
                       scale, cx, cy, ss=VIEW_SS, hidden_alpha=0.0)
    mask_to_rgba(mask).save(os.path.join(GAUGES, "side.png"), optimize=True)
    print(f"attitude views: front {FRONT_W}x{FRONT_H}, side {SIDE_W}x{SIDE_H}")


def main():
    os.makedirs(DOCS, exist_ok=True)
    model = render_hero_frames()
    print("spec:", ", ".join(f"{k}={v}" for k, v in SPEC.items()))
    render_attitude_views()
    print("wrote", os.path.abspath(TRUCK))


if __name__ == "__main__":
    main()
