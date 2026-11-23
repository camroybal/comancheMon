#!/usr/bin/env python3
"""
Accurate wireframe Jeep Comanche (MJ) model and a small host-side renderer.

The model is built in inches from the published 1986-1992 long-bed MJ
dimensions, then projected with a perspective turntable camera and hidden-line
tested against the body shell.  It is deliberately monochrome so the renderer
can emit an 8-bit alpha mask; LVGL recolours that mask amber at runtime.  One
byte per pixel instead of three (RGB565 + alpha) is the single biggest flash
and bandwidth saving in the project.

Reference dimensions (long bed, 4WD):
    overall length 194.0 in, width 71.7 in, height 64.7 in,
    wheelbase 119.9 in, track 57.0 in, tyre diameter 28.3 in.
"""
from __future__ import annotations

import math
import numpy as np
from PIL import Image, ImageDraw

# Published MJ dimensions, in inches.  Keep these in one place: the model and
# the docs both quote them.
SPEC = {
    "length": 194.0,
    "width": 71.7,
    "height": 64.7,
    "wheelbase": 119.9,
    "track": 57.0,
    "tyre_diameter": 28.3,
    "bed_length": 84.0,
}

BW = SPEC["width"] / 2.0          # body half width
WB = SPEC["wheelbase"]
TRACK = SPEC["track"] / 2.0       # wheel-centre half track
TYRE_R = SPEC["tyre_diameter"] / 2.0
TYRE_HW = 4.65                    # 225-section tyre on a 7 in rim
WHEEL_IN = TRACK - TYRE_HW        # inboard tyre face
WHEEL_OUT = TRACK + TYRE_HW       # outboard tyre face

# Body reference heights.  The long-bed MJ is a unibody pickup: low sill,
# horizontal beltline, flat roof, and a bed floor above the rear axle.
SILL = 20.0
BELT = 43.0
ROOF = SPEC["height"]
HOOD_F = 42.5                     # grille end of the hood
HOOD_R = 45.0                     # cowl end
BED_FLOOR = 30.0
AXLE_Z = TYRE_R

# Longitudinal stations.
FRONT_AXLE = 0.0
REAR_AXLE = -WB
FRONT_BUMPER = 32.5
REAR_BUMPER = FRONT_BUMPER - SPEC["length"]   # -161.5
CAB_FRONT = 4.0
CAB_REAR = -60.0
BED_FRONT = -62.0
BED_REAR = -150.0
TAILGATE_REAR = -153.5
MODEL_CENTER_X = (FRONT_BUMPER + REAR_BUMPER) * 0.5   # -64.5 in


class Model:
    """Vertices, weighted edges and opaque shell faces."""

    def __init__(self):
        self.verts: list[tuple[float, float, float]] = []
        self.edges: dict[tuple[int, int], int] = {}
        self.faces: list[tuple[int, ...]] = []
        self.wheel_faces: list[int] = []

    def v(self, x: float, y: float, z: float) -> int:
        self.verts.append((float(x), float(y), float(z)))
        return len(self.verts) - 1

    def e(self, a: int, b: int, weight: int = 230):
        if a == b:
            return
        key = (a, b) if a < b else (b, a)
        if key not in self.edges or weight > self.edges[key]:
            self.edges[key] = weight

    def loop(self, pts, weight: int = 230):
        for i in range(len(pts)):
            self.e(pts[i], pts[(i + 1) % len(pts)], weight)

    def face(self, pts, weight: int = 230, edges: bool = True,
             wheel: bool = False):
        pts = tuple(pts)
        if len(pts) >= 3:
            if wheel:
                self.wheel_faces.append(len(self.faces))
            self.faces.append(pts)
        if edges:
            self.loop(pts, weight)

    def quad(self, a, b, c, d, weight: int = 230, edges: bool = True):
        self.face((a, b, c, d), weight, edges)

    def box(self, x0, x1, y0, y1, z0, z1, *, bottom=True, top=True,
            weight: int = 220):
        p = len(self.verts)
        for z in (z0, z1):
            for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
                self.v(x, y, z)
        if bottom:
            self.quad(p, p + 1, p + 2, p + 3, weight)
        if top:
            self.quad(p + 4, p + 7, p + 6, p + 5, weight)
        for k in range(4):
            self.e(p + k, p + 4 + k, weight)
        # vertical side faces (only the four uprights are needed as edges)
        return p


def _arc_pts(m: Model, cx, y, cz, r, a0, a1, steps, *, weight=210):
    pts = []
    for k in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * k / steps)
        pts.append(m.v(cx + r * math.cos(a), y, cz + r * math.sin(a)))
    for k in range(len(pts) - 1):
        m.e(pts[k], pts[k + 1], weight)
    return pts


def _wheel(m: Model, cx: float, sy: int):
    """A steel wheel with tyre, rim, hub and six spokes."""
    y_in, y_out = sy * WHEEL_IN, sy * WHEEL_OUT
    zc = AXLE_Z
    n = 16

    def circle(y, r, weight):
        pts = []
        for k in range(n):
            a = 2 * math.pi * k / n
            pts.append(m.v(cx + r * math.cos(a), y, zc + r * math.sin(a)))
        m.loop(pts, weight)
        return pts

    outer = circle(y_out, TYRE_R, 235)
    inner = circle(y_in, TYRE_R, 190)
    # The sidewall is an opaque disc in the hidden-line buffer.  It also stops
    # the far wheel showing through the near wheel.
    m.face(outer, 235, wheel=True)
    m.face(inner, 190, wheel=True)

    rim_o = circle(y_out, 7.5, 220)
    rim_i = circle(y_in, 7.5, 180)

    # Tyre tread connectors.
    for k in range(0, n, 2):
        m.e(outer[k], inner[k], 175 if sy < 0 else 150)

    # Six spokes on the visible outer face, offset a fraction of an inch
    # outboard so they win the depth test against the sidewall.
    y_spoke = y_out + sy * 0.22
    hub_r = 2.35
    hub = []
    for k in range(10):
        a = 2 * math.pi * k / 10
        hub.append(m.v(cx + hub_r * math.cos(a), y_spoke, zc + hub_r * math.sin(a)))
    m.loop(hub, 215)
    for k in range(5):
        a = 2 * math.pi * k / 5 + math.pi / 10
        a0 = m.v(cx + hub_r * math.cos(a), y_spoke, zc + hub_r * math.sin(a))
        a1 = m.v(cx + 7.5 * math.cos(a), y_spoke, zc + 7.5 * math.sin(a))
        m.e(a0, a1, 205)
    # Centre cap.
    cap = []
    for k in range(8):
        a = 2 * math.pi * k / 8
        cap.append(m.v(cx + 1.15 * math.cos(a), y_spoke + sy * 0.05,
                       zc + 1.15 * math.sin(a)))
    m.loop(cap, 190)
    return outer, inner, rim_o, rim_i


def build() -> Model:
    """Build the long-bed MJ.  X forward, Y left, Z up, ground at Z=0."""
    m = Model()

    # ------------------------------------------------------------------ cab
    for sy in (-1, 1):
        y = sy * BW
        # Lower cab side, below the glass.  The perimeter is added by hand so
        # the rocker can stop at the wheel opening instead of drawing a line
        # straight through the tyre.
        m.face([m.v(CAB_FRONT, y, SILL), m.v(CAB_REAR, y, SILL),
                m.v(CAB_REAR, y, 46.0), m.v(CAB_FRONT, y, 46.0)],
               235, edges=False)
        arch_x = math.sqrt(17.0 ** 2 - (SILL - AXLE_Z) ** 2)
        # Top, rear and the rocker behind the front wheel.
        m.e(m.v(CAB_FRONT, y, 46.0), m.v(CAB_REAR, y, 46.0), 235)
        m.e(m.v(CAB_REAR, y, SILL), m.v(CAB_REAR, y, 46.0), 235)
        m.e(m.v(-arch_x, y, SILL), m.v(CAB_REAR, y, SILL), 235)
        # The cab-side front edge only exists above the wheel opening.
        m.e(m.v(CAB_FRONT, y, AXLE_Z + math.sqrt(17.0 ** 2 - CAB_FRONT ** 2)),
            m.v(CAB_FRONT, y, 46.0), 235)
        # Body crease along the XJ/MJ character line.
        m.e(m.v(CAB_FRONT, sy * (BW + 0.12), 35.5),
            m.v(CAB_REAR, sy * (BW + 0.12), 35.5), 145)
        # Door shut line and handle.
        m.e(m.v(-42.0, sy * (BW + 0.15), SILL),
            m.v(-42.0, sy * (BW + 0.15), 62.0), 195)
        h = [m.v(-27.5, sy * (BW + 0.25), 37.5),
             m.v(-35.0, sy * (BW + 0.25), 37.5),
             m.v(-35.0, sy * (BW + 0.25), 39.4),
             m.v(-27.5, sy * (BW + 0.25), 39.4)]
        m.loop(h, 175)
        # Mirror on an arm just ahead of the A-pillar.
        m.e(m.v(-0.5, sy * BW, 47.5), m.v(-2.0, sy * (BW + 4.8), 49.5), 180)
        mirror = [m.v(-4.0, sy * (BW + 4.8), 48.0),
                  m.v(0.2, sy * (BW + 4.8), 48.0),
                  m.v(0.2, sy * (BW + 7.6), 52.0),
                  m.v(-4.0, sy * (BW + 7.6), 52.0)]
        m.loop(mirror, 190)

    # Roof, windshield and glass houses.
    m.face([m.v(-11.0, -34.5, ROOF), m.v(-58.0, -34.5, ROOF),
            m.v(-58.0, 34.5, ROOF), m.v(-11.0, 34.5, ROOF)], 245)
    m.e(m.v(-11.0, 0.0, ROOF + 0.15), m.v(-58.0, 0.0, ROOF + 0.15), 120)
    m.face([m.v(CAB_FRONT, -34.5, HOOD_R), m.v(-11.0, -34.5, 63.5),
            m.v(-11.0, 34.5, 63.5), m.v(CAB_FRONT, 34.5, HOOD_R)], 235)
    for sy in (-1, 1):
        y = sy * 34.8
        # Door glass: slanted A-pillar, vertical B-pillar.
        m.face([m.v(2.0, y, 46.0), m.v(-42.0, y, 46.0),
                m.v(-42.0, y, 62.0), m.v(-9.0, y, 62.0)], 225)
        # Fixed quarter glass behind the door.
        m.face([m.v(-44.0, y, 46.0), m.v(-57.0, y, 46.0),
                m.v(-57.0, y, 61.0), m.v(-44.0, y, 61.0)], 215)
        # Pillars and drip rail.
        m.e(m.v(CAB_FRONT, y, HOOD_R), m.v(-11.0, y, 63.5), 245)
        m.e(m.v(-42.0, y, 46.0), m.v(-42.0, y, 62.0), 240)
        m.e(m.v(-57.0, y, 46.0), m.v(-57.0, y, 61.0), 235)
        m.e(m.v(-11.0, y, 62.8), m.v(-58.0, y, 62.8), 190)

    # Rear cab wall and its window opening.
    m.face([m.v(CAB_REAR, -BW, SILL), m.v(CAB_REAR, BW, SILL),
            m.v(CAB_REAR, BW, 63.5), m.v(CAB_REAR, -BW, 63.5)], 225)
    rw = [m.v(CAB_REAR - 0.15, -27.0, 47.0), m.v(CAB_REAR - 0.15, 27.0, 47.0),
          m.v(CAB_REAR - 0.15, 27.0, 60.0), m.v(CAB_REAR - 0.15, -27.0, 60.0)]
    m.loop(rw, 205)

    # ---------------------------------------------------------------- front
    # Front fender side panels: the XJ/MJ fender is a real panel between the
    # cab and the grille, not an open gap above the wheel.
    arch_x = math.sqrt(17.0 ** 2 - (SILL - AXLE_Z) ** 2)
    for sy in (-1, 1):
        y = sy * BW
        m.face([m.v(CAB_FRONT, y, AXLE_Z + math.sqrt(17.0 ** 2 - CAB_FRONT ** 2)),
                m.v(31.0, y, 25.5), m.v(31.0, y, HOOD_F),
                m.v(CAB_FRONT, y, HOOD_R)], 230, edges=False)
        m.e(m.v(CAB_FRONT, y, HOOD_R), m.v(31.0, y, HOOD_F), 235)
        m.e(m.v(31.0, y, 25.5), m.v(31.0, y, HOOD_F), 235)
        m.e(m.v(31.0, y, 25.5), m.v(arch_x, y, SILL), 225)
        m.e(m.v(CAB_FRONT, sy * (BW + 0.10), 35.5),
            m.v(31.0, sy * (BW + 0.10), 33.0), 145)
        # Side marker lamp.
        m.loop([m.v(23.0, sy * (BW + 0.16), 33.5),
                m.v(27.5, sy * (BW + 0.16), 33.0),
                m.v(27.5, sy * (BW + 0.16), 34.8),
                m.v(23.0, sy * (BW + 0.16), 35.3)], 165)

    m.face([m.v(CAB_FRONT, -35.0, HOOD_R), m.v(31.0, -35.0, HOOD_F),
            m.v(31.0, 35.0, HOOD_F), m.v(CAB_FRONT, 35.0, HOOD_R)], 245)
    m.face([m.v(CAB_FRONT, -35.0, 43.0), m.v(CAB_FRONT, 35.0, 43.0),
            m.v(CAB_FRONT, 35.0, HOOD_R), m.v(CAB_FRONT, -35.0, HOOD_R)], 225)
    # Hood centre crease and two shoulder creases.
    for y in (-14.0, 0.0, 14.0):
        m.e(m.v(CAB_FRONT, y, HOOD_R + 0.08), m.v(31.0, y, HOOD_F + 0.08), 165)

    # Front fascia, grille and lamps.
    m.face([m.v(32.5, -35.5, 25.5), m.v(32.5, 35.5, 25.5),
            m.v(32.5, 35.5, HOOD_F), m.v(32.5, -35.5, HOOD_F)], 235)
    grille = [m.v(32.72, -30.0, 28.6), m.v(32.72, 30.0, 28.6),
              m.v(32.72, 30.0, 41.6), m.v(32.72, -30.0, 41.6)]
    m.loop(grille, 225)
    # 1986-87 MJ: ten vertical slots between the quad rectangular lamps.
    for k in range(-5, 5):
        y = (k + 0.5) * 3.0
        m.e(m.v(32.80, y, 29.6), m.v(32.80, y, 40.8), 185)
    for sy in (-1, 1):
        for y0, y1 in ((16.0, 24.0), (25.0, 33.0)):
            a = sy * y0
            b = sy * y1
            m.loop([m.v(32.82, a, 32.0), m.v(32.82, b, 32.0),
                    m.v(32.82, b, 39.4), m.v(32.82, a, 39.4)], 215)
            m.e(m.v(32.84, a, 35.7), m.v(32.84, b, 35.7), 160)
        # Amber turn signal in the bumper face.
        a, b = sy * 16.0, sy * 33.0
        m.loop([m.v(33.62, a, 19.4), m.v(33.62, b, 19.4),
                m.v(33.62, b, 24.4), m.v(33.62, a, 24.4)], 195)

    # Bumper with guards and a centre plate.
    m.box(30.5, 33.8, -35.5, 35.5, 17.5, 25.5, bottom=False, weight=235)
    for y in (-12.0, 12.0):
        m.box(33.8, 34.3, y - 1.2, y + 1.2, 17.5, 25.5, bottom=False, weight=190)
    plate = [m.v(33.9, -8.0, 19.5), m.v(33.9, 8.0, 19.5),
             m.v(33.9, 8.0, 24.0), m.v(33.9, -8.0, 24.0)]
    m.loop(plate, 170)

    # --------------------------------------------------------------- wheels
    _wheel(m, FRONT_AXLE, -1)
    _wheel(m, FRONT_AXLE, 1)
    _wheel(m, REAR_AXLE, -1)
    _wheel(m, REAR_AXLE, 1)

    # Front fender arches (cut into the lower cab side).
    for sy in (-1, 1):
        a = _arc_pts(m, FRONT_AXLE, sy * (BW + 0.35), AXLE_Z, 17.0,
                     18, 162, 14, weight=225)
        b = _arc_pts(m, FRONT_AXLE, sy * (BW + 0.85), AXLE_Z, 18.0,
                     24, 156, 12, weight=155)
        m.e(a[0], b[0], 150)
        m.e(a[-1], b[-1], 150)
    # Rear arches (cut into the bed side).
    for sy in (-1, 1):
        a = _arc_pts(m, REAR_AXLE, sy * (BW + 0.35), AXLE_Z, 17.0,
                     44, 136, 12, weight=220)
        b = _arc_pts(m, REAR_AXLE, sy * (BW + 0.85), AXLE_Z, 18.0,
                     48, 132, 10, weight=150)
        m.e(a[0], b[0], 145)
        m.e(a[-1], b[-1], 145)

    # ----------------------------------------------------------------- bed
    for sy in (-1, 1):
        y = sy * BW
        m.face([m.v(BED_FRONT, y, 27.0), m.v(BED_REAR, y, 27.0),
                m.v(BED_REAR, y, BELT), m.v(BED_FRONT, y, BELT)],
               235, edges=False)
        arch_x = math.sqrt(17.0 ** 2 - (27.0 - AXLE_Z) ** 2)
        # Top and uprights.
        m.e(m.v(BED_FRONT, y, BELT), m.v(BED_REAR, y, BELT), 235)
        m.e(m.v(BED_FRONT, y, 27.0), m.v(BED_FRONT, y, BELT), 235)
        m.e(m.v(BED_REAR, y, 27.0), m.v(BED_REAR, y, BELT), 235)
        # Rocker segments either side of the rear wheel opening.
        m.e(m.v(BED_FRONT, y, 27.0), m.v(REAR_AXLE + arch_x, y, 27.0), 235)
        m.e(m.v(REAR_AXLE - arch_x, y, 27.0), m.v(BED_REAR, y, 27.0), 235)
        # Top rail and lower crease.
        m.e(m.v(BED_FRONT, sy * (BW + 0.18), BELT - 0.7),
            m.v(BED_REAR, sy * (BW + 0.18), BELT - 0.7), 160)
        m.e(m.v(BED_FRONT, sy * (BW + 0.12), 35.0),
            m.v(BED_REAR, sy * (BW + 0.12), 35.0), 140)
        # The MJ's fuel filler door on the left rear quarter.
        if sy > 0:
            fd = [m.v(-132.0, y + 0.18, 31.5), m.v(-138.0, y + 0.18, 31.5),
                  m.v(-138.0, y + 0.18, 38.0), m.v(-132.0, y + 0.18, 38.0)]
            m.loop(fd, 160)
    m.face([m.v(BED_FRONT, -35.0, BED_FLOOR), m.v(BED_REAR, -35.0, BED_FLOOR),
            m.v(BED_REAR, 35.0, BED_FLOOR), m.v(BED_FRONT, 35.0, BED_FLOOR)],
           190, edges=False)
    m.face([m.v(BED_FRONT, -BW, 27.0), m.v(BED_FRONT, BW, 27.0),
            m.v(BED_FRONT, BW, BELT), m.v(BED_FRONT, -BW, BELT)], 225)
    # Cab/bed gap.
    for sy in (-1, 1):
        m.e(m.v(-61.0, sy * (BW + 0.2), SILL), m.v(-61.0, sy * (BW + 0.2), BELT), 150)

    # Tailgate and step bumper.
    m.box(TAILGATE_REAR, BED_REAR, -BW, BW, 27.0, BELT, bottom=False, weight=235)
    m.e(m.v(BED_REAR - 0.15, -34.0, 31.8), m.v(BED_REAR - 0.15, 34.0, 31.8), 145)
    m.e(m.v(BED_REAR - 0.15, -34.0, 38.2), m.v(BED_REAR - 0.15, 34.0, 38.2), 145)
    m.loop([m.v(BED_REAR - 0.2, -6.0, 33.8), m.v(BED_REAR - 0.2, 6.0, 33.8),
            m.v(BED_REAR - 0.2, 6.0, 36.2), m.v(BED_REAR - 0.2, -6.0, 36.2)], 175)
    for sy in (-1, 1):
        a, b = sy * 28.5, sy * 34.8
        m.loop([m.v(TAILGATE_REAR - 0.18, a, 29.5), m.v(TAILGATE_REAR - 0.18, b, 29.5),
                m.v(TAILGATE_REAR - 0.18, b, 40.0), m.v(TAILGATE_REAR - 0.18, a, 40.0)], 200)
        m.e(m.v(TAILGATE_REAR - 0.20, a, 34.7), m.v(TAILGATE_REAR - 0.20, b, 34.7), 145)
    m.box(REAR_BUMPER, TAILGATE_REAR, -35.5, 35.5, 17.5, 25.5,
          bottom=False, weight=235)
    m.e(m.v(REAR_BUMPER + 0.2, -34.0, 21.0), m.v(REAR_BUMPER + 0.2, 34.0, 21.0), 160)

    # ------------------------------------------------------------ underbody
    # Only the axles are shown: the frame rails and prop shaft sit inside the
    # shell and would otherwise be visible through the wheel openings.
    for cx in (FRONT_AXLE, REAR_AXLE):
        m.e(m.v(cx, -TRACK, AXLE_Z), m.v(cx, TRACK, AXLE_Z), 115)

    return m


# --------------------------------------------------------------------------
# projection and rasterisation
# --------------------------------------------------------------------------

def project_points(points, yaw, elev, scale=1.0, cx=0.0, cy=0.0,
                   dist=1200.0):
    """Perspective turntable projection.  Returns Nx3 (screen x, screen y, depth)."""
    cyaw, syaw = math.cos(yaw), math.sin(yaw)
    ce, se = math.cos(elev), math.sin(elev)
    out = np.empty((len(points), 3), dtype=np.float64)
    for i, (x, y, z) in enumerate(points):
        # Yaw around the middle of the MJ, not the world origin (which sits at
        # the front axle and made the truck orbit its nose).
        xr0 = x - MODEL_CENTER_X
        xr = xr0 * cyaw - y * syaw
        yr = xr0 * syaw + y * cyaw
        # Positive elevation is a camera looking down: farther objects move
        # up the screen and the turntable ring reads as a top-down ellipse.
        sy = z * ce + yr * se
        depth = yr * ce - z * se
        persp = dist / (dist + depth)
        out[i, 0] = cx + xr * scale * persp
        out[i, 1] = cy - sy * scale * persp
        # Keep camera-space depth positive: the inverse-depth rasteriser and
        # the hidden-line test both rely on 1/depth.
        out[i, 2] = dist + depth
    return out


def view_fit(points_sets, yaws, width, height, elev, dist=1200.0, margin=4.0):
    """Choose one scale/centre that fits every yaw without scale pulsing."""
    minx = miny = float("inf")
    maxx = maxy = float("-inf")
    for pts in points_sets:
        for yaw in yaws:
            xy = project_points(pts, yaw, elev, 1.0, 0.0, 0.0, dist)
            minx = min(minx, float(xy[:, 0].min()))
            maxx = max(maxx, float(xy[:, 0].max()))
            miny = min(miny, float(xy[:, 1].min()))
            maxy = max(maxy, float(xy[:, 1].max()))
    sx = (width - 2 * margin) / max(1e-6, maxx - minx)
    sy = (height - 2 * margin) / max(1e-6, maxy - miny)
    scale = min(sx, sy)
    cx = width * 0.5 - (minx + maxx) * 0.5 * scale
    cy = height * 0.5 - (miny + maxy) * 0.5 * scale
    return scale, cx, cy


def _raster_tri(zbuf, p, d, ss):
    """Rasterise one screen-space triangle with inverse-depth interpolation."""
    x0, y0 = p[0, 0] * ss, p[0, 1] * ss
    x1, y1 = p[1, 0] * ss, p[1, 1] * ss
    x2, y2 = p[2, 0] * ss, p[2, 1] * ss
    xmin = max(0, int(math.floor(min(x0, x1, x2))))
    xmax = min(zbuf.shape[1] - 1, int(math.ceil(max(x0, x1, x2))))
    ymin = max(0, int(math.floor(min(y0, y1, y2))))
    ymax = min(zbuf.shape[0] - 1, int(math.ceil(max(y0, y1, y2))))
    if xmin > xmax or ymin > ymax:
        return
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(den) < 1e-9:
        return
    xs = np.arange(xmin, xmax + 1, dtype=np.float64) + 0.5
    ys = np.arange(ymin, ymax + 1, dtype=np.float64) + 0.5
    gx, gy = np.meshgrid(xs, ys)
    l0 = ((y1 - y2) * (gx - x2) + (x2 - x1) * (gy - y2)) / den
    l1 = ((y2 - y0) * (gx - x2) + (x0 - x2) * (gy - y2)) / den
    l2 = 1.0 - l0 - l1
    mask = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
    if not mask.any():
        return
    w0, w1, w2 = 1.0 / d[0], 1.0 / d[1], 1.0 / d[2]
    w = l0 * w0 + l1 * w1 + l2 * w2
    with np.errstate(divide="ignore", invalid="ignore"):
        depth = np.where(w > 1e-12, 1.0 / w, np.inf)
    region = zbuf[ymin:ymax + 1, xmin:xmax + 1]
    np.minimum(region, depth, out=region, where=mask & (depth < region))


def rasterize(model: Model, pts: np.ndarray, width, height, ss,
              faces=None, zbuf=None):
    if zbuf is None:
        zbuf = np.full((height * ss, width * ss), np.inf, dtype=np.float32)
    for i, face in enumerate(model.faces):
        if faces is not None and i not in faces:
            continue
        if len(face) < 3:
            continue
        tri_pts = pts[list(face)]
        tri_d = pts[list(face), 2]
        for k in range(1, len(face) - 1):
            idx = (0, k, k + 1)
            _raster_tri(zbuf, tri_pts[list(idx)], tri_d[list(idx)], ss)
    return zbuf


def clear_hole(zbuf, poly, width, height, ss):
    """Clear the projected wheel-arch opening so the wheel is not occluded."""
    mask = Image.new("1", (width * ss, height * ss), 0)
    d = ImageDraw.Draw(mask)
    d.polygon([(float(x) * ss, float(y) * ss) for x, y in poly], fill=1)
    zbuf[np.asarray(mask, dtype=bool)] = np.inf


def _draw_edge(draw, pts, zbuf, a, b, weight, ss, hidden_alpha, tolerance=2.2):
    x0, y0, d0 = pts[a]
    x1, y1, d1 = pts[b]
    length = math.hypot((x1 - x0) * ss, (y1 - y0) * ss)
    n = max(2, int(length * 1.15) + 1)
    xs = np.linspace(x0, x1, n)
    ys = np.linspace(y0, y1, n)
    # Inverse-depth linear interpolation is a good approximation for these
    # short edges and keeps the hidden-line test stable.
    w0, w1 = 1.0 / max(d0, 1e-6), 1.0 / max(d1, 1e-6)
    w = np.linspace(w0, w1, n)
    depth = 1.0 / np.maximum(w, 1e-12)
    xi = np.clip(np.rint(xs * ss).astype(int), 0, zbuf.shape[1] - 1)
    yi = np.clip(np.rint(ys * ss).astype(int), 0, zbuf.shape[0] - 1)
    visible = depth <= (zbuf[yi, xi] + tolerance)
    # Group runs of equal visibility to avoid per-pixel drawing.
    start = 0
    for k in range(1, n + 1):
        if k == n or visible[k] != visible[start]:
            if k - start >= 2:
                run = [(float(xs[j] * ss), float(ys[j] * ss))
                       for j in range(start, k)]
                alpha = weight if visible[start] else int(weight * hidden_alpha)
                if alpha > 0:
                    draw.line(run, fill=alpha, width=max(1, int(round(ss * 1.08))))
            start = k


def render_mask(model: Model, width, height, yaw, elev, scale, cx, cy,
                ss=4, hidden_alpha=0.18, ring_pts=None, ring_yaw=0.0,
                ring_scale=None, ring_cx=None, ring_cy=None):
    """Render a monochrome alpha mask (mode L) for the current pose."""
    pts = project_points(model.verts, yaw, elev, scale, cx, cy)
    wheel_faces = set(model.wheel_faces)
    body_faces = set(range(len(model.faces))) - wheel_faces
    zbuf = rasterize(model, pts, width, height, ss, faces=body_faces)

    # Wheel arch openings: clear the body side faces on both sides so the
    # wheels can be seen in the wells instead of being hidden by the shell.
    for sy in (-1, 1):
        for axle in (FRONT_AXLE, REAR_AXLE):
            poly = []
            for k in range(24):
                a = 2 * math.pi * k / 24
                poly.append((axle + 17.5 * math.cos(a),
                             AXLE_Z + 17.5 * math.sin(a)))
            hole_pts = [(p[0], sy * BW, p[1]) for p in poly]
            hp = project_points(hole_pts, yaw, elev, scale, cx, cy)
            clear_hole(zbuf, hp[:, :2], width, height, ss)

    # Wheels are rasterised after the arch is opened.  Their sidewalls then
    # occlude the axle and the far side of the truck, but are not themselves
    # erased by the arch clearing polygon.
    rasterize(model, pts, width, height, ss, faces=wheel_faces, zbuf=zbuf)

    mask = Image.new("L", (width * ss, height * ss), 0)
    draw = ImageDraw.Draw(mask)

    # Turntable ring is fixed in world space, so it keeps the truck's yaw out
    # of its own projection.  This is what makes the rotation read as a
    # measured turntable rather than the whole scene spinning.
    if ring_pts:
        rs = scale if ring_scale is None else ring_scale
        rcx = cx if ring_cx is None else ring_cx
        rcy = cy if ring_cy is None else ring_cy
        rp = project_points(ring_pts, ring_yaw, elev, rs, rcx, rcy)
        ring = [(float(x * ss), float(y * ss)) for x, y, _ in rp]
        draw.line(ring + [ring[0]], fill=84, width=max(1, int(round(ss * 0.8))))
        # Degree ticks every 15 degrees.
        for k in range(0, len(ring_pts) - 1, 3):
            x, y, _ = rp[k]
            # Radial tick towards the ring centre in world XY.
            p0 = ring_pts[k]
            dx, dy = p0[0] - (-64.5), p0[1]
            ln = math.hypot(dx, dy) or 1.0
            p1 = (p0[0] + dx / ln * 5.0, p0[1] + dy / ln * 5.0, p0[2])
            q = project_points([p0, p1], ring_yaw, elev, rs, rcx, rcy)
            draw.line([(q[0, 0] * ss, q[0, 1] * ss),
                       (q[1, 0] * ss, q[1, 1] * ss)],
                      fill=152, width=max(1, int(round(ss * 0.8))))

    for (a, b), weight in model.edges.items():
        _draw_edge(draw, pts, zbuf, a, b, weight, ss, hidden_alpha)

    if ss != 1:
        mask = mask.resize((width, height), Image.Resampling.LANCZOS)
    return mask


def mask_to_rgba(mask: Image.Image) -> Image.Image:
    """ESPHome's grayscale alpha path wants RGB=0 plus an alpha channel."""
    im = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    im.putalpha(mask.convert("L"))
    return im


def turntable_ring(cx=-64.5, rx=102.0, ry=57.0, z=0.25, step_deg=5):
    pts = []
    for k in range(0, 360, step_deg):
        a = math.radians(k)
        pts.append((cx + rx * math.cos(a), ry * math.sin(a), z))
    pts.append(pts[0])
    return pts
