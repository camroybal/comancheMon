# RENIX data reality check

This truck is a **Renix-era Jeep Comanche** (1987–1990, 4.0 L inline-six,
Renix/Bendix engine management). The dashboard is deliberately shaped around
what that truck can actually provide — not around generic OBD-II assumptions.

## What the Renix ECU gives you

These are analogue sensors wired into the Renix ECU and can be tapped or
simulated for the UI:

| Parameter | Range / note |
|---|---|
| Coolant temperature | NTC sender, ~196 °F warm |
| Oil pressure | resistive sender, ~40–60 psi hot |
| Battery voltage | ~13.8 V running |
| Fuel level | tank sender, 0–100 % |
| Engine speed | tach / ECU crank signal |
| Manifold vacuum (MAP) | ~18–20 inHg at idle |
| Throttle position (TPS) | ~0.8 V closed, rising with throttle |
| Oxygen sensor | 0–1 V narrowband, oscillating |
| Idle air control (IAC) | stepper counts, ~20–60 |
| Ignition timing | ~12° BTDC at idle, advancing |
| Knock | knock sensor status |

## What it does **not** have

- **No OBD-II port, no CAN bus, no PID stream.** Renix predates both.
- No transmission temperature, differential temperature, wheel speeds, or
  individual cylinder data unless you add sensors.
- No factory fuel-trim or misfire counters in a form the monitor can read.
- The factory diagnostic connector is a proprietary Renix plug, not ALDL or
  OBD.

## What this firmware shows

- `NAV` — flight instruments: speed/altitude tapes, compass, pitch and roll.
- `DIAG` — **RENIX // ECU DATA**: coolant, vacuum, TPS, O2, IAC steps and
  timing, plus engine-health bars for coolant, oil, battery, fuel and RPM.
  These are simulated today; the labels and ranges match the Renix sensor set
  so real ADC/tach inputs can replace the globals later.
- `COMMS` — the monitor's own GPS/telemetry link, independent of the truck.
- `SYS` — platform health and sensor/IO status.

Avoid adding rows like “trans temp” or “CAN 0x1A4”: they would be fiction on
this vehicle. If you add sensors (e.g. a transmission temperature probe), add a
row and document the sensor in `HARDWARE.md`.
