"""Download one persistent model copy and repair upstream processor omissions."""
import fcntl
import json
import os
from pathlib import Path
from huggingface_hub import snapshot_download, hf_hub_download

def main():
    root = Path(os.environ.get('LTX23_PERSIST_ROOT', '/workspace/ltx23-data'))
    target = root/'models/LLM/Qwen-VL/Qwen3.5-4B-heretic-v2'
    target.mkdir(parents=True, exist_ok=True)
    with (target/'.provision.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        marker = target/'.ltx-ready'
        if marker.exists():
            expected = json.loads(marker.read_text())
            if all((target/n).is_file() and (target/n).stat().st_size == size for n,size in expected.items()):
                print('Heretic: existing complete download reused.', flush=True)
                return
            marker.unlink()
        print('Downloading Heretic weights and tokenizer into persistent volume...', flush=True)
        snapshot_download('tvall43/Qwen3.5-4B-heretic-v2', revision=HERETIC_REV,
            local_dir=target, allow_patterns=['*.json', '*.jinja', '*.safetensors'])
        for name in ('preprocessor_config.json', 'video_preprocessor_config.json'):
            hf_hub_download('Qwen/Qwen3.5-4B', name, revision=QWEN_REV, local_dir=target)
        from transformers import AutoProcessor
        AutoProcessor.from_pretrained(target, local_files_only=True)
        files = {p.name:p.stat().st_size for p in target.iterdir() if p.is_file() and not p.name.startswith('.')}
        if not any(n.endswith('.safetensors') and size > 1_000_000 for n,size in files.items()):
            raise RuntimeError('Model weights missing')
        temporary = target/'.ltx-ready.tmp'
        temporary.write_text(json.dumps(files)); temporary.replace(marker)
        print('Heretic ready: weights, tokenizer and image processor verified.', flush=True)

HERETIC_REV = '1e5898a664ccf8c8b3e5827138b533136b6d6d7f'
QWEN_REV = '851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a'
if __name__ == '__main__': main()
