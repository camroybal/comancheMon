#!/usr/bin/env python3
"""
Generate the amber HUD instrument faces as 8-bit alpha masks.

Everything here is a mask: RGB is black and the alpha channel carries the
line/label coverage.  ESPHome encodes that as LVGL A8 and the widget recolours
it to amber, so a 272x124 compass frame costs 33.7 KB instead of 101 KB.

The compass frames are drawn directly from the heading, not by rotating a
large raster card.  That removes interpolation blur and makes every tick land
on the mathematically correct bearing.
"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

from comanche_model import mask_to_rgba

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "firmware", "assets", "gauges")
FONT = os.path.join(ROOT, "firmware", "fonts", "BlexMonoNerdFontMono-Regular.ttf")

SS = 4
CARDINALS = {0: "N", 90: "E", 180: "S", 270: "W"}


def font(size):
    return ImageFont.truetype(FONT, size * SS)


def _norm(deg):
    return deg % 360


def _text(draw, x, y, text, size, alpha=255, anchor="mm"):
    draw.text((x * SS, y * SS), text, font=font(size), fill=alpha,
              anchor=anchor)


def compass_frames():
    """36 x (272x124) A8 masks, one per 10 degrees of heading."""
    out = os.path.join(OUT, "arc")
    os.makedirs(out, exist_ok=True)
    W, H = 272, 124
    cx, cy = 136.0, 160.0
    r = 160.0
    label_r = 130.0
    for idx in range(36):
        heading = idx * 10
        im = Image.new("L", (W * SS, H * SS), 0)
        d = ImageDraw.Draw(im)

        # Faint arc track.
        pts = []
        for bearing in range(heading - 62, heading + 63, 1):
            a = math.radians(bearing - heading)
            pts.append(((cx + r * math.sin(a)) * SS,
                        (cy - r * math.cos(a)) * SS))
        d.line(pts, fill=48, width=max(1, int(SS * 0.8)))

        # 5-degree ticks; every 10 is long and bright.
        for bearing in range(heading - 60, heading + 61, 5):
            major = bearing % 10 == 0
            a = math.radians(bearing - heading)
            r0 = r
            r1 = r - (12.0 if major else 6.5)
            d.line([((cx + r0 * math.sin(a)) * SS, (cy - r0 * math.cos(a)) * SS),
                    ((cx + r1 * math.sin(a)) * SS, (cy - r1 * math.cos(a)) * SS)],
                   fill=255 if major else 150,
                   width=max(1, int(round(SS * (1.0 if major else 0.8)))))

        # Labels every 30 degrees.  Cardinals get the larger face.
        for bearing in range(heading - 60, heading + 61, 30):
            b = _norm(bearing)
            label = CARDINALS.get(b, f"{b:03d}")
            a = math.radians(bearing - heading)
            x = cx + label_r * math.sin(a)
            y = cy - label_r * math.cos(a)
            _text(d, x, y, label, 12 if b in CARDINALS else 10,
                  255 if b in CARDINALS else 205)

        im = im.resize((W, H), Image.Resampling.LANCZOS)
        mask_to_rgba(im).save(os.path.join(out, f"arc_{idx:02d}.png"),
                              optimize=True)


def face(name):
    """134x88 attitude scale, transparent so the grid shows through."""
    W, H = 134, 88
    im = Image.new("L", (W * SS, H * SS), 0)
    d = ImageDraw.Draw(im)

    # Hairline frame and title rule.
    d.rectangle([0, 0, (W - 1) * SS, (H - 1) * SS], outline=62,
                width=max(1, SS // 2))
    d.line([(8 * SS, 14 * SS), (126 * SS, 14 * SS)], fill=42,
           width=max(1, SS // 2))

    cx, cy, r = 67.0, 52.0, 30.0
    # 120-degree arc track.
    arc = []
    for deg in range(210, 331, 2):
        a = math.radians(deg)
        arc.append(((cx + r * math.cos(a)) * SS,
                    (cy + r * math.sin(a)) * SS))
    d.line(arc, fill=45, width=max(1, SS // 2))

    for deg in range(210, 331, 5):
        major = deg % 10 == 0
        a = math.radians(deg)
        r0 = r
        r1 = r - (6.0 if major else 3.2)
        d.line([((cx + r0 * math.cos(a)) * SS, (cy + r0 * math.sin(a)) * SS),
                ((cx + r1 * math.cos(a)) * SS, (cy + r1 * math.sin(a)) * SS)],
               fill=255 if major else 145,
               width=max(1, int(round(SS * (1.0 if major else 0.75)))))

    # Fixed index at the top of the scale.
    d.polygon([((cx - 3) * SS, 17 * SS), ((cx + 3) * SS, 17 * SS),
               (cx * SS, 22 * SS)], fill=235)

    _text(d, 6, 43, "-60", 8, 185, anchor="lm")
    _text(d, 128, 43, "+60", 8, 185, anchor="rm")

    im = im.resize((W, H), Image.Resampling.LANCZOS)
    mask_to_rgba(im).save(os.path.join(OUT, name), optimize=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    compass_frames()
    face("gauge_roll.png")
    face("gauge_pitch.png")
    print("wrote gauge masks to", OUT)


if __name__ == "__main__":
    main()
