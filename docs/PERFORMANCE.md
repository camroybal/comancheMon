# Performance notes

Everything here is either measured on this build or taken from the part
datasheet.  The target is a stable 30 fps-class dashboard with the least
possible flash, PSRAM traffic and radio/CPU idle work.

## Display bus

The ST77922 QSPI write timing has a minimum serial-clock cycle of **16 ns**
(datasheet section 7.4.5), i.e. a **62.5 MHz** ceiling.  This build runs the
panel at **40 MHz**:

- 40 MHz is comfortably inside the limit with margin for the flex cable and
  the board's level shifting.
- A full 480x320 RGB565 frame is 307,200 bytes.  QSPI moves four bits per
  clock, so 40 MHz is about 20 MB/s raw and a full frame is ~15 ms.  Most
  refreshes are partial, so the panel is not the limiting factor.
- 80 MHz is out of specification.  The earlier README's 40 MHz setting was
  correct for reliability; it is now documented instead of being an accident.

PSRAM is the `ESP32-S3R8` 8 MB octal part at **80 MHz**, the supported speed
for this module.  80 MHz is deliberately not pushed to an overclock: the
animation already fits the frame budget, and PSRAM errors are not recoverable.

## Asset encoding: A8 masks instead of RGB565+A

Every wireframe asset is a single-colour amber drawing.  Instead of baking
colour, the tools emit a **grayscale alpha mask**: RGB is black, the alpha
channel carries line coverage, and LVGL's `recolor` style paints it amber at
draw time.

| Asset | Old encoding | New encoding | Saving |
|---|---|---|---|
| 36 compass arcs, 272x124 | RGB565 + alpha, 101,184 B each (3.64 MB) | A8, 33,728 B each (1.21 MB) | **2.43 MB** |
| Gauge faces, 2 x 134x88 | RGB565 + alpha, 70,752 B | A8, 23,584 B | 47 KB |
| Attitude views, 90x36 x2 | RGB565 + alpha, 19,440 B | 56x48 + 116x40 A8, 7,328 B | 12 KB |
| Jeep turntable, 120 x 140x78 | - | A8, 1.31 MB | 2x frames, 3.4x area vs the old 60x76x44 |
| Unused instrument faces | ~126 KB linked | not linked | 126 KB |

The full application image went from **6,050,288 bytes** (old build) to
**4,452,192 bytes** (this build): a **26% reduction**, with 39% of the 7 MB OTA
slot still free.  Static `.rodata` dropped from 5.08 MB to 3.36 MB.

A8 also halves the bytes LVGL reads for the rotating gauge views and removes
the RGB565 colour-fringing that made the old large-image rotations unusable.

## Render loop

The UI is not redrawn as one 480x320 canvas every frame.  Work is split by
what actually changes:

| Interval | Work |
|---|---|
| 100 ms | simulated motion + NAV speed/alt tapes, compass frame (only when the 10-degree index changes), attitude text and two small rotations. Only runs while NAV is visible. |
| 250 ms | ECU/engine/comms/SYS text and five bar values, with change detection. |
| 300 ms | one serial token and the three-band waterfall. |
| 1 s | mission/uptime clock, internal heap, PSRAM free, WiFi RSSI, IP, mesh rate. |
| 2 s | one mesh message, packet counters and RF stats. |

Specific wins:

- `cm::text()` compares against `lv_label_get_text` before calling
  `lv_label_set_text`.  LVGL invalidates the whole label object on a set, even
  if the string is identical.
- `cm::y()` and `cm::bar()` do the same for positions and bar values.
- The speed/altitude tape text is rebuilt only when the 20 MPH/100 ft base
  changes; the tick positions are integer-compared.
- The compass mapping only calls `lv_image_set_src()` when the 10-degree
  bucket changes.  With the simulated heading the arc changes roughly once
  every 20 seconds, not ten times a second.
- The DIAG animimg is started on page entry and stopped on leave.  There is no
  hidden animation timer running on NAV/COMMS/SYS.
- The serial string ring is maintained every 300 ms, but label writes are
  skipped while neither NAV nor DIAG is visible.

## LVGL and framework settings

```yaml
lvgl:
  buffer_size: 25%       # 76.8 KB draw buffer; also 76.8 KB PSRAM rotate buffer
  draw_rounding: 4       # 4-pixel dirty regions
  refresh_interval: 33ms # ~30 fps ceiling, enough for 24 fps turntable
display:
  data_rate: 40MHz
  update_interval: never # LVGL owns the panel; no redundant display task
```

Framework:

```yaml
compiler_optimization: PERF
assertion_level: DISABLE
CONFIG_ESPTOOLPY_FLASHMODE_QIO: "y"
CONFIG_ESPTOOLPY_FLASHFREQ_80M: "y"
CONFIG_ESP32S3_DATA_CACHE_64KB: "y"
CONFIG_ESP32S3_DATA_CACHE_LINE_64B: "y"
```

The 64 KB data cache helps the software-rotation path, which reads masks and
writes the rotate buffer in PSRAM.  IRAM is intentionally full (16,384 bytes);
DIRAM still has 225,204 bytes free and the build uses 34.1% of RAM.
`flash_chip: generic` removes the unused flash-vendor drivers and saves about
4.8 KB of DIRAM; the board's Zbit part works with the generic driver.

`buffer_size: 25%` is a deliberate reliability choice.  A 50% buffer would
allocate 153.6 KB internally; after Wi-Fi, lwIP and the API stack that can
fall back to PSRAM and become slower.  The current buffer leaves the display
driver enough internal headroom and still reduces a full-screen redraw to four
flushes.

## Boot

The startup card is opaque, so all five update intervals are held off with
`startup_delay: 4500ms`; they begin under the still-opaque startup card, then
the card is dismissed at 5 s with current data already drawn.  This keeps the
first full-screen LVGL draw from competing with label/tape work.  The first
draw still takes ~120-200 ms on the bench unit, before the card is revealed;
the wipe begins at 300 ms and is unaffected.  Subsequent partial refreshes are
far below the 50/60 ms component budget.  The boot log after the final flash
shows no "interval took a long time" warning, only the one-time LVGL draw.

Runtime logs after flashing show the app running and Wi-Fi retrying against the
placeholder SSID in `secrets.yaml`; there is no reboot because
`wifi: reboot_timeout: 0s`.  Fill in the real credentials before deployment.

## Longevity

- Panel clock is 36% below the QSPI write ceiling.
- PSRAM stays at its rated 80 MHz.
- The turntable timer stops when DIAG is not visible.
- Logging is INFO with noisy components (LVGL, display, Wi-Fi, API, mDNS) at
  WARN.  There is no verbose serial logging in the normal build.
- Audio, SD and WS2812 are not enabled, so no unverified drivers or extra
  power domains are active.
- OTA is authenticated with the API encryption key; the legacy OTA password
  (and its flash/RAM cost) is gone.

## Reproduce

```bash
./scripts/verify.sh --compile
```

This regenerates every asset, runs the host regression tests, validates the
ESPHome config and optionally compiles.  The build prints the exact image,
RAM and flash figures; use those rather than trusting a README number after a
large change.

References:

- ST77922 datasheet, QSPI interface characteristics, section 7.4.5
  <https://dl.espressif.com/AE/esp-iot-solution/ST77922_SPEC_V0.1.pdf>
- ESPHome `mipi_spi`: <https://esphome.io/components/display/mipi_spi/>
- ESPHome LVGL: <https://esphome.io/components/lvgl/>
- ESPHome image/`GRAYSCALE` alpha path:
  <https://esphome.io/components/image/>
