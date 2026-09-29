# Vast.ai Template — LTX 2.3 Dashboard

Base image: `antilopax/ltx23:v14`

Published wrapper image:

```
ghcr.io/ftbpro04/vast-ltx23:latest
```

The wrapper intentionally keeps the base image's original Docker ENTRYPOINT and CMD unchanged. It only adds the LTX 2.3 dashboard.

## Vast template fields

### Identification
- Template Name: `LTX 2.3 - Dashboard`
- Template Description: `LTX 2.3 based on antilopax/ltx23:v14 with ComfyUI/Jupyter dashboard and persistent workspace`

### Docker Repository And Environment
- Image Path:Tag: `ghcr.io/ftbpro04/vast-ltx23:latest`
- Version Tag: `latest`

### Docker Options
Leave the free-form Docker options field blank.

### Ports
Add these as TCP:
- `8080` — dashboard
- `8188` — ComfyUI
- `8888` — JupyterLab

### Environment Variables
```
WORKSPACE=/workspace
DASHBOARD_PORT=8080
COMFY_PORT=8188
JUPYTER_PORT=8888
LTX23_BASE_IMAGE=antilopax/ltx23:v14
```

Optional:
```
DASHBOARD_PASSWORD=choose-a-password
```

### Launch Mode
Select:
```
Docker ENTRYPOINT
```

Leave "Args to pass to docker ENTRYPOINT" blank.

### On-start Script
Paste:
```bash
mkdir -p /workspace/logs
pkill -f ltx23-dashboard.py 2>/dev/null || true
nohup python3 /usr/local/bin/ltx23-dashboard.py >> /workspace/logs/ltx23-dashboard.log 2>&1 &
```

This starts only the dashboard. The original `antilopax/ltx23:v14` ENTRYPOINT/CMD still handles the actual LTX/ComfyUI environment.

### Disk
Recommended starting point:
- Container disk: `50 GB`
- Persistent volume: `200 GB+`
- Mount the persistent volume at: `/workspace`

Use a larger volume if you keep multiple checkpoints, LoRAs, input videos, and outputs.

### Visibility
Private while testing.

## Bandwidth note
Reuse the same persistent `/workspace` volume whenever possible so any models stored there do not need to be downloaded again on each new machine. The wrapper itself does not add an automatic model downloader.
