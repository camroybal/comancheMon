# Jeep Comanche (MJ) model and turntable

The rotating truck is a 3D wireframe built from the published long-bed
Comanche dimensions, not a generic pickup.  The source of truth is
`tools/comanche_model.py`; `tools/render_truck.py` renders it to the 120-frame
A8 turntable and the two attitude views.

## Reference vehicle

Long-bed, 4WD, 1986-1992 MJ.  The long bed was the original 1986 body style
and gives the best silhouette for a turntable.

| Dimension | Value |
|---|---|
| Overall length | 194.0 in (4,928 mm) |
| Overall width | 71.7 in (1,821 mm) |
| Overall height (4WD) | 64.7 in (1,643 mm) |
| Wheelbase (long bed) | 119.9 in (3,045 mm) |
| Track | 57.0 in (1,448 mm) |
| Tyre diameter | 28.3 in (225/75R15 nominal) |
| Cargo bed | 7 ft (84 in) class |

Sources: Jeep Comanche (MJ) published dimensions and the Jeep Database MJ
page.  The model uses those values directly; the only derived numbers are the
front/rear overhangs (194.0 - 119.9 split as 32.5 in front and 41.6 in rear),
the 4WD ride height and the body stations described below.

## Coordinates and body stations

Units are inches, X forward, Y left, Z up, ground at Z=0.

| Station | Value |
|---|---|
| Front axle | 0 |
| Rear axle | -119.9 |
| Front bumper | +32.5 |
| Rear bumper | -161.5 |
| Cab front (cowl) | +4.0 |
| Cab rear | -60.0 |
| Bed front | -62.0 |
| Tailgate | -150.0 .. -153.5 |
| Sill | 20.0 |
| Beltline | 43.0 |
| Hood | 42.5 front, 45.0 cowl |
| Roof | 64.7 |
| Bed floor | 30.0 |

The mesh includes the 1986-87 ten-slot grille, four rectangular lamps, the
XJ/MJ body crease, door shut/handle, mirrors, side glass and quarter glass,
the long bed with wheel arches, a ribbed tailgate, step bumper, taillights and
six-spoke steel wheels.  Front and rear wheel arches are cut into the side
panels and the wheel wells are opened in the depth buffer; the wheels are not
drawn on top of an unbroken body line.

## Rendering

- Perspective turntable camera at a 16-degree elevation, 1,200 in virtual
  distance, with one scale/centre fitted across every yaw so the truck does
  not pulse in size.
- Opaque shell faces are rasterised into a depth buffer.  Each edge is sampled
  along its length and drawn bright where it passes in front of the shell and
  dim where it is occluded.  That is why the far side reads as depth instead of
  a double-exposure scribble.
- Wheel arches are cleared from the depth buffer before the wheel sidewalls
  are rasterised, so the tyres sit in real openings and the axle is hidden.
- The turntable ring is projected at yaw 0 while the truck uses the frame yaw.
  The ring therefore stays still under the rotating vehicle, like a measured
  turntable rather than a spinning scene.  Both the truck yaw and the ring use
  the MJ's longitudinal midpoint (x = -64.5 in) as their rotation centre, so
  the vehicle turns about its middle instead of orbiting the front axle.
- **120 frames, 3.0 degrees apart, 5 s per revolution = 24 fps.**  Frame 119
  and frame 0 are one 3-degree step apart; the loop is seamless.
- Output is an 8-bit alpha mask at 140x78.  RGB is black, alpha is coverage.
  ESPHome encodes it as LVGL A8 and the animimg recolours it to `#FF8C00`.

## Attitude views

The NAV gauges use the same model:

- Front view: 56x48, yaw -90 degrees, 0 elevation.  The front is nearly square
  (71.7 x 64.7 in), so the old 90x36 box squashed it.
- Side view: 116x40, yaw 0, nose to the right.  The side is 3:1, hence the wide
  strip.
- At runtime LVGL rotates these small A8 masks around their centre.  Roll is a
  front-view rotation; pitch is a side-view rotation.  Because the rotations
  are around the vehicle's projection centre, the wheels and body stay in the
  same relationship instead of sliding around a corner pivot.

## Reproduce

```bash
.venv/bin/python tools/render_truck.py
.venv/bin/python tools/gen_assets.py
.venv/bin/python tools/preview.py
.venv/bin/python -m unittest discover -s tools -p 'test_*.py' -v
```

`tools/render_truck.py` also writes `docs/truck-contact-sheet.png` (all 120
frames) and `docs/jeep-comanche-hero.png` (a larger still).

## Accuracy notes

This is a styling-accurate wireframe, not a measured CAD surface.  The
long-bed proportions, wheelbase, track, wheel size, beltline and roof height
are to published dimensions; the sheet-metal curvature and interior are
simplified because they are not visible at 140x78 on a 3.5-inch panel.  The
grille and lamp pattern represent the 1986-87 MJ; 1988-92 trucks used an
eight-slot grille.
