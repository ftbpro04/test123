#!/usr/bin/env bash
set -Eeuo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
COMFY_ROOT="/app/ComfyUI"
PERSIST_ROOT="${LTX23_PERSIST_ROOT:-$WORKSPACE/ComfyUI}"
LOG_DIR="$WORKSPACE/logs"

mkdir -p "$LOG_DIR" "$PERSIST_ROOT"

persist_dir() {
  local name="$1"
  local src="$COMFY_ROOT/$name"
  local dst="$PERSIST_ROOT/$name"

  mkdir -p "$dst"

  # Seed the persistent directory from anything baked into the image, but only
  # when the persistent destination is empty.
  if [ -d "$src" ] && [ ! -L "$src" ]; then
    if [ -z "$(find "$dst" -mindepth 1 -print -quit 2>/dev/null)" ]; then
      cp -a "$src/." "$dst/" 2>/dev/null || true
    fi
    rm -rf "$src"
  elif [ -L "$src" ]; then
    rm -f "$src"
  fi

  ln -s "$dst" "$src"
}

# Large assets and user data survive when /workspace is a Vast persistent volume.
persist_dir models
persist_dir input
persist_dir output
persist_dir user

# Start the control panel without interfering with the base image startup.
if [ "${ENABLE_DASHBOARD:-1}" != "0" ]; then
  nohup python3 /usr/local/bin/ltx23-dashboard.py >> "$LOG_DIR/ltx23-dashboard.log" 2>&1 &
  echo $! > "$LOG_DIR/ltx23-dashboard.pid"
fi

# Capture the original startup output for the dashboard while keeping the
# NVIDIA entrypoint as the final process path.
exec > >(tee -a "$LOG_DIR/ltx23-container.log") 2>&1

echo "[ltx23-wrapper] Persistent ComfyUI data: $PERSIST_ROOT"
echo "[ltx23-wrapper] Original NVIDIA entrypoint: /opt/nvidia/nvidia_entrypoint.sh"
echo "[ltx23-wrapper] Original command: $*"

exec /opt/nvidia/nvidia_entrypoint.sh "$@"
