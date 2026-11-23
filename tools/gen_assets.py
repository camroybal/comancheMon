#!/usr/bin/env python3
"""Generate the ESPHome image manifest.

Monochrome wireframe art is stored as a grayscale alpha mask (one byte per
pixel).  LVGL recolours it amber at runtime.  Only the startup card and the
page background carry real colour.
"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "firmware", "assets")
FRAMES = 120
OUT = os.path.join(ASSETS, "images.yaml")


def image(path, ident, typ="GRAYSCALE", alpha=True):
    lines = [
        "- platform: file",
        f"  file: {path}",
        f"  id: {ident}",
        f"  type: {typ}",
    ]
    if alpha:
        lines.append("  transparency: alpha_channel")
    return "\n".join(lines) + "\n"


def main():
    with open(OUT, "w") as f:
        # Attitude gauge faces and the two static 3D views.
        f.write(image("assets/gauges/gauge_roll.png", "gauge_roll_face"))
        f.write(image("assets/gauges/gauge_pitch.png", "gauge_pitch_face"))
        f.write(image("assets/gauges/front.png", "truck_front"))
        f.write(image("assets/gauges/side.png", "truck_side"))

        # 36 compass frames, 10 degrees apart.
        for i in range(36):
            f.write(image(f"assets/gauges/arc/arc_{i:02d}.png",
                          f"compass_arc_{i:02d}"))

        # Full-colour page background and startup card.
        f.write(image("assets/ui-background.png", "ui_bg", "RGB565", False))
        f.write(image("assets/startup.png", "startup_art", "RGB565", False))
        f.write(image("assets/paint_edge.png", "paint_edge_img", "RGB565", True))

        # 120 turntable frames, 3 degrees apart.
        for i in range(FRAMES):
            f.write(image(f"assets/truck/frame_{i:03d}.png", f"truck_{i:03d}"))

    with open(os.path.join(ASSETS, "truck_src.yaml"), "w") as f:
        for i in range(FRAMES):
            f.write(f"- truck_{i:03d}\n")

    print(f"wrote {OUT} and 120-frame source list")


if __name__ == "__main__":
    main()
