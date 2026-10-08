# Validation and remaining acceptance gates

## Verified in this development session

- Programmatic workflow audit: 95 nodes across the root and subgraph; 16 unique configured models. All seven Power LoRAs and bypassed selections retained.
- Six non-selection references classified: two catalog references plus four stale execution/frontend references. No automatic catalog downloads.
- SHA256 and exact byte-size metadata obtained for 15 files (10 author/maintainer sources, five mirrors). Model bytes were not downloaded.
- Pinned repositories inspected. `GLSLShader` in the bypassed subgraph is included in validation; frontend-only Set/Get nodes are checked separately.
- 13 meaningful local tests passed: graph inventory, named widget parsing, unknown loader fail-closed behavior, path/symlink traversal rejection, Range resume, ignored/invalid Range handling, hash rejection, disk guard, partial identity protection, downloader locking, zero-network reuse, duplicate supervisor refusal, and dashboard survival with a captured ComfyUI traceback.
- Python compilation and shell syntax checks passed.

## Not yet verified

| Milestone | Status |
|---|---|
| Docker build / final CUDA assertion | Not executed locally: Docker unavailable; CI definition provided |
| Full backend custom-node registration | Requires the built container CPU smoke test, then GPU validation |
| CUDA device availability | Requires actual compatible GPU |
| All 16 model files downloaded and hash checked | Not performed; anime size/hash unresolved |
| Civitai source verification for six LoRAs | Blocked by HTTP 403 in this environment |
| GHCR publication | Deliberately disabled by request |
| Vast runtime / mapped port test | Not performed; no Vast runtime was provisioned |
| Workflow opened and all three passes generated with audio | Not performed |
| Reattachment of real Vast storage | Not performed; fixture reuse verified locally |
| Docker image disk size | Unknown until image builds |

## Findings in the previous code

The previous downloader hardcoded only five files and had no file lock, space guard, or SHA256 verification. When remote-size lookup failed, it treated files larger than 1 MB as complete. The dashboard displayed the five-model profile, could expose the Jupyter token without authentication, relied on service information that could be stale, and imported Torch for runtime information. Startup performed the Torch probe before launching the dashboard, so a probe failure could prevent diagnostics from opening. The prior GitHub workflow published before it smoke-tested.

The old persistence helper copied/deleted application data during startup, and historical layouts/caches could coexist under `/workspace`. These are plausible failure/duplication mechanisms. **They do not prove the exact cause of the user's prior restart loops or 500+ GB report.** No affected live volume or matching failure logs were inspected during this work. The new audit reports allocated bytes, logical bytes, and legacy locations without automatic deletion.

## Before release

Resolve and independently verify the six Civitai author-source entries, including anime size/hash. Update the manifest with exact evidence and rerun `check_build.py --require-sources`. Finish Docker and CPU registration CI. Inspect `build_report.json`, pin additional Python packages if the resolved dependency set needs stabilization, and measure image size. Run the real-GPU acceptance steps in VAST_TEMPLATE.md. Only then publish a versioned image with separate authorization. Existing MiniMax files and tags are unchanged.
