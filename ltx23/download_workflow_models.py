#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import get_hf_file_metadata, hf_hub_download, hf_hub_url
from tqdm.auto import tqdm as base_tqdm

WORKSPACE = Path(os.getenv("WORKSPACE", "/workspace"))
PERSIST_ROOT = Path(os.getenv("LTX23_PERSIST_ROOT", "/workspace/ltx23-data"))
MODELS_ROOT = Path(os.getenv("LTX23_MODELS_ROOT", str(PERSIST_ROOT / "models")))
DOWNLOAD_ROOT = PERSIST_ROOT / ".downloads"
LOG_DIR = WORKSPACE / "logs"
STATUS_FILE = LOG_DIR / "ltx23-model-status.json"
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")

MODELS = [
    {
        "name": "10Eros LTX 2.3 BF16 checkpoint",
        "repo": "TenStrip/LTX2.3-10Eros",
        "filename": "10Eros_v1_bf16.safetensors",
        "target": "checkpoints/10Eros_v1_bf16.safetensors",
    },
    {
        "name": "Gemma 3 12B FP8 text encoder",
        "repo": "GitMylo/LTX-2-comfy_gemma_fp8_e4m3fn",
        "filename": "gemma_3_12B_it_fp8_e4m3fn.safetensors",
        "target": "text_encoders/gemma_3_12B_it_fp8_e4m3fn.safetensors",
    },
    {
        "name": "LTX 2.3 spatial upscaler x2 v1.1",
        "repo": "Lightricks/LTX-2.3",
        "filename": "ltx-2.3-spatial-upscaler-x2-1.1.safetensors",
        "target": "latent_upscale_models/ltx-2.3-spatial-upscaler-x2-1.1.safetensors",
    },
    {
        "name": "LTX 2.3 cond-safe distilled LoRA",
        "repo": "SulphurAI/Sulphur-2-base",
        "filename": "distill_loras/ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors",
        "target": "loras/ltx23/ltx-2.3-22b-distilled-lora-1.1_fro90_ceil72_condsafe.safetensors",
    },
    {
        "name": "LTX 2.3 Edit Anything IC-LoRA",
        "repo": "Alissonerdx/LTX-LoRAs",
        "filename": "ltx23_edit_anything_global_rank128_v1_9000steps_adamw.safetensors",
        "target": "loras/ltx23/ltx23_edit_anything_global_rank128_v1_9000steps_adamw.safetensors",
    },
]

def now() -> str:
    return datetime.now(timezone.utc).isoformat()

def write_status(rows: list[dict]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ready = sum(1 for x in rows if x["status"] in {"present", "downloaded", "ready"})
    payload = {"updated_at": now(), "ready": ready, "total": len(rows), "models": rows}
    tmp = STATUS_FILE.with_name(f"{STATUS_FILE.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, STATUS_FILE)

def remote_size(m: dict) -> int | None:
    try:
        meta = get_hf_file_metadata(hf_hub_url(m["repo"], m["filename"]), token=HF_TOKEN)
        return int(meta.size) if meta.size is not None else None
    except Exception as exc:
        print(f"[models] SIZE? {m['name']}: {exc}", flush=True)
        return None

def progress_class(index: int, rows: list[dict]):
    class DashboardTqdm(base_tqdm):
        def __init__(self, *args, **kwargs):
            self._last_dashboard_write = 0.0
            super().__init__(*args, **kwargs)
            self._sync(force=True)

        def _sync(self, force: bool = False):
            t = time.monotonic()
            if not force and t - self._last_dashboard_write < 0.5:
                return
            self._last_dashboard_write = t
            rows[index]["downloaded_bytes"] = int(getattr(self, "n", 0) or 0)
            total = getattr(self, "total", None)
            if total:
                rows[index]["size_bytes"] = int(total)
            rows[index]["updated_at"] = now()
            write_status(rows)

        def update(self, n=1):
            result = super().update(n)
            self._sync()
            return result

        def close(self):
            try:
                self._sync(force=True)
            except Exception:
                pass
            return super().close()
    return DashboardTqdm

def target_is_complete(target: Path, expected_size: int | None) -> bool:
    if not target.exists() or not target.is_file():
        return False
    size = target.stat().st_size
    if expected_size:
        return size == expected_size
    return size > 1024 * 1024

def main() -> int:
    MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for m in MODELS:
        rows.append({
            "name": m["name"], "repo": m["repo"], "filename": m["filename"],
            "target": str(MODELS_ROOT / m["target"]), "status": "queued",
            "size_bytes": None, "downloaded_bytes": 0, "updated_at": now(),
        })
    write_status(rows)

    failures = 0
    for i, m in enumerate(MODELS):
        target = MODELS_ROOT / m["target"]
        target.parent.mkdir(parents=True, exist_ok=True)
        expected = remote_size(m)
        rows[i]["size_bytes"] = expected
        write_status(rows)

        if target_is_complete(target, expected):
            actual = target.stat().st_size
            rows[i].update(status="present", downloaded_bytes=actual,
                           size_bytes=expected or actual, updated_at=now())
            write_status(rows)
            print(f"[models] SKIP {m['name']} -> {target}", flush=True)
            continue

        if target.exists():
            print(f"[models] Removing incomplete target: {target}", flush=True)
            target.unlink(missing_ok=True)

        slot = DOWNLOAD_ROOT / f"model-{i}"
        slot.mkdir(parents=True, exist_ok=True)

        rows[i]["status"] = "downloading"
        rows[i]["updated_at"] = now()
        write_status(rows)
        print(f"[models] GET  {m['name']} ({m['repo']} :: {m['filename']})", flush=True)

        try:
            cached = Path(hf_hub_download(
                repo_id=m["repo"],
                filename=m["filename"],
                token=HF_TOKEN,
                local_dir=str(slot),
                tqdm_class=progress_class(i, rows),
            ))
            if not cached.exists():
                raise RuntimeError(f"Downloaded file not found: {cached}")

            os.replace(cached, target)
            actual = target.stat().st_size
            shutil.rmtree(slot, ignore_errors=True)

            rows[i].update(status="downloaded", downloaded_bytes=actual,
                           size_bytes=expected or actual, updated_at=now())
            write_status(rows)
            print(f"[models] DONE {m['name']} -> {target}", flush=True)
        except Exception as exc:
            failures += 1
            rows[i]["status"] = "error"
            rows[i]["error"] = str(exc)
            rows[i]["updated_at"] = now()
            write_status(rows)
            print(f"[models] ERROR {m['name']}: {exc}", flush=True)

    # Remove empty download root when everything is complete.
    try:
        if DOWNLOAD_ROOT.exists() and not any(DOWNLOAD_ROOT.iterdir()):
            DOWNLOAD_ROOT.rmdir()
    except Exception:
        pass

    if failures:
        print(f"[models] Finished with {failures} failure(s). Re-running resumes.", flush=True)
        return 2

    print("[models] All exact workflow models are ready.", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
