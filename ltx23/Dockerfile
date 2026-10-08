FROM pytorch/pytorch:2.10.0-cuda13.0-cudnn9-devel

ARG DEBIAN_FRONTEND=noninteractive
ARG COMFY_REF=52f98af2e2e42c421070a3e147c161c47cdeaf22

ENV PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    WORKSPACE=/workspace \
    LTX23_PERSIST_ROOT=/workspace/ltx23-data \
    ENABLE_DASHBOARD=1 \
    ENABLE_JUPYTER=1 \
    DASHBOARD_PORT=18080 \
    COMFY_PORT=8188 \
    JUPYTER_PORT=8888 \
    DOWNLOAD_WORKFLOW_MODELS=1 \
    HF_HOME=/tmp/huggingface \
    HUGGINGFACE_HUB_CACHE=/tmp/huggingface/hub \
    TORCH_HOME=/tmp/torch-cache \
    TRITON_CACHE_DIR=/tmp/triton-cache \
    LTX23_BASE_IMAGE="Clean ComfyUI + PyTorch 2.10 CUDA 13.0" \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

RUN apt-get update && apt-get install -y --no-install-recommends \
      git git-lfs curl wget aria2 rsync unzip jq ffmpeg \
      build-essential ninja-build cmake ca-certificates tini python3-venv \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv --system-site-packages /opt/venv \
    && /opt/venv/bin/python -m pip install --no-cache-dir --upgrade pip setuptools wheel

WORKDIR /opt
RUN git clone https://github.com/Comfy-Org/ComfyUI.git \
    && cd ComfyUI \
    && git checkout "$COMFY_REF" \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip install --no-cache-dir \
         jupyterlab psutil "huggingface_hub>=0.34" hf-xet requests

COPY install_workflow_nodes.sh /tmp/install_workflow_nodes.sh
RUN chmod +x /tmp/install_workflow_nodes.sh \
    && /tmp/install_workflow_nodes.sh /opt/ComfyUI \
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

WORKDIR /opt/ComfyUI
EXPOSE 18080 8188 8888

ENTRYPOINT ["/usr/bin/tini","--","/usr/local/bin/ltx23-entrypoint.sh"]
