#!/usr/bin/env python3
"""Static faces for the NAV instruments: compass, altimeter tape, attitude box."""
import os

from PIL import Image, ImageDraw, ImageFont

from palette import BG, AMBER, MID, DIM, FAINT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(ROOT, "firmware", "fonts", "BlexMonoNerdFontMono-Regular.ttf")
OUT = os.path.join(ROOT, "firmware", "assets", "instruments")


def font(sz):
    return ImageFont.truetype(FONT, sz)


def compass():
    W, H = 120, 72
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    cx, cy, R = 60, 36, 30
    d.ellipse([cx - R, cy - R, cx + R, cy + R], outline=FAINT, width=1)
    import math
    for deg in range(0, 360, 15):
        major = deg % 45 == 0
        a = math.radians(deg - 90)
        r0 = R - (7 if major else 4)
        r1 = R - 1
        col = AMBER if major else DIM
        d.line([(cx + r0 * math.cos(a), cy + r0 * math.sin(a)),
                (cx + r1 * math.cos(a), cy + r1 * math.sin(a))], fill=col, width=1)
    for label, deg in (("N", 0), ("E", 90), ("S", 180), ("W", 270)):
        a = math.radians(deg - 90)
        rr = R - 15
        x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
        f = font(8)
        tw = d.textlength(label, font=f)
        d.text((x - tw / 2, y - 5), label, font=f, fill=AMBER)
    d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=AMBER)
    im.save(os.path.join(OUT, "compass.png"), optimize=True)


def altimeter():
    W, H = 62, 60
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    x = 46
    d.line([(x, 4), (x, 56)], fill=FAINT, width=1)
    for i, alt in enumerate(range(3000, 5001, 250)):
        y = 56 - (alt - 3000) / 2000 * 52
        major = alt % 500 == 0
        d.line([(x - (8 if major else 4), y), (x, y)],
               fill=AMBER if major else DIM, width=1)
        if major:
            f = font(7)
            s = f"{alt:,}"
            tw = d.textlength(s, font=f)
            d.text((x - 10 - tw, y - 4), s, font=f, fill=MID)
    im.save(os.path.join(OUT, "altimeter.png"), optimize=True)


def altimeter_big():
    W, H = 114, 230
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    x = 98
    d.line([(x, 10), (x, 220)], fill=FAINT, width=1)
    f = font(7)
    d.text((6, 4), "ALT FT", font=f, fill=DIM)
    for alt in range(0, 10001, 250):
        y = 220 - alt / 10000 * 210
        major = alt % 1000 == 0
        d.line([(x - (10 if major else 5), y), (x, y)],
               fill=AMBER if major else DIM, width=1)
        if major:
            s = f"{alt:,}"
            tw = d.textlength(s, font=f)
            d.text((x - 12 - tw, y - 4), s, font=f, fill=MID)
    im.save(os.path.join(OUT, "altimeter_big.png"), optimize=True)


def attitude():
    W, H = 100, 64
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W - 1, H - 1], outline=FAINT)
    for dy in (-20, -10, 10, 20):
        y = 32 + dy
        d.line([(16, y), (38, y)], fill=DIM)
        d.line([(62, y), (84, y)], fill=DIM)
    d.line([(40, 32), (60, 32)], fill=AMBER)
    d.line([(50, 22), (50, 42)], fill=AMBER)
    im.save(os.path.join(OUT, "attitude.png"), optimize=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    compass()
    altimeter_big()
    attitude()
    print("wrote instrument faces to", OUT)


if __name__ == "__main__":
    main()
