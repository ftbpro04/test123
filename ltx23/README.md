# Vast LTX 2.3 Dashboard

Thin Vast.ai wrapper around:

```
antilopax/ltx23:v14
```

Published as:

```
ghcr.io/ftbpro04/vast-ltx23:latest
```

## What it preserves

The original image was inspected before wrapping. It uses:

```
ENTRYPOINT ["/opt/nvidia/nvidia_entrypoint.sh"]
CMD ["/app/startup_unix.sh"]
WORKDIR /app/ComfyUI
```

The wrapper chains back into that exact original startup path.

## What it adds

- Dashboard on port 8080
- ComfyUI/Jupyter launch buttons
- GPU, VRAM, temperature, power and disk status
- live startup/dashboard logs
- persistent `/workspace`
- model persistence across Vast instances

The wrapper redirects the base image's writable ComfyUI folders to:

```
/workspace/ComfyUI/models
/workspace/ComfyUI/input
/workspace/ComfyUI/output
/workspace/ComfyUI/user
```

This is especially useful on Vast because large LTX checkpoints can remain on the same persistent volume instead of being downloaded again for every new instance.

## Base model defaults

The inspected `v14` image defaults to LTX 2.3 Distilled + Full FP8 + upscalers, with Full BF16 disabled.

See `VAST_TEMPLATE.md` for exact Vast.ai fields and a lower-bandwidth configuration.
