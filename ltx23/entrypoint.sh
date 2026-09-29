#!/usr/bin/env bash
set -Eeuo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
COMFY_ROOT="/app/ComfyUI"
PERSIST_ROOT="${LTX23_PERSIST_ROOT:-$WORKSPACE/ComfyUI}"
LOG_DIR="$WORKSPACE/logs"

mkdir -p "$LOG_DIR" "$PERSIST_ROOT" "$WORKSPACE/hf-cache"

persist_dir() {
  local name="$1"
  local src="$COMFY_ROOT/$name"
  local dst="$PERSIST_ROOT/$name"

  mkdir -p "$dst"

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

persist_dir models
persist_dir input
persist_dir output
persist_dir user

if [ "${ENABLE_DASHBOARD:-1}" != "0" ]; then
  echo "[ltx23-wrapper] Starting dashboard watchdog on port ${DASHBOARD_PORT:-18080}..."
  (
    while true; do
      echo "[dashboard-watchdog] launching dashboard at $(date -Is)" >> "$LOG_DIR/ltx23-dashboard.log"
      python3 /usr/local/bin/ltx23-dashboard.py >> "$LOG_DIR/ltx23-dashboard.log" 2>&1
      rc=$?
      echo "[dashboard-watchdog] dashboard exited rc=$rc; restarting in 2s" >> "$LOG_DIR/ltx23-dashboard.log"
      sleep 2
    done
  ) &
  echo $! > "$LOG_DIR/ltx23-dashboard.pid"
fi

if [[ "${DOWNLOAD_WORKFLOW_MODELS:-1}" =~ ^(1|true|yes|on)$ ]]; then
  echo "[ltx23-wrapper] Starting exact 5-model workflow download..."
  nohup python3 /usr/local/bin/download_ltx23_workflow_models.py \
    >> "$LOG_DIR/ltx23-model-download.log" 2>&1 &
  echo $! > "$LOG_DIR/ltx23-model-download.pid"
else
  echo "[ltx23-wrapper] Exact workflow model download disabled."
fi

exec > >(tee -a "$LOG_DIR/ltx23-container.log") 2>&1

echo "[ltx23-wrapper] Persistent ComfyUI data: $PERSIST_ROOT"
echo "[ltx23-wrapper] Base LTX model auto-downloads: disabled"
echo "[ltx23-wrapper] Exact workflow models: ${DOWNLOAD_WORKFLOW_MODELS:-1}"
echo "[ltx23-wrapper] Original NVIDIA entrypoint: /opt/nvidia/nvidia_entrypoint.sh"
echo "[ltx23-wrapper] Original command: $*"

exec /opt/nvidia/nvidia_entrypoint.sh "$@"
