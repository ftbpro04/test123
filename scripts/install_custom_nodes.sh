#!/usr/bin/env bash
set -Eeuo pipefail

DEST="${1:-/opt/ComfyUI/custom_nodes}"
mkdir -p "$DEST"

clone_node () {
  local url="$1"
  local name="$2"
  local ref="${3:-}"
  echo "==> Installing $name"
  if [[ ! -d "$DEST/$name/.git" ]]; then
    git clone --depth 1 "$url" "$DEST/$name"
  fi
  if [[ -n "$ref" ]]; then
    git -C "$DEST/$name" fetch --depth 1 origin "$ref"
    git -C "$DEST/$name" checkout --detach "$ref"
  fi
  if [[ -f "$DEST/$name/requirements.txt" ]]; then
    python -m pip install -r "$DEST/$name/requirements.txt"
  fi
}

clone_node "https://github.com/Comfy-Org/ComfyUI-Manager.git" "ComfyUI-Manager"
clone_node "https://github.com/MoonGoblinDev/Civicomfy.git" "Civicomfy"
clone_node "https://github.com/huchukato/ComfyUI-HuggingFace.git" "ComfyUI-HuggingFace"
python -m pip install "huggingface_hub>=0.20.0" "requests>=2.25.0"
clone_node "https://github.com/rgthree/rgthree-comfy.git" "rgthree-comfy" "bc48c6aaeca87bedbc14245d89f9bc6be37a630e"
clone_node "https://github.com/kijai/ComfyUI-KJNodes.git" "ComfyUI-KJNodes" "aa2b5ea5e7f61b51f5d26d726f23c1d74e951016"
clone_node "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git" "ComfyUI-VideoHelperSuite"
clone_node "https://github.com/ethanfel/ComfyUI-MiniMax-H3-Guide.git" "ComfyUI-MiniMax-H3-Guide"
clone_node "https://github.com/huchukato/ComfyUI-QwenVL-Mod.git" "ComfyUI-QwenVL-Mod" "d3240c85b11eddefde11fd832f019d1ba02ade5a"
clone_node "https://github.com/huchukato/ComfyUI-RIFE-TensorRT-Auto.git" "ComfyUI-RIFE-TensorRT-Auto"
clone_node "https://github.com/huchukato/ComfyUI-Upscaler-TensorRT-Auto.git" "ComfyUI-Upscaler-TensorRT-Auto"

echo "==> Custom-node installation finished successfully"

clone_node "https://github.com/cicalooo/ComfyUI-H3-PowerLoraStack.git" "ComfyUI-H3-PowerLoraStack" "55da4ee624a6d730c3853cd7309892ec38257a60"

clone_node "https://github.com/LBH-123-AI/Comfyui_Minimax_h3_latent_Upscaler.git" "Comfyui_Minimax_h3_latent_Upscaler" "f34cadb19f10fee7e36091b690cac39b4eb40573"

clone_node "https://github.com/LordLocksley/ComfyUI-Lokken-VideoTools.git" "ComfyUI-Lokken-VideoTools" "6e9ba890b4ffdd9f378652bd608559c918de8d6e"

clone_node "https://github.com/Comfy-Org/ComfyUI_Nvidia_VFX_Nodes.git" "ComfyUI_Nvidia_VFX_Nodes" "38d790ded00650681fa3645362efe28c8560cf40"
