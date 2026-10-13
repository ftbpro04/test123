# Create the Vast test template

Published test image: `ghcr.io/ftbpro04/vast-ltx23:cuda13-v3-test-6d3e3f5`
Source: `6d3e3f53bade6c2f066fe49f3fc6ef2798c9f989`
Publication run: https://github.com/ftbpro04/test123/actions/runs/38469933610

Publication and anonymous registry access passed on 2026-10-13.

Digest: `sha256:8ab78dbc6333ecacf1690c5be171574ad3a73ed8fd7338ed28975c74624f88fc`.

This is a GPU-test candidate; live GPU generation still needs acceptance testing.

## 1. Template fields

Open https://cloud.vast.ai/templates/ and create a template.

| Field | Value |
|---|---|
| Name | LTX 2.3 Exact Workflow - CUDA 13 Test |
| Image path | ghcr.io/ftbpro04/vast-ltx23 |
| Version tag | cuda13-v3-test-6d3e3f5 |
| Launch mode | docker ENTRYPOINT |
| Entrypoint arguments | Leave blank |
| On-start script | Leave blank / not applicable |
| Ports | TCP 18080, 8188, 8888 |
| Container disk | 40 GB, with the separate volume below |
| Visibility | Private |
| Registry authentication | Leave blank after public pull verification succeeds |

If the UI uses one combined image field, paste the complete image:tag above. Do not select Automatic, latest or clean-cuda13-v2.

Docker Options (the GUI port/environment widgets are equivalent):

```text
-p 18080:18080 -p 8188:8188 -p 8888:8888 -e WORKSPACE=/workspace -e LTX23_PERSIST_ROOT=/workspace/ltx23-data -e ENABLE_DASHBOARD=1 -e ENABLE_JUPYTER=1 -e DASHBOARD_PORT=18080 -e COMFY_PORT=8188 -e JUPYTER_PORT=8888 -e DOWNLOAD_WORKFLOW_MODELS=1
```

Set a private `DASHBOARD_PASSWORD` through Vast account environment settings or the private instance environment. Dashboard username is `ltx23`; password is your chosen value. The authenticated dashboard can show the generated Jupyter token. Optional HF_TOKEN/CIVITAI_TOKEN belong in private account or instance settings, never a public template.

## 2. Storage and host selection

Filter for NVIDIA hosts with CUDA Max Supported >= 13.0 and x86_64/AMD64 CPU architecture. GPU generation has not yet been benchmarked; verify the selected offer before committing to a long rental.

In the template editor, open **Disk Space (Container + Volume)**, enable **Add recommended volume settings**, enter **200 GB**, and change the installation/mount path to **/workspace** (do not leave the default /data). A 40 GB container disk alone cannot hold the models. Models total 101,398,017,134 bytes, before inputs/outputs. The 200 GB plan includes room for roughly 50 GiB of output and a 10 GiB reserve.

Vast local volumes are tied to their physical machine. Keep the volume when replacing an instance on the same machine. Moving to another machine requires copying data. Setting the WORKSPACE environment variable alone does not attach a persistent volume.

If choosing to test without a separate volume, use at least 220 GB of container disk and understand that destroying that instance loses its files. This does not satisfy the persistent-volume plan.

## 3. First start

Wait for the image pull and startup. In the instance port mappings, open the public address mapped to internal **18080**. Public port numbers will usually differ from the internal numbers. Log in as `ltx23` if you set DASHBOARD_PASSWORD.

Use the dashboard's ComfyUI/Jupyter buttons. Wait for **16/16 models Ready**, ComfyUI Running and workflow validation Ready. The first download is about 101.4 GB; a correctly reused volume avoids downloading verified weights again.

Open `ltx23-exact-linux.json` from ComfyUI's saved workflows. Supply the missing input image and your prompt before generating. Begin with a short, low-resolution test. GPU generation, all three passes and audio still need live acceptance testing.

If a model fails, inspect the Models log instead of recreating the instance. Twerking uses a pinned HF mirror with a known hash; its original author source remains unverified. Civitai downloads may require your own token if access changes.

## 4. What to send back

Send the instance card/port-mapping screenshot and dashboard status, with passwords/tokens hidden. If anything fails, include the corresponding ComfyUI or Models log. Do not destroy the persistent volume while troubleshooting.

Sources: https://docs.vast.ai/guides/templates/template-settings and https://docs.vast.ai/guides/instances/storage/volumes
