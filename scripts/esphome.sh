#!/usr/bin/env bash
# Run ESPHome in the pinned container with the project mounted.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARGS=(--rm -v "$ROOT/firmware:/config:Z" -v "$ROOT/.cache:/cache:Z")
if [ -t 0 ]; then
  ARGS+=(-it)
else
  ARGS+=(-i)
fi
if [ -e /dev/ttyACM0 ]; then
  # Rootless Podman on an SELinux host needs the label override to open the
  # USB serial device; the bind mounts still carry their :Z labels.
  ARGS+=(--device /dev/ttyACM0 --security-opt label=disable)
fi
exec podman run "${ARGS[@]}" docker.io/esphome/esphome:latest "$@"
