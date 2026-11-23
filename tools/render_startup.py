#!/usr/bin/env python3
"""Generate the startup title art and paint-edge wipe."""
import math
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "firmware", "assets")
TITLE_FONT = os.path.join(ROOT, "racing_in_the_rain", "Racing in the Rain.ttf")
MONO_FONT = os.path.join(ROOT, "firmware", "fonts", "BlexMonoNerdFontMono-Bold.ttf")

AMBER = (255, 140, 0)
AMBER_HI = (255, 196, 90)
OUTLINE = (105, 42, 0)
RED = (176, 24, 10)
DARK_RED = (92, 8, 3)
BLACK = (0, 0, 0)

W, H = 480, 320


def startup():
    im = Image.new("RGB", (W, H), BLACK)
    d = ImageDraw.Draw(im)

    title_font = ImageFont.truetype(TITLE_FONT, 86)
    sub_font = ImageFont.truetype(MONO_FONT, 24)

    # ---- title, rendered on its own layer so it can be angled cleanly
    bb = d.textbbox((0, 0), "Comanche", font=title_font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pad = 22
    art = Image.new("RGBA", (tw + pad * 2, th + pad * 2), (0, 0, 0, 0))
    ad = ImageDraw.Draw(art)
    x0, y0 = pad - bb[0], pad - bb[1]
    # hard red drop shadow + dark red depth layer
    ad.text((x0 + 9, y0 + 10), "Comanche", font=title_font, fill=(*RED, 255))
    ad.text((x0 + 5, y0 + 6), "Comanche", font=title_font, fill=(*DARK_RED, 255))
    # amber face with a dark rim
    ad.text((x0, y0), "Comanche", font=title_font, fill=(*AMBER, 255),
            stroke_width=2, stroke_fill=(*OUTLINE, 255))

    art = art.rotate(-6, resample=Image.BICUBIC, expand=True)

    # centre the angled title around y=120
    im.paste(art, (W // 2 - art.width // 2, 120 - art.height // 2), art)

    # ---- divider and subtitle
    d.line([(150, 214), (330, 214)], fill=(120, 40, 0), width=2)
    sub = "Game over"
    sbb = d.textbbox((0, 0), sub, font=sub_font)
    sx = (W - (sbb[2] - sbb[0])) // 2
    sy = 232
    sub_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sub_layer)
    sd.text((sx + 3, sy + 3), sub, font=sub_font, fill=(*DARK_RED, 255))
    sd.text((sx + 1, sy + 1), sub, font=sub_font, fill=(*RED, 220))
    sd.text((sx, sy), sub, font=sub_font, fill=(*AMBER, 255))
    im.paste(sub_layer, (0, 0), sub_layer)

    im.save(os.path.join(ASSETS, "startup.png"), optimize=True)
    docs = os.path.join(ROOT, "docs")
    os.makedirs(docs, exist_ok=True)
    im.save(os.path.join(docs, "startup-preview.png"), optimize=True)


def paint_edge():
    """16 px wide rough paint edge: transparent left, black right, amber rim."""
    w, h = 16, H
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    px = im.load()
    for y in range(h):
        edge = 6.0 + 1.8 * math.sin(y * 0.071) + 1.1 * math.sin(y * 0.29 + 1.3)
        edge = max(2, min(w - 3, int(round(edge))))
        for x in range(w):
            if x >= edge:
                px[x, y] = (*BLACK, 255)
        # amber leading stroke with a red fringe
        px[edge, y] = (*AMBER, 235)
        if edge + 1 < w:
            px[edge + 1, y] = (*RED, 200)
        if edge - 1 >= 0:
            px[edge - 1, y] = (*AMBER_HI, 120)
    im.save(os.path.join(ASSETS, "paint_edge.png"), optimize=True)


def main():
    os.makedirs(ASSETS, exist_ok=True)
    startup()
    paint_edge()
    print("wrote startup art and paint edge")


if __name__ == "__main__":
    main()
