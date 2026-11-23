# Build, flash, restore

## Prerequisites

- Podman (the config is pinned to ESPHome **2026.10.2** in the container)
- Your user in `dialout`, or a temporary `chmod 666 /dev/ttyACM0`
- `secrets.yaml` in `firmware/` (copy `secrets.yaml.example`, fill it in)
- Python 3 + Pillow + numpy for the local renderer/tests:
  ```bash
  python3 -m venv .venv
  .venv/bin/pip install pillow numpy
  ```

The wrapper mounts `firmware/` at `/config`, `../.cache` at `/cache`, and passes
the board through when `/dev/ttyACM0` exists.  On rootless Podman/SELinux it
adds `--security-opt label=disable` for the USB device only; the bind mounts
keep their `:Z` labels.

## Verify locally first

```bash
./scripts/verify.sh              # render every asset + tests + config validation
./scripts/verify.sh --no-render  # tests + config only
./scripts/verify.sh --compile    # also build the image
```

The render step regenerates the background, compass arcs, gauge faces, 120
truck frames, startup art and the ESPHome image manifest, then writes the four
1:1 page mocks to `docs/`.  The unittest suite checks frame counts, sizes,
alpha coverage, unique compass frames, model dimensions, projection fit and
manifest paths.  Only flash after this passes.

## Build and first flash (USB)

```bash
./scripts/esphome.sh config comanche-monitor.yaml     # validate
./scripts/esphome.sh compile comanche-monitor.yaml    # build
./scripts/esphome.sh run comanche-monitor.yaml --device /dev/ttyACM0
```

`run` asks whether to use OTA or USB; choose USB the first time. After that,
`run` without `--device` will OTA to `comanche-monitor.local`.

A normal build is **~4.45 MB** (60.7% of the 7 MB OTA slot):

```
Flash Data   3,364,124 B
Flash Code     998,544 B
DIRAM          116,556 B (34.1%)
IRAM            16,384 B (100%)
Total image   4,452,192 B
```

If the panel stays black but the log is clean: **unplug the USB-C cable and
plug it back in**. LCD reset is tied to CHIP_PU, so a USB reset does not reset
the panel.

## Partition layout

`firmware/partitions.csv` is deliberately not the ESPHome default. Two 7 MB OTA
slots leave room for the A8 mask set and future assets:

```
nvs       0x009000    16 KB
otadata   0x00d000     8 KB
app0      0x010000   7 MB
app1      0x710000   7 MB
ffat      0xe10000  1.94 MB
```

## OTA

```bash
./scripts/esphome.sh run comanche-monitor.yaml
```

OTA uses the same encryption key as the API (`ota: encryption: key:
!secret api_key`).  This removes the legacy OTA password and its flash/RAM
cost.  The key must match between API and OTA; it is inherited when omitted.

## Restore the factory firmware

The untouched 16 MB dump is `backup/factory-esp32s3-16MB.bin`
(sha256 `48dbfba8…f1969dd2`). It includes bootloader, partition table, both app
slots, NVS and the empty FAT partition.

```bash
# from the repo root
esptool -p /dev/ttyACM0 write-flash 0x0 backup/factory-esp32s3-16MB.bin
```

or from a throwaway venv:

```bash
python3 -m venv /tmp/esptool && /tmp/esptool/bin/pip install esptool
/tmp/esptool/bin/esptool -p /dev/ttyACM0 write-flash 0x0 backup/factory-esp32s3-16MB.bin
```

The MAC address lives in eFuse and is not touched by a flash restore.

## Regenerating the visuals

```bash
.venv/bin/python tools/render_background.py # grid + vignette background
.venv/bin/python tools/render_gauges.py     # 36 compass arcs + gauge faces (A8)
.venv/bin/python tools/render_truck.py      # 120 turntable frames + contact sheet
.venv/bin/python tools/render_startup.py    # startup art and paint edge
.venv/bin/python tools/gen_assets.py        # ESPHome image manifest
.venv/bin/python tools/preview.py           # all four 480x320 UI mocks
```

`tools/comanche_model.py` is the Jeep source of truth; `docs/MODEL.md` lists
the published dimensions and the projection/hidden-line method.  The order
matters: the background must exist before the previews, and the truck/gauges
must exist before `gen_assets.py`.

## Troubleshooting

| Symptom | Cause |
|---|---|
| Black screen, clean log | panel not power-cycled; unplug/replug |
| Mirrored / sideways image | keep `transform: disabled` on the display and `rotation: 270` in LVGL; the hardware MADCTL path failed on this unit |
| Touch offset/transposed | remove any `transform:`/`calibration:` from the touchscreen |
| Wireframe art is white | the image lost `transparency: alpha_channel` / the widget lost `recolor: 0xFF8C00` and `recolor_opa: COVER` |
| Build fails on glyphs | a glyph is missing from BlexMono; see `docs/DRIVERS.md` |
| `Permission denied: /dev/ttyACM0` | `sudo usermod -aG dialout $USER`, re-login; or use the wrapper's label override |
| OTA not found | mDNS; use the IP from the boot log |
| `Serial port closed!` in `esphome logs` | the port re-enumerated after reset; reopen it, or use the wrapper's `logs` again |
