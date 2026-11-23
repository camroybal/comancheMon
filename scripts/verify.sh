#!/usr/bin/env bash
# Local verification: regenerate every asset, run the host tests, then validate
# the ESPHome configuration.  Add --compile to build the firmware as well.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-$ROOT/.venv/bin/python}"
if [ ! -x "$PY" ]; then
  echo "error: $PY not found; run: python3 -m venv .venv && .venv/bin/pip install pillow numpy" >&2
  exit 1
fi

COMPILE=0
RENDER=1
for arg in "$@"; do
  case "$arg" in
    --compile) COMPILE=1 ;;
    --no-render) RENDER=0 ;;
    *) echo "unknown option: $arg" >&2; exit 2 ;;
  esac
done

if [ "$RENDER" = 1 ]; then
  echo "== rendering assets =="
  "$PY" tools/render_background.py
  "$PY" tools/render_gauges.py
  "$PY" tools/render_truck.py
  "$PY" tools/render_startup.py
  "$PY" tools/gen_assets.py
  "$PY" tools/preview.py
fi

echo "== host tests =="
"$PY" -m unittest discover -s tools -p 'test_*.py' -v

echo "== ESPHome config =="
./scripts/esphome.sh config comanche-monitor.yaml > /tmp/comanche-config.log
tail -n 1 /tmp/comanche-config.log

if [ "$COMPILE" = 1 ]; then
  echo "== ESPHome compile =="
  ./scripts/esphome.sh compile comanche-monitor.yaml
fi

echo "verify OK"
