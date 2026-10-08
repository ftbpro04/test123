#!/usr/bin/env bash
set -Eeuo pipefail

WORKSPACE="${WORKSPACE:-/workspace}"
COMFY_ROOT="/opt/ComfyUI"
PERSIST_ROOT="${LTX23_PERSIST_ROOT:-$WORKSPACE/ltx23-data}"
LOG_DIR="$WORKSPACE/logs"
DASHBOARD_PORT="${DASHBOARD_PORT:-18080}"
COMFY_PORT="${COMFY_PORT:-8188}"
JUPYTER_PORT="${JUPYTER_PORT:-8888}"

mkdir -p "$LOG_DIR" "$PERSIST_ROOT"

persist_dir() {
  local name="$1"
  local src="$COMFY_ROOT/$name"
  local dst="$PERSIST_ROOT/$name"

  mkdir -p "$dst"

  if [ -L "$src" ]; then
    rm -f "$src"
  elif [ -d "$src" ]; then
    if [ -z "$(find "$dst" -mindepth 1 -print -quit 2>/dev/null)" ]; then
      cp -a "$src/." "$dst/" 2>/dev/null || true
    fi
    rm -rf "$src"
  elif [ -e "$src" ]; then
    rm -f "$src"
  fi

  ln -s "$dst" "$src"
}

# Persist ONLY user/runtime data. Never persist the app, Python env, custom nodes,
# Hugging Face cache, Torch cache, or Triton cache.
persist_dir models
persist_dir input
persist_dir output
persist_dir user

exec > >(tee -a "$LOG_DIR/ltx23-container.log") 2>&1

echo
echo "=============================================================="
echo " LTX 2.3 Exact Workflow - CLEAN CUDA 13"
echo " ComfyUI:     $COMFY_ROOT"
echo " Persistent:  $PERSIST_ROOT"
echo " Dashboard:   0.0.0.0:$DASHBOARD_PORT"
echo " ComfyUI web: 0.0.0.0:$COMFY_PORT"
echo " Jupyter:     0.0.0.0:$JUPYTER_PORT"
echo "=============================================================="

python - <<'PY'
import torch
print("[runtime] Torch:", torch.__version__)
print("[runtime] Torch CUDA:", torch.version.cuda)
print("[runtime] CUDA available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("[runtime] GPU:", torch.cuda.get_device_name(0))
PY

if [ "${ENABLE_DASHBOARD:-1}" != "0" ]; then
  (
    set +e
    while true; do
      python /usr/local/bin/ltx23-dashboard.py >> "$LOG_DIR/ltx23-dashboard.log" 2>&1
      rc=$?
      echo "[dashboard-watchdog] dashboard exited rc=$rc; restarting in 2s" >> "$LOG_DIR/ltx23-dashboard.log"
      sleep 2
    done
  ) &
  echo $! > "$LOG_DIR/ltx23-dashboard.pid"
fi

if [[ "${DOWNLOAD_WORKFLOW_MODELS:-1}" =~ ^(1|true|yes|on)$ ]]; then
  nohup python /usr/local/bin/download_ltx23_workflow_models.py \
    >> "$LOG_DIR/ltx23-model-download.log" 2>&1 &
  echo $! > "$LOG_DIR/ltx23-model-download.pid"
fi

if [[ "${ENABLE_JUPYTER:-1}" =~ ^(1|true|yes|on)$ ]]; then
  if [[ -n "${JUPYTER_TOKEN:-}" ]]; then
    printf '%s' "$JUPYTER_TOKEN" > "$WORKSPACE/.jupyter_token"
  elif [[ -f "$WORKSPACE/.jupyter_token" ]]; then
    JUPYTER_TOKEN="$(cat "$WORKSPACE/.jupyter_token")"
  else
    JUPYTER_TOKEN="$(python - <<'PY'
import secrets
print(secrets.token_urlsafe(24))
PY
)"
    printf '%s' "$JUPYTER_TOKEN" > "$WORKSPACE/.jupyter_token"
  fi
  chmod 600 "$WORKSPACE/.jupyter_token"
  export JUPYTER_TOKEN

  nohup jupyter lab \
    --ip=0.0.0.0 \
    --port="$JUPYTER_PORT" \
    --no-browser \
    --allow-root \
    --ServerApp.token="$JUPYTER_TOKEN" \
    --ServerApp.password='' \
    --ServerApp.root_dir="$WORKSPACE" \
    >> "$LOG_DIR/jupyter.log" 2>&1 &
  echo $! > "$LOG_DIR/jupyter.pid"
fi

cd "$COMFY_ROOT"

DEFAULT_ARGS=(
  --listen 0.0.0.0
  --port "$COMFY_PORT"
  --disable-auto-launch
  --cuda-malloc
  --fast fp16_accumulation
)

echo "[comfy] Starting clean ComfyUI..."
set +e
# shellcheck disable=SC2086
python main.py "${DEFAULT_ARGS[@]}" ${COMFY_EXTRA_ARGS:-}
COMFY_RC=$?
set -e

echo "[comfy] ComfyUI exited with code $COMFY_RC."
echo "[comfy] Container will remain alive so the dashboard/logs stay available."
while true; do sleep 3600; done
