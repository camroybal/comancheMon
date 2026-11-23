# UI specification

Logical frame: **480x320 landscape**. LVGL rotates the 320x480 panel in software
(`display: transform: disabled`, `lvgl: rotation: 270`).

## Chrome

| Region | x, y | w, h | Notes |
|---|---|---|---|
| header | 0, 0 | 480, 30 | title, screen name, mission timer (`T+ HH:MM:SS`) |
| content | 0, 34 | 480, 250 | per-screen |
| buttons | 0, 288 | 4 x 120, 32 | NAV / DIAG / COMMS / SYS, full width |

Header: `COMANCHE` in 18 px amber at (10, 3); `// SCREEN // MODE` in 11 px
dim at (104, 9); mission clock in 11 px mid at (386, 9); hairline rules at
x=96 and x=378, plus the full-width rule at y=30.

Buttons have no individual border.  One rule sits above the row at y=287 and
single-pixel separators at x=120/240/360 keep the active amber block crisp.
The active button inverts to near-black text on amber.

## Startup

The startup overlay is a full-screen black card shown before the dashboard.

- `startup_art` is a 480x320 baked image. `Comanche` uses Racing in the Rain at
  86 px, rotated -6 degrees, filled amber with a dark rim and a red drop shadow.
  `Game over` is BlexMono Bold 24 px below a thin divider.
- `startup_cover` is an opaque black rectangle and `startup_edge` is a 16x320
  jagged amber/red paint edge. Both slide right together over 1 s; the cover
  hides the unrevealed art and the edge hides the cover's straight leading edge.
- `startup_paint` starts 300 ms after boot and runs for 1 s, then its `on_stop`
  waits 3.7 s before hiding `startup_overlay`, so the splash is up for about
  5 seconds total.
- The startup font is baked into the PNG, so the font file is not embedded.

## Palette

| Name | Hex | Use |
|---|---|---|
| amber | `#FF8C00` | primary text, active control |
| hot | `#FFB25A` | emphasis |
| mid | `#D07400` | secondary values, middle serial band |
| dim | `#9A5400` | labels, oldest serial band |
| faint | `#4A2A00` | rules, panel borders |
| chassis | `#0A0600` | header / terminal fills |
| screen | `#060300` | page base |
| grid | `#0E0800` on `#060300` | 16/64 px background grid + amber vignette |

Masks encode brightness in their alpha channel.  A mask pixel at alpha 255 is
full amber; a dim hidden-line pixel is the same amber at lower alpha.  LVGL's
`recolor`/`recolor_opa: COVER` supplies the amber, so there are no per-asset
colour tables.

## Type

BlexMono Nerd Font Mono, 4 bpp antialiased, sizes **9 / 10 / 11 / 12 / 14 /
18**, with a **bold 10 px** face for the annunciator codes.  Only the runtime
glyphs are embedded: ASCII, `°`, `±`, `·`.  The block/box-drawing glyphs are no
longer needed because the engine-health meters are LVGL bar widgets.

## NAV

| Region | x, y | w, h | Contents |
|---|---|---|---|
| serial strip | 8, 34 | 56, 250 | newest at the top, 3 bands x 6 lines |
| speed tape | 72, 34 | 56, 250 | 20 MPH major / 10 MPH minor ticks, 18 px digital |
| annunciators | 136, 34 | 4 x 62, 28 | SPD / TMP / TLT / MIS, bordered, bold |
| compass arc | 136, 64 | 272, 124 | 120-degree arc, 36 pre-rendered A8 frames, fixed pointer |
| heading | 136, 172 | 272 | centered `311° NW`, 14 px |
| altitude tape | 416, 34 | 56, 250 | 100 ft major / 50 ft minor ticks, digital |
| roll gauge | 136, 196 | 134, 88 | front-view truck rotated by roll |
| pitch gauge | 274, 196 | 134, 88 | side-view truck rotated by pitch |

Annunciators are 1 px-bordered blocks at the top of the content area, using
bold three-letter codes: `SPD` (over-speed), `TMP` (coolant high), `TLT`
(attitude limit) and `MIS` (mission active). The mission clock itself is the
`T+ HH:MM:SS` label in the top-right header bar; `MIS` stays lit while it runs.

Compass arc: 36 pre-rendered 272x124 A8 masks (`compass_arc_00` … `_35`),
10 degrees apart.  They are drawn directly from the heading (not rotated from
a large card), so every tick lands on the mathematically correct bearing.
The `compass_map` image mapping selects `round(heading / 10) % 36`; the label
under it is centered at y=172.  The arc doesn't use runtime image rotation and
doesn't colour-fringe.

Speed tape: a clipped seven-line label, seven long major ticks (20 MPH) and six
short minor ticks (10 MPH) scroll at 30 px per 20 MPH; the fixed needle is at
y=125 and its arrowhead faces the tick scale. A dark cover hides the top tape
line, and an 18 px digital `MPH` readout sits above the window. Altitude tape
uses the same mechanism at 30 px per 100 ft with 50 ft minor ticks.

Attitude gauges: each is a 134x88 A8 face (`gauge_roll_face` /
`gauge_pitch_face`) using the same 120-degree arc language as the compass:
major ticks every 10 degrees, minor ticks every 5, labels at `-60`, `+60`.
The face background is transparent so the grid shows through.  The front view
is 56x48 and the side view is 116x40 — different aspect ratios on purpose,
because a truck front is nearly square and a side profile is 3:1.  The front
view rotates with roll around its centre; the side view rotates with pitch.
Titles show `ROLL +n.n°` and `PITCH +n.n°`.

GPS, the local/Zulu clock, the ATMOS lines and the old circular compass have
been removed from NAV. GPS status remains on SYS.

## DIAG

| Region | x, y | w, h | Contents |
|---|---|---|---|
| serial strip | 8, 34 | 56, 250 | same newest-on-top monitor |
| Renix ECU | 72, 34 | 168, 156 | coolant, vacuum, TPS, O2, IAC, timing |
| engine health | 246, 34 | 226, 156 | ENG/OIL/BAT/FUEL/RPM rows + bar meters |
| turntable | 72, 196 | 394, 88 | 140x78 rotating MJ, attitude/date readouts, fixed ring |

Both top panels end at y=190, so the turntable band has a clear 88 px stage.
The engine panel uses LVGL `bar` widgets (track + amber indicator) instead of
block-glyph text, which is sharper and does not depend on a block font.  A
footer line at y=164 reads `RENIX // CLOSED LOOP` and `4.0L`.

The turntable band has vertical rules at x=190 and x=348.  The left column is
headed `ATTITUDE` and holds PITCH, ROLL, YAW and `RENIX // 4WD`; the right
column is headed `TURNTABLE` and holds `5.00 S/REV`, `3.0 DEG/FRM`,
`1986 // MJ`, `BED 7FT`.  Both columns share the same row baselines.  The
animimg is 140x78 at (199, 200), centred between the rules, and starts when
DIAG opens.

## COMMS

| Region | x, y | w, h | Contents |
|---|---|---|---|
| mesh stats | 8, 34 | 150, 250 | auto-detect, node, RSSI/SNR, hops, nodes, packets, UART |
| messages | 166, 34 | 306, 250 | 10-line message feed |

Simulated Meshtastic/MeshCore link. The second ESP32 is sketched on UART1
(GPIO17 RX / GPIO18 TX, 115200) in the YAML comments.  The stats panel ends
with the active protocol and the standby protocol in dim text; the message
panel has a live rate at the right of its title and a UART/error footer.

## SYS

| Region | x, y | w, h | Contents |
|---|---|---|---|
| mainboard | 8, 34 | 224, 250 | chip, cores, PSRAM, flash, heap, PSRAM free, uptime, WiFi, IP, firmware |
| sensors | 240, 34 | 232, 250 | GPS, IMU, engine senders, mesh, I2C |

Heap and PSRAM free are read from `heap_caps_get_free_size` every second; IP
comes from the `wifi_info` text sensor and RSSI from `wifi_signal`.  Both
panels have a hairline footer so the row block does not float.

## Serial monitor

56 px wide, 18 visible lines in three 6-line bands, **newest at the top**:

- top band: newest, `#FF8C00`
- middle band: `#D07400`
- bottom band: oldest, `#9A5400`

One token is prepended every 300 ms, so the newest line is at the top; overflow
rolls downward: the oldest line in the top band moves to the middle, then to the
bottom, then drops off. Each line is at most 8 characters so it fits 48 px at
9 px. The strip runs the full height, ending just above the buttons. Visible
only on NAV and DIAG.

## Truck

- 120 frames, 140x78, 3.0 degrees per frame, 5 s per revolution (24 fps).
- Dimensioned long-bed MJ: 194.0 x 71.7 x 64.7 in, 119.9 in wheelbase, 57 in
  track, 28.3 in tyres.  See [MODEL.md](MODEL.md).
- Hidden-line z-buffer, front-facing edges bright, occluded edges dim; wheel
  arches are real openings, not lines across the tyres.
- A fixed turntable ring stays still under the truck; the truck yaws 360°.
- Frames are A8 masks recoloured amber at runtime.  The animimg starts on DIAG
  entry and stops on leave.
- Attitude views use the same model: front 56x48, side 116x40.

## Update cadence

| Interval | Work |
|---|---|
| 100 ms | simulate NAV/DIAG/health/ECU/IMU values; update NAV tapes, compass frame (when the 10° bucket changes), attitude text/rotations, annunciators |
| 250 ms | ECU/engine/comms/SYS text, five bar meters, attitude readouts |
| 300 ms | append one serial token, roll the three fade bands |
| 1 s | mission clock, uptime, heap, PSRAM free, WiFi RSSI, IP, mesh rate |
| 2 s | append a mesh message, update RSSI/SNR/hops/nodes/packets |

Hidden pages skip the expensive NAV drawing and the serial label writes.  The
text/position helpers compare before invalidating, so most ticks produce no
redraw at all.

## Screen switching

All four screens are full-page transparent containers; only one is visible.
Button handlers show/hide the containers and the truck/serial group, start or
stop the turntable, update the header screen name and set the `g_page` global.
Buttons are checkable and mutually exclusive.
