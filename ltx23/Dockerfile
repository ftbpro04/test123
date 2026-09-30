# Use Antilopax v14 as the source for its working LTX/ComfyUI tree,
# but run it on a real CUDA 13.0 / PyTorch 2.10 userspace.
FROM docker.io/antilopax/ltx23:v14 AS antilopax

FROM pytorch/pytorch:2.10.0-cuda13.0-cudnn9-devel

ARG DEBIAN_FRONTEND=noninteractive

ENV PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    WORKSPACE=/workspace \
    LTX23_PERSIST_ROOT=/workspace/ComfyUI \
    ENABLE_DASHBOARD=1 \
    DASHBOARD_PORT=18080 \
    COMFY_PORT=8188 \
    JUPYTER_PORT=8888 \
    DOWNLOAD_WORKFLOW_MODELS=1 \
    HF_HOME=/workspace/hf-cache \
    HUGGINGFACE_HUB_CACHE=/workspace/hf-cache/hub \
    TORCH_HOME=/workspace/torch-cache \
    TRITON_CACHE_DIR=/workspace/triton-cache \
    LTX23_BASE_IMAGE="Antilopax v14 app on PyTorch 2.10 CUDA 13.0"

RUN apt-get update && apt-get install -y --no-install-recommends \
      git git-lfs curl wget aria2 rsync unzip jq ffmpeg \
      build-essential ninja-build cmake ca-certificates \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

# Preserve the ComfyUI/LTX application tree from the requested Antilopax image,
# but discard its mutable model/custom-node data so our exact workflow set is clean.
COPY --from=antilopax /app/ComfyUI /app/ComfyUI

RUN rm -rf /app/ComfyUI/models /app/ComfyUI/custom_nodes \
    && mkdir -p /app/ComfyUI/models /app/ComfyUI/custom_nodes \
    && python -m pip install --no-cache-dir -r /app/ComfyUI/requirements.txt \
    && python -m pip install --no-cache-dir \
         jupyterlab psutil "huggingface_hub>=0.34" hf-xet requests

COPY install_workflow_nodes.sh /tmp/install_workflow_nodes.sh
RUN chmod +x /tmp/install_workflow_nodes.sh \
    && /tmp/install_workflow_nodes.sh /app/ComfyUI \
    && rm /tmp/install_workflow_nodes.sh

COPY dashboard.py /usr/local/bin/ltx23-dashboard.py
COPY download_workflow_models.py /usr/local/bin/download_ltx23_workflow_models.py
COPY entrypoint.sh /usr/local/bin/ltx23-entrypoint.sh

RUN chmod +x \
      /usr/local/bin/ltx23-dashboard.py \
      /usr/local/bin/download_ltx23_workflow_models.py \
      /usr/local/bin/ltx23-entrypoint.sh \
    && bash -n /usr/local/bin/ltx23-entrypoint.sh \
    && python -m py_compile \
      /usr/local/bin/ltx23-dashboard.py \
      /usr/local/bin/download_ltx23_workflow_models.py \
    && python - <<'PY'
import torch
print("Torch:", torch.__version__)
print("Torch CUDA:", torch.version.cuda)
assert str(torch.version.cuda).startswith("13."), torch.version.cuda
PY

WORKDIR /app/ComfyUI

EXPOSE 18080 8188 8888

ENTRYPOINT ["/usr/local/bin/ltx23-entrypoint.sh"]
