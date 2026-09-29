# Vast.ai MiniMax H3 + Control Panel

This version adds a lightweight landing page on **port 8080** to the existing MiniMax H3 Vast.ai image.

## Control panel features

- One-click **Open ComfyUI** button.
- One-click **Open JupyterLab** button with the container's Jupyter token included automatically.
- Automatic use of Vast's current random external port mappings.
- Live ComfyUI/container, model-download, Jupyter and dashboard logs.
- GPU utilization, VRAM, temperature and power readout.
- `/workspace` disk usage.
- Model profile and per-model state: queued, downloading, present/downloaded, or error.
- Overall model-ready progress bar.
- No additional web framework; the dashboard uses Python's standard library.
- Optional HTTP password protection with `DASHBOARD_PASSWORD`.

## Ports

| Container port | Service |
|---|---|
| `8080` | MiniMax H3 Control Panel |
| `8188` | ComfyUI |
| `8888` | JupyterLab |

For the Vast template use:

```text
-p 8080:8080 -p 8188:8188 -p 8888:8888
```

Then open the public mapping for **8080**. You should not need to manually rebuild the ComfyUI or Jupyter URLs anymore.

### Optional dashboard password

For an internet-exposed instance, set `DASHBOARD_PASSWORD` in Vast account environment variables. The browser username is `minimax`; the password is whatever value you set. Leave the variable unset if you prefer the dashboard to open without a login prompt.

## Persistence

The existing `/workspace` persistence is preserved. Logs are stored in:

```text
/workspace/logs/container.log
/workspace/logs/model-download.log
/workspace/logs/model-status.json
/workspace/logs/jupyter.log
/workspace/logs/dashboard.log
```

Jupyter's generated token remains in:

```text
/workspace/.jupyter_token
```

## Build

Push this repository to your GitHub account. The included GitHub Action builds:

```text
ghcr.io/YOUR_GITHUB_USERNAME/vast-minimax-h3:latest
```

Use `VAST_TEMPLATE.md` for the Vast settings.

## Existing MiniMax behavior retained

- PyTorch 2.10 / CUDA 13 base.
- Persistent ComfyUI models, custom nodes, input, output and user folders under `/workspace`.
- Resumable Hugging Face downloads.
- `MINIMAX_PROFILE` support (`full`, `core`, `fl2va`, `ref2va`, `none`).
- ComfyUI Manager, rgthree Power LoRA Loader, KJNodes, VideoHelperSuite, MiniMax helpers, QwenVL tools, RIFE TensorRT and TensorRT upscaling.
