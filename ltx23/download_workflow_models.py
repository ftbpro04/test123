#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from huggingface_hub import hf_hub_download

WORKSPACE = Path(os.getenv("WORKSPACE", "/workspace"))
MODELS_ROOT = Path(os.getenv("LTX23_MODELS_ROOT", "/workspace/ComfyUI/models"))
LOG_DIR = WORKSPACE / "logs"
STATUS_FILE = LOG_DIR / "ltx23-model-status.json"
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGING_FACE_HUB_TOKEN")

# Only the five UNIQUE files used by ACTIVE nodes in
# 10E_I2V_triplepass_00010-audio.json.
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
    ready = sum(1 for x in rows if x["status"] in {"present", "downloaded"})
    payload = {
        "updated_at": now(),
        "ready": ready,
        "total": len(rows),
        "models": rows,
    }
    tmp = STATUS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, STATUS_FILE)

def link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        return
    try:
        os.link(src, dst)
    except OSError:
        shutil.copy2(src, dst)

def main() -> int:
    MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    rows = []
    for m in MODELS:
        rows.append({
            "name": m["name"],
            "repo": m["repo"],
            "filename": m["filename"],
            "target": str(MODELS_ROOT / m["target"]),
            "status": "queued",
            "updated_at": now(),
        })
    write_status(rows)

    failures = 0
    for i, m in enumerate(MODELS):
        target = MODELS_ROOT / m["target"]
        if target.exists() and target.stat().st_size > 1024 * 1024:
            rows[i]["status"] = "present"
            rows[i]["updated_at"] = now()
            write_status(rows)
            print(f"[models] SKIP {m['name']} -> {target}", flush=True)
            continue

        rows[i]["status"] = "downloading"
        rows[i]["updated_at"] = now()
        write_status(rows)
        print(f"[models] GET  {m['name']} ({m['repo']} :: {m['filename']})", flush=True)

        try:
            cached = Path(hf_hub_download(
                repo_id=m["repo"],
                filename=m["filename"],
                token=HF_TOKEN,
            ))
            link_or_copy(cached, target)
            rows[i]["status"] = "downloaded"
            rows[i]["updated_at"] = now()
            rows[i]["size_bytes"] = target.stat().st_size
            write_status(rows)
            print(f"[models] DONE {m['name']} -> {target}", flush=True)
        except Exception as exc:
            failures += 1
            rows[i]["status"] = "error"
            rows[i]["error"] = str(exc)
            rows[i]["updated_at"] = now()
            write_status(rows)
            print(f"[models] ERROR {m['name']}: {exc}", flush=True)

    if failures:
        print(f"[models] Finished with {failures} failure(s). Re-running resumes.", flush=True)
        return 2

    print("[models] All exact workflow models are ready.", flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
