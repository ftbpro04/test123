# Vast.ai Template — LTX 2.3 Exact Workflow

## Image

```
ghcr.io/ftbpro04/vast-ltx23:latest
```

## Identification

Template Name:

```
LTX 2.3 - Exact Workflow
```

Template Description:

```
LTX 2.3 10Eros triple-pass I2V based on antilopax/ltx23:v14 with exact workflow nodes/models, persistent storage, dashboard and Jupyter
```

## Ports

TCP only:

- `8080` — Dashboard
- `8188` — ComfyUI
- `8888` — JupyterLab

## Environment Variables

Recommended:

```
WORKSPACE=/workspace
LTX23_PERSIST_ROOT=/workspace/ComfyUI
ENABLE_DASHBOARD=1
DASHBOARD_PORT=8080
COMFY_PORT=8188
JUPYTER_PORT=8888
DOWNLOAD_WORKFLOW_MODELS=1
```

The image already defaults these Antilopax bulk downloads to false:

```
DOWNLOAD_LTX23_DISTILLED=false
DOWNLOAD_LTX23_FULL_FP8=false
DOWNLOAD_LTX23_FULL_BF16=false
DOWNLOAD_LTX23_UPSCALERS=false
```

Do not turn those back on unless you intentionally want additional models.

Optional:

```
HF_TOKEN=<your Hugging Face token if needed>
DASHBOARD_PASSWORD=<optional password>
DOWNLOAD_WORKFLOW_MODELS=0
```

Use `DOWNLOAD_WORKFLOW_MODELS=0` only when the persistent volume already contains all five required files and you do not want the downloader to check them.

## Launch Mode

Select:

```
Docker ENTRYPOINT
```

Leave Docker ENTRYPOINT args blank.

Leave On-start Script blank.

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

Existing files are skipped on subsequent launches when the same `/workspace` volume is attached.

## Visibility

Keep the Vast template Private while testing.
