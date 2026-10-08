# Vast.ai Template — LTX 2.3 CLEAN CUDA 13

## Image

```
ghcr.io/ftbpro04/vast-ltx23:clean-cuda13-v2
```

## Host requirement

Choose a Vast offer with CUDA Max Supported 13.0 or newer.

## Ports

TCP only:

- 18080 — Dashboard
- 8188 — ComfyUI
- 8888 — JupyterLab

## Environment

```
WORKSPACE=/workspace
LTX23_PERSIST_ROOT=/workspace/ltx23-data
ENABLE_DASHBOARD=1
ENABLE_JUPYTER=1
DASHBOARD_PORT=18080
COMFY_PORT=8188
JUPYTER_PORT=8888
DOWNLOAD_WORKFLOW_MODELS=1
```

Optional:

```
HF_TOKEN=<token if required>
DASHBOARD_PASSWORD=<optional>
COMFY_EXTRA_ARGS=<optional>
```

## Launch mode

Docker ENTRYPOINT

Leave ENTRYPOINT args blank.
Leave On-start Script blank.

## Storage

Container disk: 40–50 GB.

Persistent volume: 100 GB minimum, 150 GB recommended.
Mount the volume at /workspace.

Only these directories are persistent under /workspace/ltx23-data:

- models
- input
- output
- user

Hugging Face, Torch and Triton caches are NOT stored persistently.

The automatic downloader keeps temporary partial downloads under
/workspace/ltx23-data/.downloads and removes each temporary directory after
the corresponding model is moved into its final models path.

## Exact models

Only the five active workflow files are downloaded:

- 10Eros_v1_bf16.safetensors
- gemma_3_12B_it_fp8_e4m3fn.safetensors
- ltx-2.3-spatial-upscaler-x2-1.1.safetensors
- ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors
- ltx23_edit_anything_global_rank128_v1_9000steps_adamw.safetensors

Do not reuse the old /workspace/ComfyUI persistent folder from previous
LTX template generations.
