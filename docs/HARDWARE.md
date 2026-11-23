# Hardware reference — Hosyond / LCDWiki ES3C35P

Everything here was established by interrogating the board over USB and reading
the factory flash image, not by trusting the marketplace listing. The listing
said 240x320; the panel is 320x480.

## Identity

| Item | Value | How established |
|---|---|---|
| Board | LCDWiki **ES3C35P** (sold rebadged as Hosyond 3.5" ESP32-S3) | firmware drivers, panel behaviour, feature set |
| MCU | ESP32-S3, QFN56, silicon **v0.2** | `esptool read-mac` |
| Cores | dual LX7 + LP core, 240 MHz max, 40 MHz crystal | eFuse/chip query |
| PSRAM | **8 MB octal (OPI)**, `ESP32-S3R8` | chip feature string + working config |
| Flash | **16 MB**, JEDEC `5E 4018` (Zbit), quad, 3.3 V | `esptool flash-id` |
| USB | native **USB-Serial/JTAG** (`303a:1001`), no bridge chip | USB descriptors, boot log |
| MAC | `28:84:85:85:12:a8` | eFuse |
| Panel | Sitronix **ST77922**, 320x480, IPS, RGB565, QSPI | firmware `st77922` driver, vendor docs |
| Touch | ST77922 integrated touch controller, I2C | firmware `esp_lcd_touch_new_i2c_st77922` |
| Audio | ES8311 codec + SC8002B speaker amp + mic | vendor docs / board population |
| Storage | microSD, 4-bit SDIO | vendor docs |
| LED | single WS2812 RGB | vendor docs |
| Power | USB-C, LiPo charger, battery header | vendor docs |

## Display / touch wiring

| Signal | GPIO | Notes |
|---|---|---|
| QSPI SCK | 12 | 40 MHz (ST77922 write limit is 62.5 MHz) |
| QSPI D0 | 11 | |
| QSPI D1 | 13 | |
| QSPI D2 | 14 | |
| QSPI D3 | 9 | strapping-adjacent, do not pull at boot |
| LCD CS | 10 | |
| LCD reset | — | **tied to CHIP_PU**; see quirks |
| Backlight | 41 | active HIGH, PWM-capable |
| Touch SDA | 38 | 400 kHz |
| Touch SCL | 39 | |
| Touch reset | 48 | |
| Touch INT | 47 | |
| Touch address | `0x55` | vendor PDF says `0x38`; `0x55` is what the ES3C35P references use |

Panel clock is deliberately **40 MHz**.  The ST77922 QSPI write timing has a
16 ns minimum serial clock (62.5 MHz ceiling, datasheet 7.4.5); 80 MHz is out
of specification.  The PSRAM is the ESP32-S3R8 octal part at its rated 80 MHz.

Panel is **native portrait**. The vendor-correct landscape value is MADCTL
`MV|MY` (`0xA0`), i.e. LVGL `rotation: 270`. On this unit the hardware path did
not take effect at all — the image came out 90 degrees off. The firmware now
forces **LVGL software rotation** with `transform: disabled` on the display and
`rotation: 270` in the LVGL block. That is verified working on the bench unit.

## Ports / expansion

| Signal | GPIO | Notes |
|---|---|---|
| USB D- / D+ | 19 / 20 | native USB, also the serial console |
| UART0 TX / RX | 43 / 44 | exposed on the P4 header; reserved here for GPS |
| RGB LED | 40 | single WS2812 |
| Codec I2C address | `0x18` | ES8311 |
| Speaker amp enable | 1 | active LOW per vendor docs |

SDIO, microphone and I2S pins are **not documented here on purpose**. Published
pin tables for the 2.8" and 4.0" siblings conflict with the 3.5" touch pins, and
nobody has verified the 3.5" SD/audio map on this unit yet. Treat them as unknown
until traced.

## Memory map as shipped

Factory Arduino build (`esp32:esp32:esp32s3`, 16 MB, `app3M_fat9M_16MB`):

```
0x000000  bootloader
0x008000  partition table
0x009000  nvs        20 KB
0x00e000  otadata     8 KB
0x010000  app0        3 MB   (factory test firmware, active)
0x310000  app1        3 MB   (blank)
0x610000  ffat     9.88 MB   (empty, all 0xFF)
0xff0000  coredump   64 KB
```

Factory firmware: Arduino core on IDF `v5.4.1`, built 2025-03-28, LVGL 8
widgets demo + aging tests (ES8311 audio, microphone, WiFi STA/AP, SD, keys,
LED). Full dump and checksum in `docs/BACKUP.md`.

## Quirks that will waste your afternoon

1. **LCD reset is wired to CHIP_PU.** A reset over USB does not reset the panel.
   After flashing another firmware, if the screen stays black with a clean log,
   unplug and replug power once.
2. **Rotation.** See above: 270, and use software rotation (`transform: disabled`);
   the MADCTL path is not reliable on this revision.
3. **Touch transform.** With ESPHome LVGL, do **not** add `transform:` or
   `calibration:`. The touch component caches the un-rotated 320x480 frame and
   LVGL applies the rotation itself. Adding a transform rotates twice.
4. **Backlight.** Nothing drives GPIO41 by default; the panel is dark until the
   firmware turns it on.
5. **Wi-Fi PSK in logs.** Never set the logger to `VERBOSE`; ESPHome prints the
   PSK in clear text at that level.
