"""Build-time CPU registration check; no model weights or GPU required."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

root = Path(sys.argv[1] if len(sys.argv) > 1 else '/opt/ComfyUI')
required = {'UNETLoader', 'CLIPLoader', 'VAELoader', 'MiniMaxH3ReferenceToVideo',
            'MiniMaxH3AddGuide', 'MiniMaxH3SigmaShift', 'BetaSamplingScheduler',
            'KSamplerSelect', 'SamplerCustomAdvanced', 'BasicGuider', 'RandomNoise',
            'Power Lora Loader (rgthree)', 'ResolutionSelector', 'ComfyMathExpression',
            'PrimitiveFloat', 'PrimitiveStringMultiline', 'LoadImage', 'VAEDecode',
            'VAEDecodeAudio', 'CreateVideo', 'SaveVideo'}
with tempfile.TemporaryFile(mode='w+') as log:
    p = subprocess.Popen([sys.executable, 'main.py', '--cpu', '--listen', '127.0.0.1',
                          '--port', '18189', '--disable-auto-launch'], cwd=root, stdout=log, stderr=log)
    try:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if p.poll() is not None:
                raise RuntimeError('ComfyUI exited before node registration')
            try:
                with urllib.request.urlopen('http://127.0.0.1:18189/object_info', timeout=5) as response:
                    info = json.load(response)
            except (OSError, ValueError):
                time.sleep(1)
                continue
            missing = required - info.keys()
            if missing:
                raise RuntimeError('Missing PRISM workflow nodes: ' + ', '.join(sorted(missing)))
            for name, fields in {'BetaSamplingScheduler': {'model','steps','alpha','beta'},
                                 'MiniMaxH3SigmaShift': {'model','shift_video','shift_audio'},
                                 'MiniMaxH3AddGuide': {'positive','latent','frame_idx','image','vae'}}.items():
                inputs = info[name]['input']
                actual = set(inputs.get('required', {})) | set(inputs.get('optional', {}))
                if not fields <= actual:
                    raise RuntimeError(f'{name}: missing inputs {fields-actual}')
            print('PASS: all PRISM I2V/Power LoRA nodes registered on CPU', flush=True)
            break
        else:
            raise RuntimeError('Timed out waiting for ComfyUI node registration')
    except Exception:
        log.seek(0)
        print(log.read()[-18000:])
        raise
    finally:
        p.terminate()
        try: p.wait(timeout=10)
        except subprocess.TimeoutExpired: p.kill(); p.wait()
