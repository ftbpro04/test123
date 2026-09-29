# Vast LTX 2.3 — Exact Workflow Dashboard

Thin Vast.ai wrapper around:

```
antilopax/ltx23:v14
```

Published as:

```
ghcr.io/ftbpro04/vast-ltx23:latest
```

This version is tailored to `10E_I2V_triplepass_00010-audio.json`.

## Included custom nodes

- ComfyUI-Manager
- Civicomfy
- ComfyUI-HuggingFace
- ComfyUI-KJNodes
- ComfyMath
- ComfyUI-LTXVideo
- RES4LYF
- 10S-Comfy-nodes
- rgthree-comfy
- ComfyUI-VideoHelperSuite

Workflow-specific packages with commit metadata in the JSON are pinned where practical.

## Exact active model set

Only these five unique files are downloaded automatically:

1. `checkpoints/10Eros_v1_bf16.safetensors`
2. `text_encoders/gemma_3_12B_it_fp8_e4m3fn.safetensors`
3. `latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.1.safetensors`
4. `loras/ltx23/ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors`
5. `loras/ltx23/ltx23_edit_anything_global_rank128_v1_9000steps_adamw.safetensors`

The alternate FP8 transformer, standalone VAEs and standalone text-projection referenced by bypassed nodes are intentionally not downloaded.

Antilopax's broader automatic LTX model set is disabled by default.

## Persistence

Mount a Vast persistent volume at:

```
/workspace
```

Models persist under:

```
/workspace/ComfyUI/models
```

Hugging Face cache persists under:

```
/workspace/hf-cache
```

Recreating an instance with the same volume causes existing models to be skipped instead of downloaded again.

## Ports

- 18080 — dashboard
- 8188 — ComfyUI
- 8888 — JupyterLab

See `VAST_TEMPLATE.md` for exact Vast fields.
