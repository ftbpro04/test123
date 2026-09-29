FROM antilopax/ltx23:v14

# Keep the base image's original ENTRYPOINT and CMD unchanged.
ENV LTX23_BASE_IMAGE=antilopax/ltx23:v14 \
    WORKSPACE=/workspace \
    DASHBOARD_PORT=8080 \
    COMFY_PORT=8188 \
    JUPYTER_PORT=8888

COPY dashboard.py /usr/local/bin/ltx23-dashboard.py
RUN chmod +x /usr/local/bin/ltx23-dashboard.py

EXPOSE 8080 8188 8888
