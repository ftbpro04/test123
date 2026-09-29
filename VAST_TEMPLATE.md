# Vast.ai template settings

## Recommended settings

- **Template name:** MiniMax H3 - Dashboard
- **Image:** `ghcr.io/YOUR_GITHUB_USERNAME/vast-minimax-h3:latest`
- **Launch mode:** `docker ENTRYPOINT`
- **Ports:** `8080/tcp`, `8188/tcp`, `8888/tcp`
- **Container disk:** 35-50 GB
- **Recommended volume:** 180-250 GB
- **Volume mount/install path:** `/workspace`
- **Visibility:** Private while testing

Use Docker create/run options:

```text
-p 8080:8080 -p 8188:8188 -p 8888:8888
```

Vast maps these container ports to available public ports. Port `8080` is the landing/control panel; from there the **Open ComfyUI** and **Open JupyterLab** buttons use the `VAST_TCP_PORT_8188` and `VAST_TCP_PORT_8888` mappings automatically.

Do **not** select Vast's "Jupyter + SSH" launch mode. This image starts its own dashboard, ComfyUI and JupyterLab.

## Suggested environment variables

```text
MINIMAX_PROFILE=full
DOWNLOAD_MODELS=1
MODEL_DOWNLOAD_WORKERS=2
ENABLE_DASHBOARD=1
DASHBOARD_PORT=8080
ENABLE_JUPYTER=1
COMFY_PORT=8188
JUPYTER_PORT=8888
```

Optional but recommended for an internet-exposed instance:

```text
DASHBOARD_PASSWORD=choose-a-password
```

If set, the dashboard uses browser Basic Auth with username `minimax`.

Put `HF_TOKEN` in Vast **Account Settings -> Environment Variables**, not in a public/shared template.

## How you use it

1. Start the Vast instance.
2. Open the web UI for container port **8080** from Vast's instance/port controls.
3. The MiniMax H3 Control Panel appears.
4. Click **Open ComfyUI** or **Open JupyterLab**.
5. Model download state, GPU/VRAM, disk usage and live logs remain visible on the same page.
