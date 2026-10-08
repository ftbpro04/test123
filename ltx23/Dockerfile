FROM pytorch/pytorch:2.10.0-cuda13.0-cudnn9-devel
ARG DEBIAN_FRONTEND=noninteractive
ARG COMFY_REF=52f98af2e2e42c421070a3e147c161c47cdeaf22
ENV PYTHONUNBUFFERED=1 \
    NVIDIA_VISIBLE_DEVICES=all \
    NVIDIA_DRIVER_CAPABILITIES=compute,utility,graphics \
    WORKSPACE=/workspace \
    LTX23_PERSIST_ROOT=/workspace/ltx23-data \
    ENABLE_DASHBOARD=1 ENABLE_JUPYTER=1 \
    DASHBOARD_PORT=18080 COMFY_PORT=8188 JUPYTER_PORT=8888 \
    DOWNLOAD_WORKFLOW_MODELS=1 \
    HF_HOME=/tmp/huggingface HF_HUB_CACHE=/tmp/huggingface/hub \
    HF_XET_CACHE=/tmp/huggingface/xet TORCH_HOME=/tmp/torch-cache \
    TRITON_CACHE_DIR=/tmp/triton-cache XDG_CACHE_HOME=/tmp/xdg-cache \
    PIP_NO_CACHE_DIR=1 GIT_LFS_SKIP_SMUDGE=1 \
    VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH \
    PIP_CONSTRAINT=/opt/ltx23/torch-constraints.txt
RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs curl ffmpeg ca-certificates tini python3-venv \
    build-essential ninja-build cmake libgl1 libglib2.0-0 libegl1 libgles2 \
    libvulkan1 mesa-vulkan-drivers libx11-6 libxcb1 \
    && rm -rf /var/lib/apt/lists/*
COPY . /opt/ltx23/
RUN python -m venv --system-site-packages /opt/venv \
    && python - <<'PY'
from importlib.metadata import version,PackageNotFoundError
from pathlib import Path
rows=[]
for name in ('torch','torchvision','torchaudio','triton'):
    try: rows.append(f'{name}=={version(name)}')
    except PackageNotFoundError: pass
Path('/opt/ltx23/torch-constraints.txt').write_text('\n'.join(rows)+'\n')
PY
RUN python -m pip install --upgrade pip setuptools wheel \
    && mkdir /opt/ComfyUI \
    && git -C /opt/ComfyUI init -q \
    && git -C /opt/ComfyUI fetch --depth 1 https://github.com/Comfy-Org/ComfyUI.git "$COMFY_REF" \
    && git -C /opt/ComfyUI checkout --detach FETCH_HEAD \
    && python -m pip install -r /opt/ComfyUI/requirements.txt \
    && python -m pip install jupyterlab psutil requests huggingface_hub \
    && bash /opt/ltx23/install_workflow_nodes.sh /opt/ComfyUI \
    && python -m pip check \
    && python /opt/ltx23/check_build.py --runtime \
    && bash -n /opt/ltx23/entrypoint.sh \
    && python -m compileall -q /opt/ltx23 \
    && test -f /opt/ComfyUI/main.py \
    && chmod +x /opt/ltx23/entrypoint.sh \
    && rm -rf /opt/ComfyUI/models /opt/ComfyUI/input /opt/ComfyUI/output /opt/ComfyUI/user \
    && rm -rf /root/.cache/pip /tmp/huggingface /tmp/torch-cache
WORKDIR /opt/ComfyUI
EXPOSE 18080 8188 8888
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('DASHBOARD_PORT','18080')+'/api/health',timeout=3)"
ENTRYPOINT ["/usr/bin/tini","--","/opt/ltx23/entrypoint.sh"]
CMD []
