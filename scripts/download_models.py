#!/usr/bin/env python3
"""Resumable MiniMax H3 model downloader with dashboard-friendly status."""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import get_hf_file_metadata, hf_hub_download, hf_hub_url
from tqdm.auto import tqdm as base_tqdm

MODELS_ROOT = Path(os.getenv("MODELS_ROOT", "/workspace/ComfyUI/models"))
LOG_DIR = Path(os.getenv("LOG_DIR", "/workspace/logs"))
STATUS_FILE = LOG_DIR / "model-status.json"
PROFILE = os.getenv("MINIMAX_PROFILE", "full").strip().lower()
WORKERS = max(1, min(int(os.getenv("MODEL_DOWNLOAD_WORKERS", "2")), 4))
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")

VALID_PROFILES = {"full", "core", "fl2va", "ref2va", "none"}
if PROFILE not in VALID_PROFILES:
    print(f"[models] Unknown MINIMAX_PROFILE={PROFILE!r}; using 'full'.", flush=True)
    PROFILE = "full"

MODELS = [
    {"name":"MiniMax H3 video VAE FP16","repo":"Comfy-Org/MiniMax-H3","remote_path":"vae/minimax_h3_video_vae_fp16.safetensors","local_dir":".","profiles":["full","core","fl2va","ref2va"]},
    {"name":"MiniMax H3 audio VAE FP32","repo":"Comfy-Org/MiniMax-H3","remote_path":"vae/minimax_h3_audio_vae_fp32.safetensors","local_dir":".","profiles":["full","core","fl2va","ref2va"]},
    {"name":"FL2VA NVFP4 + ConvRot INT8","repo":"lilcheaty/MiniMax-H3-NVFP4","remote_path":"minimax_h3_fl2va_pruned_nvfp4_convrot_int8.safetensors","local_dir":"diffusion_models","profiles":["full","core","fl2va"]},
    {"name":"Ref2VA NVFP4 + ConvRot INT8","repo":"lilcheaty/MiniMax-H3-NVFP4","remote_path":"minimax_h3_ref2va_pruned_nvfp4_convrot_int8.safetensors","local_dir":"diffusion_models","profiles":["full","core","ref2va"]},
    {"name":"Qwen3-VL 32B Heretic MiniMax H3 NVFP4","repo":"Momoking/Qwen3-VL-32B-Heretic-MiniMax-H3-NVFP4","remote_path":"qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors","local_dir":"text_encoders","profiles":["full","core","fl2va","ref2va"]},
    {"name":"FL2V Turbo 8-step 768p LoRA","repo":"lightx2v/Minimax-h3-Turbo","remote_path":"minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors","local_dir":"loras","profiles":["full","core","fl2va"]},
    {"name":"Ref2V Turbo 8-step 768p LoRA","repo":"lightx2v/Minimax-h3-Turbo","remote_path":"minimax_h3_ref2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors","local_dir":"loras","profiles":["full","core","ref2va"]},
    {"name":"10Eros-Max H3 TURBO Hybrid Beta3 INT8 ConvRot Skip-Edges","repo":"cicalooo/10Eros-Max-h3-int8-convrot","remote_path":"10Eros_Max_h3_TURBO-hybrid_beta3_int8_convrot_skip_edges.safetensors","local_dir":"diffusion_models","profiles":["full"]},
]

if os.getenv("DOWNLOAD_INT8_VIDEO_VAE", "0").lower() in {"1", "true", "yes", "on"}:
    MODELS.append({"name":"MiniMax H3 video VAE INT8 ConvRot (optional)","repo":"Comfy-Org/MiniMax-H3","remote_path":"vae/minimax_h3_video_vae_int8_convrot.safetensors","local_dir":".","profiles":["full","core","fl2va","ref2va"]})

lock = threading.Lock()
state: dict[str, dict] = {}
order: list[str] = []


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def expected_target(m: dict) -> Path:
    local_base = MODELS_ROOT / m["local_dir"]
    if "/" in m["remote_path"] and m["local_dir"] == ".":
        return local_base / m["remote_path"]
    return local_base / Path(m["remote_path"]).name


def write_status() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with lock:
        rows = [state[name].copy() for name in order]
    ready = sum(1 for r in rows if r.get("status") in {"present", "downloaded", "ready"})
    payload = {
        "profile": PROFILE,
        "updated_at": now(),
        "ready": ready,
        "total": len(rows),
        "models": rows,
    }
    tmp = STATUS_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(STATUS_FILE)


def update(name: str, **fields) -> None:
    with lock:
        state[name].update(fields)
        state[name]["updated_at"] = now()
    write_status()


def remote_size(m: dict) -> int | None:
    try:
        meta = get_hf_file_metadata(hf_hub_url(m["repo"], m["remote_path"]), token=HF_TOKEN)
        return int(meta.size) if meta.size is not None else None
    except Exception as exc:
        print(f"[models] SIZE? {m['name']}: {exc}", flush=True)
        return None


def progress_class(model_name: str):
    """Create a throttled tqdm class that mirrors real byte progress to the dashboard."""
    class DashboardTqdm(base_tqdm):
        def __init__(self, *args, **kwargs):
            self._dashboard_last_write = 0.0
            super().__init__(*args, **kwargs)
            self._dashboard_sync(force=True)

        def _dashboard_sync(self, force: bool = False):
            t = time.monotonic()
            if not force and t - self._dashboard_last_write < 0.5:
                return
            self._dashboard_last_write = t
            fields = {"downloaded_bytes": int(getattr(self, "n", 0) or 0)}
            total = getattr(self, "total", None)
            if total:
                fields["size_bytes"] = int(total)
            update(model_name, **fields)

        def update(self, n=1):
            result = super().update(n)
            self._dashboard_sync()
            return result

        def close(self):
            self._dashboard_sync(force=True)
            return super().close()

    return DashboardTqdm


def download_one(m: dict) -> dict:
    name = m["name"]
    target = expected_target(m)
    target.parent.mkdir(parents=True, exist_ok=True)

    size = remote_size(m)
    if size:
        update(name, size_bytes=size)

    if target.exists() and target.stat().st_size > 1024 * 1024:
        update(name, status="present", path=str(target), downloaded_bytes=target.stat().st_size, finished_at=now())
        print(f"[models] SKIP  {name} -> {target}", flush=True)
        return state[name]

    update(name, status="downloading", started_at=now())
    print(f"[models] GET   {name} ({m['repo']} :: {m['remote_path']})", flush=True)
    local_dir = MODELS_ROOT / m["local_dir"]
    local_dir.mkdir(parents=True, exist_ok=True)

    downloaded = hf_hub_download(
        repo_id=m["repo"],
        filename=m["remote_path"],
        local_dir=str(local_dir),
        token=HF_TOKEN,
        tqdm_class=progress_class(name),
    )

    if not target.exists():
        got = Path(downloaded)
        if got.exists() and got != target:
            target.parent.mkdir(parents=True, exist_ok=True)
            got.replace(target)

    actual = target.stat().st_size if target.exists() else 0
    update(name, status="downloaded", path=str(target), downloaded_bytes=actual, finished_at=now())
    print(f"[models] DONE  {name} -> {target}", flush=True)
    return state[name]


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    MODELS_ROOT.mkdir(parents=True, exist_ok=True)

    if PROFILE == "none":
        STATUS_FILE.write_text(json.dumps({"profile": PROFILE, "ready": 0, "total": 0, "models": [], "updated_at": now()}, indent=2), encoding="utf-8")
        print("[models] MINIMAX_PROFILE=none; nothing to download.", flush=True)
        return 0

    selected = [m for m in MODELS if PROFILE in m["profiles"]]
    for m in selected:
        name = m["name"]
        order.append(name)
        state[name] = {
            "name": name,
            "repo": m["repo"],
            "remote_path": m["remote_path"],
            "status": "queued",
            "path": str(expected_target(m)),
            "size_bytes": None,
            "downloaded_bytes": 0,
            "updated_at": now(),
        }
    write_status()

    failures = 0
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(download_one, m): m for m in selected}
        for fut in as_completed(futures):
            m = futures[fut]
            try:
                fut.result()
            except Exception as exc:
                failures += 1
                print(f"[models] ERROR {m['name']}: {exc}", file=sys.stderr, flush=True)
                update(m["name"], status="error", error=str(exc), finished_at=now())

    write_status()
    if failures:
        print(f"[models] Finished with {failures} failure(s). Re-running the script resumes.", flush=True)
        return 2

    print(f"[models] All {len(selected)} selected models are ready.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
