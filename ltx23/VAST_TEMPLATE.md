# Vast.ai Template — LTX 2.3 Dashboard

Base image:

```
antilopax/ltx23:v14
```

Published wrapper image:

```
ghcr.io/ftbpro04/vast-ltx23:latest
```

## What the wrapper changes

The inspected `v14` image uses:

- ENTRYPOINT: `/opt/nvidia/nvidia_entrypoint.sh`
- CMD: `/app/startup_unix.sh`
- ComfyUI root: `/app/ComfyUI`
- ComfyUI port: `8188`
- Jupyter port: `8888`
- CUDA runtime: `12.8`

The wrapper runs before the original startup only to:

1. Redirect large/user-writable ComfyUI folders into persistent `/workspace/ComfyUI`.
2. Start the dashboard on port `8080`.
3. Capture startup output to `/workspace/logs/ltx23-container.log`.
4. Chain into the exact original NVIDIA entrypoint and original `/app/startup_unix.sh` command.

## Vast template fields

### Identification

Template Name:

```
LTX 2.3 - Dashboard
```

Template Description:

```
LTX 2.3 based on antilopax/ltx23:v14 with persistent models, ComfyUI/Jupyter dashboard and live logs
```

### Docker Repository And Environment

Image Path:Tag:

```
ghcr.io/ftbpro04/vast-ltx23:latest
```

Version Tag:

```
latest
```

### Docker Options

Leave the free-form Docker options box blank.

### Ports

Add these as TCP only:

- `8080` — Dashboard
- `8188` — ComfyUI
- `8888` — JupyterLab

### Environment Variables

Recommended:

```
WORKSPACE=/workspace
LTX23_PERSIST_ROOT=/workspace/ComfyUI
ENABLE_DASHBOARD=1
DASHBOARD_PORT=8080
COMFY_PORT=8188
JUPYTER_PORT=8888
```

Optional dashboard password:

```
DASHBOARD_PASSWORD=your-password
```

### Launch Mode

Select:

```
Docker ENTRYPOINT
```

Leave "Args to pass to docker ENTRYPOINT" blank.

### On-start Script

Leave it completely blank. The wrapper now handles persistence and dashboard startup before calling the original LTX startup script.

### Disk / Volume

Recommended starting point:

- Container disk: `50 GB`
- Persistent volume: `200 GB+`
- Mount the persistent volume at: `/workspace`

The wrapper redirects these folders into the persistent volume:

- `/app/ComfyUI/models` → `/workspace/ComfyUI/models`
- `/app/ComfyUI/input` → `/workspace/ComfyUI/input`
- `/app/ComfyUI/output` → `/workspace/ComfyUI/output`
- `/app/ComfyUI/user` → `/workspace/ComfyUI/user`

This is important because it lets downloaded LTX checkpoints survive when you create a new Vast instance using the same volume.

## Model download defaults inherited from v14

The inspected base image contains these defaults:

```
DOWNLOAD_LTX23_DISTILLED=true
DOWNLOAD_LTX23_FULL_FP8=true
DOWNLOAD_LTX23_FULL_BF16=false
DOWNLOAD_LTX23_UPSCALERS=true
NSFW=false
SKIP_COMFYUI_UPDATE=true
SKIP_NODE_UPDATES=true
```

### Lower-bandwidth option

If your workflow only needs the distilled model, add:

```
DOWNLOAD_LTX23_DISTILLED=true
DOWNLOAD_LTX23_FULL_FP8=false
DOWNLOAD_LTX23_FULL_BF16=false
DOWNLOAD_LTX23_UPSCALERS=true
```

If your workflow uses the Full FP8 checkpoint, leave `DOWNLOAD_LTX23_FULL_FP8=true`.

## CUDA note

The base image uses CUDA 12.8. A Vast host with a newer CUDA-capable NVIDIA driver, including hosts advertising CUDA 13.1+, can run older CUDA-runtime applications through NVIDIA driver backward compatibility. The wrapper does not replace the base image's CUDA stack.

## Visibility

Keep the template Private while testing.
