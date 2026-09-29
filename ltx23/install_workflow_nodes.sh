#!/usr/bin/env bash
set -Eeuo pipefail

COMFY_ROOT="${1:-/app/ComfyUI}"
DEST="$COMFY_ROOT/custom_nodes"
mkdir -p "$DEST"

PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python)}"

ensure_node() {
  local url="$1"
  local dir="$2"
  local ref="${3:-}"

  echo "[nodes] Ensuring $dir${ref:+ @ $ref}"

  if [[ ! -d "$DEST/$dir/.git" ]]; then
    rm -rf "$DEST/$dir"
    git clone "$url" "$DEST/$dir"
  fi

  if [[ -n "$ref" ]]; then
    git -C "$DEST/$dir" fetch --depth 1 origin "$ref"
    git -C "$DEST/$dir" checkout --detach FETCH_HEAD
  fi

  if [[ -f "$DEST/$dir/requirements.txt" ]]; then
    "$PYTHON_BIN" -m pip install --no-cache-dir -r "$DEST/$dir/requirements.txt"
  fi
}

# Convenience/download nodes.
ensure_node "https://github.com/Comfy-Org/ComfyUI-Manager.git" "ComfyUI-Manager"
ensure_node "https://github.com/MoonGoblinDev/Civicomfy.git" "Civicomfy"
ensure_node "https://github.com/huchukato/ComfyUI-HuggingFace.git" "ComfyUI-HuggingFace"

# Exact custom-node packages referenced by 10E_I2V_triplepass_00010-audio.json.
# Commit pins come from the workflow metadata where available.
ensure_node "https://github.com/kijai/ComfyUI-KJNodes.git" "ComfyUI-KJNodes" "4dfb85dcc52e4315c33170d97bb987baa46d128b"
ensure_node "https://github.com/evanspearman/ComfyMath.git" "ComfyMath" "c01177221c31b8e5fbc062778fc8254aeb541638"
ensure_node "https://github.com/Lightricks/ComfyUI-LTXVideo.git" "ComfyUI-LTXVideo" "2acf7af8991f33b5cc06ec26753cb6e88e057d04"
ensure_node "https://github.com/ClownsharkBatwing/RES4LYF.git" "RES4LYF" "0dc91c00c4c3fb38e7874fcd7a2a327765e8882c"
ensure_node "https://github.com/TenStrip/10S-Comfy-nodes.git" "10S-Comfy-nodes" "f5f8221d9745166e79de775af0949817283f2ea0"
ensure_node "https://github.com/rgthree/rgthree-comfy.git" "rgthree-comfy"
ensure_node "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git" "ComfyUI-VideoHelperSuite"

"$PYTHON_BIN" -m pip install --no-cache-dir "huggingface_hub>=0.34" hf-xet requests

echo "[nodes] Exact workflow node set is ready."
