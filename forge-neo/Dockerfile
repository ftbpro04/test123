FROM pytorch/pytorch:2.10.0-cuda13.0-cudnn9-devel
ARG NEO_REF=4f4284b02a5c814b81c328c64ed7e99a139f21ef
ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1 WORKSPACE=/workspace NEO_PERSIST_ROOT=/workspace/neo-data DASHBOARD_PORT=18080 WEBUI_PORT=7860 JUPYTER_PORT=8888
RUN apt-get update && apt-get install -y --no-install-recommends git curl aria2 ffmpeg libgl1 libglib2.0-0 tini rsync python3-venv && rm -rf /var/lib/apt/lists/*
RUN python -c "import importlib.metadata as m;open('/opt/constraints.txt','w').write('\n'.join(p+'=='+m.version(p) for p in ['torch','torchvision']))"
RUN python -m venv --system-site-packages /opt/venv
ENV VIRTUAL_ENV=/opt/venv PATH=/opt/venv/bin:$PATH PIP_CONSTRAINT=/opt/constraints.txt
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel
RUN git clone https://github.com/Haoming02/sd-webui-forge-classic.git /opt/forge-neo && cd /opt/forge-neo && git checkout "$NEO_REF"
COPY . /opt/template
RUN python /opt/template/install_extensions.py
WORKDIR /opt/forge-neo
# Follow Neo's own installer order: install Gradio, then enforce Neo requirements.
RUN python -m pip install --no-cache-dir 'gradio==4.40.0' 'gradio_rangeslider==0.0.8'
RUN python -m pip install --no-cache-dir -r requirements.txt jupyterlab requests && python launch.py --skip-torch-cuda-test --exit
RUN python -c "import gradio, PIL, torch; from gradio import Blocks; print(gradio.__version__, PIL.__version__)"
RUN python -c "import torch; assert torch.version.cuda.startswith('13.'); print(torch.__version__,torch.version.cuda)" && bash -n /opt/template/entrypoint.sh
EXPOSE 18080 7860 8888
ENTRYPOINT ["/usr/bin/tini","-g","--","bash","/opt/template/entrypoint.sh"]

LABEL org.opencontainers.image.source="https://github.com/ftbpro04/test123"
