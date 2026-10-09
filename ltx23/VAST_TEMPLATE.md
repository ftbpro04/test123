# Vast settings — use only after a successful build and approved publication

No new image is published by this change. **Do not enter a proposed tag in Vast yet.** The existing `latest`/`clean-cuda13-v2` tags do not contain this unmerged review branch.

| Setting | Value |
|---|---|
| Template name | LTX 2.3 Exact Workflow - CUDA 13 |
| Image | Pending successful validation and separately authorized publication |
| Proposed future version tag | `ghcr.io/ftbpro04/vast-ltx23:cuda13-v3` — not available/tested |
| Launch mode | Docker ENTRYPOINT |
| ENTRYPOINT args | Blank |
| On-start script | Blank |
| Exposed TCP ports | `18080`, `8188`, `8888` |
| Persistent volume mount | `/workspace` (configure actual volume attachment) |
| Host filter | CUDA Max Supported >= 13.0 |
| Container disk | Must be finalized from measured image size; provisional budget 40 GB |
| Persistent disk | 200 GB starting budget for 101.398 GB models, 50 GiB outputs and 10 GiB reserve; allow more for large outputs |

```text
WORKSPACE=/workspace
LTX23_PERSIST_ROOT=/workspace/ltx23-data
ENABLE_DASHBOARD=1
ENABLE_JUPYTER=1
DASHBOARD_PORT=18080
COMFY_PORT=8188
JUPYTER_PORT=8888
DOWNLOAD_WORKFLOW_MODELS=1
```

Optional: `HF_TOKEN`, `CIVITAI_TOKEN`, `JUPYTER_TOKEN`, `DASHBOARD_PASSWORD`, `COMFY_EXTRA_ARGS`. Anime metadata and download headers were accessible without a token during verification; access can change. No performance flags are added by default. `--cpu` is for CI registration tests only.

Vast mappings normally expose `VAST_TCP_PORT_18080`, `VAST_TCP_PORT_8188`, `VAST_TCP_PORT_8888`, and `PUBLIC_IPADDR`. The dashboard does not assume internal ports equal public ports. For a custom proxy, explicit `COMFY_PUBLIC_URL` and `JUPYTER_PUBLIC_URL` are supported.

## Storage sizing

All 16 files: **101,398,017,134 bytes = 101.398 GB = 94.434 GiB**. See MODEL_REPORT.md.

Budget the complete model total + desired input/output capacity + at least 10 GiB free reserve. A practical starting output allowance is 50 GiB. Round up to the volume sizes offered. Models plus those allowances total 165.823 GB; 200 GB is a practical starting budget, not a guarantee for arbitrary outputs. The volume cannot be resized after creation according to Vast's documentation.

Atomic rename means no second checkpoint-sized copy is needed for normal first downloads. A partial occupies the space that its final file will occupy; the free-space guard needs remaining bytes + reserve. Failed, legacy, and manually downloaded duplicate files consume extra space and appear in the audit. No automatic cleanup of legacy content is performed.

CI run 37741032409 measured **16,333,283,351 bytes (16.33 GB / 15.21 GiB)** for the review image. This is a baseline, not the final release size. CI records `image-size-bytes.txt`; it is the unpacked image size, not registry transfer size. Final container-disk sizing must include that unpacked image, build/runtime overhead, and disposable caches. Compressed registry transfer size requires registry inspection after publication.

## Volume reuse limitation

Vast currently offers **local volumes tied to one physical machine**. You may reattach to another compatible instance on that same machine. You cannot attach that volume directly to a different physical machine. For a different machine, copy data to a volume there using Vast's supported volume-copy flow, then preserve `ltx23-data/` at the mount root. Copying incurs data transfer; the template cannot make cross-machine migration free.

Official documentation: https://docs.vast.ai/guides/instances/storage/volumes
Networking documentation: https://docs.vast.ai/documentation/instances/connect/networking

## Real GPU acceptance still required

After a validated image is published: attach the volume, confirm dashboard and Jupyter, check runtime reports Torch 2.10.x / CUDA 13.x / CUDA available true, resolve all 16 models, inspect actual node-registration validation, upload the input image, open the normalized workflow, and run a small non-sensitive generation. Verify audio and all three passes. Test disabled LoRAs and alternate model loaders. Restart and check `Downloaded this launch: 0` with all models verified. These tests have not been claimed as complete.
