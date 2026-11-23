#!/usr/bin/env python3
"""
Host-side 1:1 preview of all four dashboard pages.

This is not the firmware renderer; it mirrors the YAML's 480x320 layout so the
layout, type sizes, contrast and spacing can be reviewed without flashing the
panel.  It loads the same masks and recolours them the same way LVGL does.
"""
import os

from PIL import Image, ImageDraw, ImageFont

from palette import BG, AMBER, MID, DIM, FAINT

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, "firmware", "assets")
FONT = os.path.join(ROOT, "firmware", "fonts", "BlexMonoNerdFontMono-Regular.ttf")
BOLD = os.path.join(ROOT, "firmware", "fonts", "BlexMonoNerdFontMono-Bold.ttf")
W, H = 480, 320
_cache = {}


def font(size, bold=False):
    key = (size, bold)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(BOLD if bold else FONT, size)
    return _cache[key]


def text(d, x, y, s, size=10, color=AMBER, bold=False, anchor=None):
    d.text((x, y), s, font=font(size, bold), fill=color, anchor=anchor)


def center(d, cx, y, s, size=10, color=AMBER, bold=False):
    d.text((cx, y), s, font=font(size, bold), fill=color, anchor="ma")


def mask(path):
    return Image.open(path).convert("RGBA").getchannel("A")


def tint(img, m, xy, color=AMBER):
    layer = Image.new("RGBA", m.size, (*color, 0))
    layer.putalpha(m)
    img.alpha_composite(layer, xy)


def panel(d, x, y, w, h):
    d.rectangle([x, y, x + w - 1, y + h - 1], outline=FAINT)


def rule(d, x, y, w):
    d.line([(x, y), (x + w, y)], fill=FAINT)


def header(img, d, title):
    d.rectangle([0, 0, W, 30], fill=(10, 6, 0))
    text(d, 10, 2, "COMANCHE", 18, AMBER)
    d.line([(96, 7), (96, 23)], fill=FAINT)
    text(d, 104, 8, title, 11, DIM)
    d.line([(378, 7), (378, 23)], fill=FAINT)
    text(d, 386, 8, "T+ 00:12:34", 11, MID)
    d.line([(0, 30), (W, 30)], fill=DIM)


def buttons(d, active=0):
    labels = ["NAV", "DIAG", "COMMS", "SYS"]
    for i, lab in enumerate(labels):
        x = i * 120
        if i == active:
            d.rectangle([x, 288, x + 120, 320], fill=AMBER)
            center(d, x + 60, 297, lab, 12, (10, 6, 0))
        else:
            center(d, x + 60, 297, lab, 12, AMBER)
    d.line([(0, 287), (W, 287)], fill=FAINT)
    for x in (120, 240, 360):
        d.line([(x, 288), (x, 320)], fill=FAINT)


def serial(img, d):
    d.rectangle([8, 34, 63, 283], fill=BG, outline=FAINT)
    text(d, 12, 36, "SERIAL", 9, DIM)
    bands = [
        (50, ["MESH RX", "UART115K", "NVS OK", "RENIX OK", "FUEL 68%", "OIL 42P"], AMBER),
        (120, ["IMU100HZ", "I2C 0x55", "TOUCH OK", "WIFI-67", "HDOP 0.8", "SATS 09"], MID),
        (190, ["BOOT OK", "HEAP142K", "PSRAM 8M", "GPS 3D", "TEMP196F", "ALT 4020"], DIM),
    ]
    for y0, lines, col in bands:
        for i, line in enumerate(lines):
            text(d, 12, y0 + i * 11, line, 9, col)
    d.line([(12, 117), (52, 117)], fill=FAINT)
    d.line([(12, 187), (52, 187)], fill=FAINT)


def tape_speed(img, d, speed=62):
    x, y = 72, 34
    d.rectangle([x, y, x + 55, y + 249], fill=BG, outline=FAINT)
    base = (speed // 20) * 20
    off = round((speed - base) / 20 * 30)
    vals = [base + k * 20 for k in range(3, -4, -1)]
    for i, v in enumerate(vals):
        if i < 0:
            continue
        text(d, x + 28, y + 29 + off + i * 30, str(max(0, v)), 10, MID,
             anchor="ra")
    for k in range(7):
        ty = y + 35 + off + 30 * k
        d.line([(x + 28, ty), (x + 38, ty)], fill=MID)
    for k in range(6):
        ty = y + 50 + off + 30 * k
        d.line([(x + 33, ty), (x + 38, ty)], fill=DIM)
    d.rectangle([x, y, x + 55, y + 41], fill=BG)
    text(d, x + 6, y + 4, "MPH", 9, DIM)
    text(d, x + 6, y + 15, f"{speed:03d}", 18, AMBER)
    d.line([(x + 38, y + 125), (x + 56, y + 125)], fill=AMBER, width=2)
    d.line([(x + 43, y + 121), (x + 38, y + 125), (x + 43, y + 129)],
           fill=AMBER, width=2)


def tape_alt(img, d, alt=4020):
    x, y = 416, 34
    d.rectangle([x, y, x + 55, y + 249], fill=BG, outline=FAINT)
    base = (alt // 100) * 100
    off = round((alt - base) / 100 * 30)
    vals = [base + k * 100 for k in range(3, -4, -1)]
    for i, v in enumerate(vals):
        text(d, x + 28, y + 29 + off + i * 30, str(max(0, v)), 10, MID)
    for k in range(7):
        ty = y + 35 + off + 30 * k
        d.line([(x + 16, ty), (x + 26, ty)], fill=MID)
    for k in range(6):
        ty = y + 50 + off + 30 * k
        d.line([(x + 21, ty), (x + 26, ty)], fill=DIM)
    d.rectangle([x, y, x + 55, y + 41], fill=BG)
    text(d, x + 6, y + 4, "FT", 9, DIM)
    text(d, x + 6, y + 16, f"{alt // 1000},{alt % 1000:03d}", 10, AMBER)
    d.line([(x, y + 125), (x + 16, y + 125)], fill=AMBER, width=2)
    d.line([(x + 11, y + 121), (x + 16, y + 125), (x + 11, y + 129)],
           fill=AMBER, width=2)


def annunciators(d, tilt=False, speed=False, temp=False):
    for i, (lab, on) in enumerate((("SPD", speed), ("TMP", temp),
                                   ("TLT", tilt), ("MIS", True))):
        x = 136 + i * 70
        d.rectangle([x, 34, x + 61, 61], fill=AMBER if on else (10, 6, 0),
                    outline=AMBER if on else FAINT)
        center(d, x + 31, 42, lab, 10, (10, 6, 0) if on else MID, bold=True)


def compass(img, d, heading=311):
    idx = (round(heading / 10) % 36)
    tint(img, mask(os.path.join(ASSETS, "gauges", "arc", f"arc_{idx:02d}.png")),
         (136, 64))
    d.line([(266, 64), (272, 74), (278, 64)], fill=AMBER, width=2)
    pts = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    h = round(heading) % 360
    center(d, 272, 172, f"{h:03d}\u00b0 {pts[((h + 22) // 45) % 8]}", 14, AMBER)


def nav(img, d):
    header(img, d, "// NAV // FLIGHT")
    serial(img, d)
    tape_speed(img, d)
    tape_alt(img, d)
    annunciators(d, tilt=True)
    compass(img, d)
    tint(img, mask(os.path.join(ASSETS, "gauges", "gauge_roll.png")), (136, 196))
    tint(img, mask(os.path.join(ASSETS, "gauges", "gauge_pitch.png")), (274, 196))
    roll = mask(os.path.join(ASSETS, "gauges", "front.png"))
    roll = roll.rotate(-8.0, center=(28, 24), resample=Image.Resampling.BICUBIC)
    tint(img, roll, (136 + 39, 196 + 38))
    pitch = mask(os.path.join(ASSETS, "gauges", "side.png"))
    pitch = pitch.rotate(5.0, center=(58, 20), resample=Image.Resampling.BICUBIC)
    tint(img, pitch, (274 + 9, 196 + 42))
    center(d, 136 + 67, 198, "ROLL +8.0\u00b0", 9, MID)
    center(d, 274 + 67, 198, "PITCH +5.0\u00b0", 9, MID)
    buttons(d, 0)


def bar(d, x, y, w, pct):
    d.rectangle([x, y, x + w - 1, y + 6], fill=(42, 24, 0), outline=FAINT)
    fillw = max(0, min(w - 2, round((w - 2) * pct / 100)))
    if fillw:
        d.rectangle([x + 1, y + 1, x + fillw, y + 5], fill=AMBER)


def diag(img, d):
    header(img, d, "// DIAG // RENIX")
    serial(img, d)
    panel(d, 72, 34, 168, 156)
    text(d, 78, 38, "RENIX // ECU", 9, DIM)
    rule(d, 78, 52, 156)
    rows = [("COOLANT", "196 F", "OK"), ("VACUUM", "18.4 IN", "OK"),
            ("TPS", "0.82 V", "IDLE"), ("O2", "0.45 V", "OSC"),
            ("IAC", "32", "STP"), ("TIMING", "13.5\u00b0", "BTDC")]
    for i, (lab, val, st) in enumerate(rows):
        y = 58 + i * 22
        text(d, 78, y, lab, 9, DIM)
        text(d, 142, y - 1, val, 10, AMBER)
        text(d, 206, y, st, 9, MID)

    panel(d, 246, 34, 226, 156)
    text(d, 252, 38, "ENGINE HEALTH", 9, DIM)
    rule(d, 252, 52, 214)
    rows = [("ENG", "196\u00b0F", 54, "OK"), ("OIL", "42 PSI", 52, "OK"),
            ("BAT", "13.8 V", 63, "CHG"), ("FUEL", "68%", 68, "312"),
            ("RPM", "2140", 36, "4X4")]
    for i, (lab, val, pct, st) in enumerate(rows):
        y = 58 + i * 22
        text(d, 252, y, lab, 9, DIM)
        text(d, 304, y - 1, val, 10, AMBER)
        bar(d, 362, y + 3, 86, pct)
        text(d, 452, y, st, 9, MID)
    rule(d, 252, 164, 214)
    text(d, 252, 170, "RENIX // CLOSED LOOP", 9, DIM)
    text(d, 452, 170, "4.0L", 9, MID)

    panel(d, 72, 196, 394, 88)
    text(d, 78, 200, "MJ // TURNTABLE", 9, DIM)
    d.line([(190, 204), (190, 276)], fill=FAINT)
    d.line([(348, 204), (348, 276)], fill=FAINT)
    text(d, 78, 216, "ATTITUDE", 9, DIM)
    for i, (lab, val, size) in enumerate((("PITCH", "+5.0\u00b0", 10),
                                          ("ROLL", "+8.0\u00b0", 10),
                                          ("YAW", "311\u00b0", 12))):
        y = 230 + i * 14
        text(d, 78, y, lab, 9, DIM)
        text(d, 138, y - 1, val, size, AMBER)
    text(d, 78, 272, "RENIX // 4WD", 9, MID)
    text(d, 354, 216, "TURNTABLE", 9, DIM)
    for i, (s, sz, col) in enumerate((("5.00 S/REV", 10, AMBER),
                                      ("3.0 DEG/FRM", 9, MID),
                                      ("1986 // MJ", 10, MID),
                                      ("BED 7FT", 9, DIM))):
        text(d, 354, 229 + i * 14, s, sz, col)
    tint(img, mask(os.path.join(ASSETS, "truck", "frame_007.png")), (199, 200))
    buttons(d, 1)


def comms(img, d):
    header(img, d, "// COMMS // MESH")
    panel(d, 8, 34, 150, 250)
    text(d, 14, 38, "MESH // AUTO", 9, DIM)
    rule(d, 14, 52, 134)
    text(d, 14, 58, "MESHTASTIC", 12, AMBER)
    text(d, 14, 74, "NODE !A1B2C3", 9, MID)
    rows = [("RSSI", "-67 dBm"), ("SNR", "8.2 dB"), ("HOPS", "2"),
            ("NODES", "14"), ("PACKETS", "12,844"), ("LAST", "00:02")]
    for i, (lab, val) in enumerate(rows):
        y = 94 + i * 18
        text(d, 14, y, lab, 9, DIM)
        text(d, 62, y - 1, val, 10, AMBER)
    rule(d, 14, 198, 134)
    text(d, 14, 204, "UART1", 9, DIM)
    text(d, 14, 216, "115200 8N1", 10, MID)
    text(d, 14, 234, "AUTO-DETECT", 9, DIM)
    text(d, 14, 246, "MESHTASTIC", 10, AMBER)
    text(d, 14, 260, "MESHCORE", 9, DIM)

    panel(d, 166, 34, 306, 250)
    text(d, 172, 38, "MESH // MESSAGES", 9, DIM)
    text(d, 390, 38, "12.4 KB/S", 9, MID)
    rule(d, 172, 52, 294)
    msgs = ["[M01] K7ABC: ridge road clear", "[M02] N0CALL: camp is up",
            "[M03] W1XYZ: 2 hops, strong", "[M04] K7ABC: fuel at 68%",
            "[M05] N0CALL: copy that", "[M06] W1XYZ: moving to 191",
            "[M07] K7ABC: gate open", "[M08] N0CALL: need water",
            "[M09] W1XYZ: rssi -67", "[M10] K7ABC: holding here"]
    for i, s in enumerate(msgs):
        text(d, 172, 58 + i * 18, s, 10, AMBER)
    text(d, 172, 268, "UART1 // 115200 8N1 // 0 ERR", 9, DIM)
    buttons(d, 2)


def sys(img, d):
    header(img, d, "// SYS // BOARD")
    panel(d, 8, 34, 224, 250)
    text(d, 14, 38, "MAINBOARD // SYS", 9, DIM)
    rule(d, 14, 52, 208)
    left = [("CHIP", "ESP32-S3 rev0.2"), ("CORES", "2 @ 240 MHz"),
            ("PSRAM", "8.0 MB"), ("FLASH", "16 MB"), ("HEAP", "142 KB"),
            ("PSRAM FREE", "7.8 MB"), ("UPTIME", "00:12:34"),
            ("WIFI", "-67 dBm"), ("IP", "192.168.1.42"), ("FIRMWARE", "0.2.0")]
    for i, (lab, val) in enumerate(left):
        y = 58 + i * 20
        text(d, 14, y, lab, 9, DIM)
        text(d, 96, y - 1, val, 10, AMBER)
    rule(d, 14, 258, 208)
    text(d, 14, 264, "ST77922 // ST7123 // 16MB", 9, MID)

    panel(d, 240, 34, 232, 250)
    text(d, 246, 38, "SENSORS // IO", 9, DIM)
    rule(d, 246, 52, 216)
    right = [("GPS", "3D FIX"), ("SATS", "09"), ("HDOP", "0.8"),
             ("PITCH", "+5.0\u00b0"), ("YAW", "+1.2\u00b0"),
             ("ROLL", "+8.0\u00b0"), ("COOLANT", "196 F"), ("OIL", "42 PSI"),
             ("FUEL", "68%"), ("VOLTS", "13.8 V"), ("MESH", "RX 12.4 KB/S"),
             ("I2C", "0x55 / 0x76")]
    for i, (lab, val) in enumerate(right):
        y = 58 + i * 17
        text(d, 246, y, lab, 9, DIM)
        text(d, 330, y - 1, val, 10, AMBER)
    rule(d, 246, 262, 216)
    text(d, 246, 268, "I2C 400 KHZ // 2 DEVICES", 9, MID)
    buttons(d, 3)


def main():
    bg = Image.open(os.path.join(ASSETS, "ui-background.png")).convert("RGBA")
    screens = [("nav", nav), ("diag", diag), ("comms", comms), ("sys", sys)]
    thumbs = []
    for name, fn in screens:
        img = bg.copy()
        d = ImageDraw.Draw(img)
        fn(img, d)
        img.convert("RGB").save(os.path.join(ROOT, "docs", f"ui-{name}.png"),
                                optimize=True)
        thumbs.append(img.convert("RGB"))
    # 2x2 contact sheet for the README.
    sheet = Image.new("RGB", (W * 2, H * 2), BG)
    for i, im in enumerate(thumbs):
        sheet.paste(im, ((i % 2) * W, (i // 2) * H))
    sheet.save(os.path.join(ROOT, "docs", "ui-screens.png"), optimize=True)
    # Keep the historical preview filenames used by the README.
    thumbs[0].save(os.path.join(ROOT, "docs", "ui-preview.png"), optimize=True)
    thumbs[0].resize((W * 2, H * 2), Image.Resampling.LANCZOS).save(
        os.path.join(ROOT, "docs", "ui-preview@2x.png"), optimize=True)
    print("wrote docs/ui-{nav,diag,comms,sys}.png and ui-screens.png")


if __name__ == "__main__":
    main()
