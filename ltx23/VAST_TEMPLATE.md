# Vast.ai Template — LTX 2.3 Exact Workflow / CUDA 13

## Image

```
ghcr.io/ftbpro04/vast-ltx23:cuda13-v1
```

## Identification

Template Name:

```
LTX 2.3 - Exact Workflow CUDA 13
```

Template Description:

```
LTX 2.3 10Eros triple-pass I2V using the Antilopax v14 ComfyUI/LTX tree on PyTorch 2.10 + CUDA 13.0, with exact workflow nodes/models, dashboard and Jupyter
```

## GPU / host requirement

Choose a Vast offer whose **CUDA Max Supported is 13.0 or newer**.

The container itself is built on:

```
PyTorch 2.10
CUDA 13.0
cuDNN 9
```

The Docker build contains a hard check and will fail instead of publishing if Torch is not using CUDA 13.x.

## Ports

TCP only:

- `18080` — Dashboard
- `8188` — ComfyUI
- `8888` — JupyterLab

Do not expose port 8080 for this template.

## Environment Variables

Recommended:

```
WORKSPACE=/workspace
LTX23_PERSIST_ROOT=/workspace/ComfyUI
ENABLE_DASHBOARD=1
ENABLE_JUPYTER=1
DASHBOARD_PORT=18080
COMFY_PORT=8188
JUPYTER_PORT=8888
DOWNLOAD_WORKFLOW_MODELS=1
```

Optional:

```
HF_TOKEN=<your Hugging Face token if needed>
DASHBOARD_PASSWORD=<optional password>
COMFY_EXTRA_ARGS=<optional additional ComfyUI arguments>
DOWNLOAD_WORKFLOW_MODELS=0
```

Use `DOWNLOAD_WORKFLOW_MODELS=0` only when the persistent volume already contains all five required files.

## Launch Mode

Select:

```
Docker ENTRYPOINT
```

Leave Docker ENTRYPOINT args blank.

Leave On-start Script blank.

This image no longer invokes Antilopax's NVIDIA entrypoint or relies on its inherited CMD. ComfyUI is launched directly by our stable entrypoint, eliminating the empty-command restart loop seen in the previous image.

## Disk / Volume

Recommended:

- Container disk: 50 GB
- Persistent volume: 150 GB minimum; 200 GB recommended
- Mount volume at: `/workspace`

## Exact automatic downloads

Approximately 62 GB total:

- `10Eros_v1_bf16.safetensors`
- `gemma_3_12B_it_fp8_e4m3fn.safetensors`
- `ltx-2.3-spatial-upscaler-x2-1.1.safetensors`
- `ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors`
- `ltx23_edit_anything_global_rank128_v1_9000steps_adamw.safetensors`

Existing files are skipped when the same persistent `/workspace` volume is attached.

## Failure behavior

If ComfyUI itself exits, the container intentionally remains alive. It does **not** restart ComfyUI in a loop. The dashboard and logs stay available on port 18080 so the error can be diagnosed.

## Visibility

Keep the Vast template Private while testing.
