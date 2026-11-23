# Driver inventory

Two stacks matter on this board: the **factory firmware** that shipped on it
(useful as a reference and as a fallback), and the **ESPHome stack** this
project builds. Keep this file updated when a driver is added or replaced.

## Bus / peripheral map

| Bus | Pins | Devices | Used by this project |
|---|---|---|---|
| QSPI (SPI2) | SCK 12, D0-3 11/13/14/9, CS 10 | ST77922 panel | yes |
| I2C | SDA 38, SCL 39 | ST77922 touch `0x55`, ES8311 `0x18`, P4 header | touch yes, codec no |
| LEDC | 41 | backlight | yes |
| USB Serial/JTAG | 19/20 | console, flashing | yes |
| SDIO | unverified | microSD | no |
| I2S | unverified | ES8311 / mic / speaker | no |
| RMT | 40 (vendor) | WS2812 | no |
| UART0 | 43/44 | P4 header | reserved for GPS |
| ADC | unverified | battery sense | no |

## Factory firmware drivers (in the 16 MB dump)

Built with the Arduino core on **ESP-IDF v5.4.1** (`arduino-lib-builder`,
2025-03-28). Components confirmed from strings and symbols in `app0`:

### Display / input

| Driver | Role | Evidence |
|---|---|---|
| `esp_lcd` SPI + panel IO | QSPI transport to the panel | `esp_lcd_new_panel_io_spi`, `panel_io_spi_tx_color` |
| vendor `esp_lcd_st77922` | panel controller: reset/init/draw/mirror/invert/on-off | `esp_lcd_new_panel_st77922`, `panel_st77922_*` |
| vendor `esp_lcd_touch_st77922` | capacitive touch over I2C | `esp_lcd_touch_new_i2c_st77922`, `touch_st77922_read_fw_info` |
| LVGL 8 | widget demo, tick task, mutex | "LVGL v8", `lvgl_port_*`, "Widgets demo" |
| `esp_lcd_panel_io_i2c_v2` | I2C panel IO (not used for this panel) | `/IDF/components/esp_lcd/i2c/...` |

The panel init table is a **63-entry** vendor array; a similar 60-entry table
for a 532x300 panel also exists in the driver and is a decoy. Our ESPHome
sequence is a transcription of the 63-entry table (`st77922-init-sequence.yaml`).

### Audio

| Driver | Role |
|---|---|
| `es8311` | I2C codec control (0x18) |
| `i2s` / `esp_driver_i2s` | PCM to codec and from microphone |
| `esp_driver_gpio` | amp enable / key / LED |

### Storage / system

| Driver | Role |
|---|---|
| `esp_driver_sdmmc` + `fatfs` + `vfs` | microSD, mounted as `/sdcard` |
| `nvs` | Wi-Fi credentials and calibration |
| `app_update` / `esp_ota_ops` | OTA slots, factory fallback |
| `espcoredump` | core dump partition |
| `freertos`, `esp_timer`, `esp_event`, `esp_netif`, `lwip` | RTOS, timers, events, TCP/IP |
| `mbedtls` | TLS / crypto |
| `esp_wifi`, `esp_phy`, `esp_bt` | Wi-Fi and Bluetooth LE |
| `esp_driver_uart`, `esp_driver_ledc`, `esp_driver_rmt` | console, backlight, WS2812 |
| `esp_psram`, `esp_mm`, `esp_partition`, `bootloader_support`, `efuse` | memory / boot plumbing |
| `network_provisioning` (managed component) | SoftAP provisioning UI |

Factory UI: LVGL 8 widgets demo, colour-fill test, audio loopback, microphone
test, Wi-Fi STA/AP test, SD test, key/LED test. It advertises `3.5_ESP32S3_AP_*`
when the AP test runs.

## This project's stack

ESPHome **2026.10.2** (ESP-IDF 5.5.6 framework, ESP32-S3, octal PSRAM):

| Component | Role | Where |
|---|---|---|
| `mipi_spi` | QSPI display driver, 320x480 native, RGB order, inverted, 40 MHz, `transform: disabled`, `update_interval: never` | `comanche-monitor.yaml` |
| custom `init_sequence` | ST77922 63-entry vendor power-up table | `st77922-init-sequence.yaml` |
| `st7123` touchscreen | ST77922 touch half, I2C `0x55`, reset GPIO48 | `comanche-monitor.yaml` |
| `lvgl` 9.5 | all UI, software rotation 270, 25% draw buffer, 4 px rounding, 33 ms refresh | `comanche-monitor.yaml` |
| `ledc` + `monochromatic` | GPIO41 backlight, 1 kHz PWM | `comanche-monitor.yaml` |
| `font` | BlexMono (Nerd Font Mono), 9/10/11/12/14/18 px, 4 bpp | `fonts/` |
| `image` (`platform: file`) + `animimg` | A8 masks recoloured amber: 36 compass arcs, gauge faces, front/side views, 120 turntable frames, startup art and paint edge, page background | `assets/images.yaml` |
| `comanche_ui.h` | allocation-free label/bar/rotation/change-detection helpers used by the lambdas | `firmware/` |
| `wifi_signal` | real RSSI on SYS | `comanche-monitor.yaml` |
| `wifi_info` | real IP and SSID text sensors on SYS | `comanche-monitor.yaml` |
| `wifi`, `api`, `ota`, `captive_portal` | network + encrypted OTA | `comanche-monitor.yaml` |
| `sntp` | **removed** — no clock is shown | - |
| `uart` + `gps` | **not enabled** — sketched for the future module | bottom of YAML |

### Why A8 masks

Every wireframe is one colour.  The image encoder is given a black RGBA PNG
whose alpha channel carries the line coverage.  `type: GRAYSCALE` +
`transparency: alpha_channel` becomes LVGL `LV_COLOR_FORMAT_A8`, one byte per
pixel.  The widget carries `recolor: 0xFF8C00` and `recolor_opa: COVER`.
Compared with RGB565+alpha (three bytes per pixel) this cuts the compass set by
2.43 MB and lets LVGL apply the amber without a per-pixel colour table.  The
alpha channel also stores hidden-line dimming, so one mask has both line art
and depth.

Do **not** use `type: RGB565` for new masks; it triples flash and reintroduces
the RGB565 rotation fringing the old attitude views had.

### Why 40 MHz QSPI

The ST77922 QSPI write cycle minimum is 16 ns, a 62.5 MHz ceiling (datasheet
section 7.4.5).  This board runs at 40 MHz with margin.  80 MHz is out of
specification; the display is not the bottleneck at 40 MHz, and the lower
clock reduces EMI and power.  See [PERFORMANCE.md](PERFORMANCE.md).

### Deliberately not used (yet)

- **ES8311 audio** — no ESPHome codec config; pins are unverified.
- **microSD** — SDIO pin map for the 3.5" revision is unverified.
- **WS2812** — GPIO40 is documented by the vendor, not traced here.
- **Battery ADC** — unknown divider pin.
- **Wi-Fi provisioning UI** — plain ESPHome captive portal instead.

## Font

`BlexMonoNerdFontMono-Regular.ttf` / `-Bold.ttf` are the Nerd Fonts build of
IBM Plex Mono (OFL 1.1).  The runtime subsets carry only the glyphs the UI uses:

```
ASCII, ° ± ·
```

The old block (`█ ▓ ▒ ░`) and box-drawing glyphs were removed because the
engine-health meters are now LVGL bar widgets.  The eight geometric shapes
(■ □ ▲ ► ▼ ◄ ○ ●) are **not** in this font build and must not be added to the
glyph list — ESPHome fails the build if they are.

## Changing the stack

- If you replace the panel driver, keep the **amber/dim palette** and the
  480x320 coordinate system; every widget is positioned in that frame.
- If you add the GPS module, enable the UART block and replace `g_lat`/`g_lon`
  updates with the `gps` component's sensors. Do not change the label IDs — the
  update intervals reference them.
- If you enable audio or SD, add the pins to `docs/HARDWARE.md` first, then the
  driver. Do not copy the 2.8"/4.0" pin tables; they conflict with touch.
- If you add a monochrome asset, render it as an alpha mask and add it to
  `tools/gen_assets.py`, not hand-written YAML.
