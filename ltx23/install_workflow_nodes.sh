#!/usr/bin/env bash
set -Eeuo pipefail

COMFY_ROOT="${1:-/app/ComfyUI}"
DEST="$COMFY_ROOT/custom_nodes"
mkdir -p "$DEST"

PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python)}"

clone_if_missing() {
  local url="$1"
  local dir="$2"
  echo "[nodes] Ensuring $dir"
  if [[ ! -d "$DEST/$dir" ]]; then
    git clone --depth 1 "$url" "$DEST/$dir"
  fi
  if [[ -f "$DEST/$dir/requirements.txt" ]]; then
    "$PYTHON_BIN" -m pip install --no-cache-dir -r "$DEST/$dir/requirements.txt"
  fi
}

# Download helpers explicitly requested.
clone_if_missing "https://github.com/MoonGoblinDev/Civicomfy.git" "Civicomfy"
clone_if_missing "https://github.com/huchukato/ComfyUI-HuggingFace.git" "ComfyUI-HuggingFace"

# Exact custom-node packages referenced by the uploaded workflow.
clone_if_missing "https://github.com/kijai/ComfyUI-KJNodes.git" "ComfyUI-KJNodes"
clone_if_missing "https://github.com/evanspearman/ComfyMath.git" "ComfyMath"
clone_if_missing "https://github.com/Lightricks/ComfyUI-LTXVideo.git" "ComfyUI-LTXVideo"
clone_if_missing "https://github.com/ClownsharkBatwing/RES4LYF.git" "RES4LYF"
clone_if_missing "https://github.com/TenStrip/10S-Comfy-nodes.git" "10S-Comfy-nodes"
clone_if_missing "https://github.com/rgthree/rgthree-comfy.git" "rgthree-comfy"
clone_if_missing "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git" "ComfyUI-VideoHelperSuite"

"$PYTHON_BIN" -m pip install --no-cache-dir "huggingface_hub>=0.34" hf-xet requests

echo "[nodes] Exact workflow node set is ready."
