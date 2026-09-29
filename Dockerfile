FROM pytorch/pytorch:2.10.0-cuda13.0-cudnn9-devel

# MiniMax H3 Vast dashboard image
ARG DEBIAN_FRONTEND=noninteractive
ARG COMFY_REF=8d534945ebd53cff61e8def81757c6a6c1b9cf2d

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility \
    CUDA_HOME=/usr/local/cuda \
    COMFYUI_ROOT=/opt/ComfyUI \
    WORKSPACE=/workspace \
    HF_HOME=/workspace/cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/workspace/cache/huggingface/hub \
    TORCH_HOME=/workspace/cache/torch \
    TRITON_CACHE_DIR=/workspace/cache/triton \
    XDG_CACHE_HOME=/workspace/cache \
    MINIMAX_H3_REFERENCE_SHEETS_DIR=/workspace/ComfyUI/user/default/minimax_h3/reference_sheets

RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs curl wget aria2 rsync unzip jq ca-certificates \
    ffmpeg \
    build-essential ninja-build cmake pkg-config \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
    && git lfs install \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt
RUN git clone https://github.com/Comfy-Org/ComfyUI.git ComfyUI \
    && cd ComfyUI \
    && git checkout "${COMFY_REF}" \
    && python -m pip install -r requirements.txt

RUN python -m pip install \
    "huggingface_hub>=0.34" hf-xet jupyterlab psutil

COPY scripts/install_custom_nodes.sh /tmp/install_custom_nodes.sh
RUN chmod +x /tmp/install_custom_nodes.sh \
    && /tmp/install_custom_nodes.sh /opt/ComfyUI/custom_nodes \
    && rm /tmp/install_custom_nodes.sh

RUN mkdir -p /opt/seed/custom_nodes \
    && rsync -a /opt/ComfyUI/custom_nodes/ /opt/seed/custom_nodes/

RUN mkdir -p /opt/seed/workflows \
    && curl -L --fail --retry 5 \
       https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/templates/video_minimax_h3_t2v.json \
       -o /opt/seed/workflows/MiniMax-H3-T2V-Official.json \
    && curl -L --fail --retry 5 \
       https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/templates/video_minimax_h3_i2v.json \
       -o /opt/seed/workflows/MiniMax-H3-I2V-Official.json \
    && curl -L --fail --retry 5 \
       https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/templates/video_minimax_h3_r2v.json \
       -o /opt/seed/workflows/MiniMax-H3-R2V-Official.json

COPY scripts/download_models.py /usr/local/bin/download_minimax_models.py
COPY scripts/dashboard.py /usr/local/bin/minimax-dashboard.py
COPY scripts/entrypoint.sh /usr/local/bin/minimax-entrypoint.sh
RUN chmod +x \
    /usr/local/bin/minimax-entrypoint.sh \
    /usr/local/bin/download_minimax_models.py \
    /usr/local/bin/minimax-dashboard.py

# 8080 = dashboard, 8188 = ComfyUI, 8888 = JupyterLab
EXPOSE 8080 8188 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8080/api/health >/dev/null \
      || curl -fsS http://127.0.0.1:8188/system_stats >/dev/null \
      || exit 1

ENTRYPOINT ["/usr/local/bin/minimax-entrypoint.sh"]
