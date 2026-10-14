"""Small shared helpers; importing these never imports Torch."""
import hashlib
import json
import os
import re
import time
from pathlib import Path

APP = Path(__file__).resolve().parent
WORKSPACE = Path(os.environ.get('WORKSPACE', '/workspace'))
PERSIST = Path(os.environ.get('LTX23_PERSIST_ROOT', str(WORKSPACE / 'ltx23-data')))
RUNTIME = Path(os.environ.get('LTX23_RUNTIME_DIR', '/tmp/ltx23-runtime'))
LOGS = WORKSPACE / 'logs'
MANIFEST = Path(os.environ.get('LTX23_MANIFEST', str(APP / 'model_manifest.json')))

def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + f'.{os.getpid()}.tmp')
    with tmp.open('w') as f:
        json.dump(obj, f, indent=2); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def read_json(path, default=None):
    try: return json.loads(Path(path).read_text())
    except (OSError, ValueError): return {} if default is None else default

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def model_path(root, destination):
    from workflow_model_parser import safe_selection
    p = Path(root) / safe_selection(destination)
    if not p.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Model path escapes model root through a symlink')
    return p

def redact(text):
    for key in ('HF_TOKEN', 'HUGGING_FACE_HUB_TOKEN', 'CIVITAI_TOKEN', 'JUPYTER_TOKEN', 'DASHBOARD_PASSWORD'):
        secret = os.environ.get(key)
        if secret: text = text.replace(secret, '[redacted]')
    return re.sub(r'(?i)([?&](?:token|access_token|signature|x-amz-signature)=)[^\s&]+', r'\1[redacted]', text)

def process_alive(info):
    try:
        import psutil
        p = psutil.Process(info['pid'])
        return (p.is_running() and p.status() != psutil.STATUS_ZOMBIE and
                abs(p.create_time() - info['create_time']) < 0.01 and
                p.cmdline() == info['command'])
    except (KeyError, OSError, ImportError): return False
    except Exception: return False
