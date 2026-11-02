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

## Automatic ComfyUI updates

New pods fetch the latest official ComfyUI default-branch commit at startup and install its requirements before launching. Restarts check again. This includes frontend updates specified by ComfyUI. Models, workflows and custom nodes remain persistent and are not updated by this step. Existing CUDA PyTorch package versions are constrained so pip cannot silently replace them.

Progress appears in Vast instance logs and `/workspace/logs/container.log`. If GitHub is unavailable, startup uses the installed core. A dependency conflict stops startup with an error instead of launching an inconsistent installation. Latest upstream code may require newer dependencies or break custom-node compatibility. Set `UPDATE_COMFYUI=0` to skip updates.

Use the newly built `ghcr.io/ftbpro04/vast-minimax-h3:latest` image for this behavior; existing containers do not receive changed startup scripts automatically.

## Singularity V2 × 10Eros Max: PRISM-DMAD-PDMD

Civitai model version **3445524** is included in the `full`, `core`, `ref2va`, and `fl2va` download profiles. The pinned author download is `PRISM_DMAD_PDMD_int8.safetensors` (20,284,678,584 bytes, about 20.3 GB); its SHA256 matches Civitai. Downloads are checked against that size and checksum. Verified files are reused on restart. No Civitai token is needed for this public author mirror.

Open **MiniMax-H3-PRISM-DMAD-PDMD-I2V-PowerLoRA.json** in saved workflows. Upload a starting image, set aspect ratio/seconds and describe motion. The image feeds H3 reference conditioning and a frame-zero guide. This is an adaptation for the Ref2VA-based merge, not an author-supplied workflow. Precise first-frame fidelity and LoRA behavior still need a GPU generation test.

Preset: Euler, BetaSamplingScheduler alpha 0.5 / beta 0.7 (Beta57), 8 steps, video/audio shifts 12/3, CFG 1. The rgthree Power LoRA Loader is connected before both the sampler schedule and guider. All LoRAs start disabled. Add compatible H3 concept/style LoRAs there; the checkpoint already includes acceleration, so do not enable the old Turbo LoRA on top of it. Put your own LoRA files under `/workspace/ComfyUI/models/loras/`.

The template reuses its H3 video/audio VAEs, Qwen text encoder, rgthree and helper nodes. ComfyUI is built from commit `bb878b9ee35274e67931634ba9e8c338f8c06035` so the native guide, shift and Beta scheduler nodes are present even with startup updates disabled. A CPU registration check runs during the Docker build. No additional inference server or prompt LLM is required by this workflow.

Image tag after publication: `ghcr.io/ftbpro04/vast-minimax-h3:singularity-prism-dmad-20261102-r2` (also published as `latest`). Existing running containers need the new image to receive the installer/workflow. Preserve the `/workspace` volume.

Sources: https://civitai.red/models/3019421?modelVersionId=3445524 and https://huggingface.co/OliviaRossi/Minimax-h3_Singularity-x-10Eros-Max_PRISM .
