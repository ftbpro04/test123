FROM antilopax/ltx23:v14

ENV LTX23_BASE_IMAGE=antilopax/ltx23:v14 \
    WORKSPACE=/workspace \
    LTX23_PERSIST_ROOT=/workspace/ComfyUI \
    ENABLE_DASHBOARD=1 \
    DASHBOARD_PORT=8080 \
    COMFY_PORT=8188 \
    JUPYTER_PORT=8888

COPY dashboard.py /usr/local/bin/ltx23-dashboard.py
COPY entrypoint.sh /usr/local/bin/ltx23-wrapper-entrypoint.sh
RUN chmod +x /usr/local/bin/ltx23-dashboard.py /usr/local/bin/ltx23-wrapper-entrypoint.sh \
    && bash -n /usr/local/bin/ltx23-wrapper-entrypoint.sh \
    && python3 -m py_compile /usr/local/bin/ltx23-dashboard.py \
    && test -x /opt/nvidia/nvidia_entrypoint.sh \
    && test -x /app/startup_unix.sh \
    && test -f /app/ComfyUI/main.py

EXPOSE 8080 8188 8888

# The inspected v14 image uses:
#   ENTRYPOINT ["/opt/nvidia/nvidia_entrypoint.sh"]
#   CMD ["/app/startup_unix.sh"]
# Our wrapper performs persistence/dashboard setup, then chains into the exact
# original NVIDIA entrypoint with the inherited CMD untouched.
ENTRYPOINT ["/usr/local/bin/ltx23-wrapper-entrypoint.sh"]
