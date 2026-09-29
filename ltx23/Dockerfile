FROM antilopax/ltx23:v14

ENV LTX23_BASE_IMAGE=antilopax/ltx23:v14 \
    WORKSPACE=/workspace \
    LTX23_PERSIST_ROOT=/workspace/ComfyUI \
    ENABLE_DASHBOARD=1 \
    DASHBOARD_PORT=18080 \
    COMFY_PORT=8188 \
    JUPYTER_PORT=8888 \
    DOWNLOAD_WORKFLOW_MODELS=1 \
    DOWNLOAD_LTX23_DISTILLED=false \
    DOWNLOAD_LTX23_FULL_FP8=false \
    DOWNLOAD_LTX23_FULL_BF16=false \
    DOWNLOAD_LTX23_UPSCALERS=false \
    HF_HOME=/workspace/hf-cache \
    HUGGINGFACE_HUB_CACHE=/workspace/hf-cache/hub

COPY install_workflow_nodes.sh /tmp/install_workflow_nodes.sh
RUN chmod +x /tmp/install_workflow_nodes.sh \
    && /tmp/install_workflow_nodes.sh /app/ComfyUI \
    && rm /tmp/install_workflow_nodes.sh

COPY dashboard.py /usr/local/bin/ltx23-dashboard.py
COPY download_workflow_models.py /usr/local/bin/download_ltx23_workflow_models.py
COPY entrypoint.sh /usr/local/bin/ltx23-wrapper-entrypoint.sh
RUN chmod +x \
      /usr/local/bin/ltx23-dashboard.py \
      /usr/local/bin/download_ltx23_workflow_models.py \
      /usr/local/bin/ltx23-wrapper-entrypoint.sh \
    && bash -n /usr/local/bin/ltx23-wrapper-entrypoint.sh \
    && python3 -m py_compile \
      /usr/local/bin/ltx23-dashboard.py \
      /usr/local/bin/download_ltx23_workflow_models.py \
    && test -x /opt/nvidia/nvidia_entrypoint.sh \
    && test -x /app/startup_unix.sh \
    && test -f /app/ComfyUI/main.py

EXPOSE 18080 8188 8888

# Preserve the original Antilopax startup. The wrapper only adds persistence,
# the dashboard, exact workflow nodes, and the exact five active workflow models.
ENTRYPOINT ["/usr/local/bin/ltx23-wrapper-entrypoint.sh"]
