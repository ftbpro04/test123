# Vast LTX 2.3 Dashboard

A thin Vast.ai wrapper around:

```
antilopax/ltx23:v14
```

It deliberately does **not** replace the original image's ENTRYPOINT or CMD. The only image-level additions are:

- LTX 2.3 control-panel dashboard
- ports 8080 / 8188 / 8888 exposed
- Vast-friendly environment defaults

The resulting GHCR image is:

```
ghcr.io/ftbpro04/vast-ltx23:latest
```

## Why it is thin

The source image may contain its own startup logic, custom nodes, model setup, or optimizations. Replacing its startup command would risk breaking those. Instead, Vast's On-start Script launches the dashboard in the background after the container starts.

## Dashboard

Port `8080` provides:

- Open ComfyUI button
- Open JupyterLab button
- GPU utilization
- VRAM usage
- GPU temperature and power
- /workspace disk usage
- live dashboard/startup logs

## Persistent storage

Mount a Vast persistent volume at:

```
/workspace
```

This is especially important for large LTX model files and helps prevent repeated model downloads when moving between compatible instances.

See `VAST_TEMPLATE.md` for the exact Vast.ai fields.
