# Factory backup

| | |
|---|---|
| File | `backup/factory-esp32s3-16MB.bin` |
| Size | 16,777,216 bytes (16 MB) |
| SHA-256 | `48dbfba8e3f514461e2ab0600f0580a7369ee39b9af41895b34e9733f1969dd2` |
| Read with | `esptool -p /dev/ttyACM0 read-flash 0 0x1000000 …` |
| Board | ESP32-S3 `28:84:85:85:12:a8`, 16 MB flash |

## What is in it

A full, byte-for-byte image of the flash as it shipped:

- ESP32-S3 bootloader
- Arduino partition table (`app3M_fat9M_16MB`)
- **app0**: factory test firmware, project `arduino-lib-builder`, version
  `bb76cb1`, IDF `v5.4.1-1-g2f7dcd862a-dirty`, built 2025-03-28
- **app1**: blank (`0xFF`)
- **ffat**: formatted but empty
- **nvs**: Wi-Fi calibration + the vendor's SoftAP defaults
- **coredump**: empty

The factory app is the LCDWiki aging/factory test: LVGL 8 widgets demo,
colour-fill test, ES8311 audio, microphone loopback, Wi-Fi STA/AP, SD card and
key/LED tests.

## Restore

```bash
esptool -p /dev/ttyACM0 write-flash 0x0 backup/factory-esp32s3-16MB.bin
```

This overwrites every partition, including NVS. The eFuse MAC and calibration
data are not part of the flash image and are unaffected.

After restoring, unplug/replug power: the panel's reset line is tied to CHIP_PU.
