"""Build-time CPU registration check; no model weights or GPU required."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import urllib.request

root = Path(sys.argv[1] if len(sys.argv) > 1 else '/opt/ComfyUI')
required = {'AILab_QwenVL_Advanced', 'PreviewAny', 'UNETLoader', 'CLIPLoader', 'VAELoader', 'MiniMaxH3ReferenceToVideo',
            'MiniMaxH3AddGuide', 'MiniMaxH3SigmaShift', 'BetaSamplingScheduler',
            'KSamplerSelect', 'SamplerCustomAdvanced', 'BasicGuider', 'RandomNoise',
            'Power Lora Loader (rgthree)', 'ResolutionSelector', 'ComfyMathExpression',
            'PrimitiveFloat', 'PrimitiveStringMultiline', 'LoadImage', 'VAEDecode',
            'VAEDecodeAudio', 'CreateVideo', 'SaveVideo'}
# Include backend nodes nested inside the supplied two-pass workflow's subgraphs.
workflow = json.loads(Path('/opt/seed/workflows/H3-Turbo-2Pass-10Eros-Max-v1-INT8-HQ.json').read_text())
subgraphs = workflow.get('definitions', {}).get('subgraphs', [])
frontend_only = {'MarkdownNote', 'Mute / Bypass Relay (rgthree)', 'Mute / Bypass Repeater (rgthree)'}
frontend_only.update(g['id'] for g in subgraphs)
for graph in [workflow] + subgraphs:
    required.update(n['type'] for n in graph['nodes'] if n['type'] not in frontend_only)
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
                raise RuntimeError('Missing workflow nodes: ' + ', '.join(sorted(missing)))
            qwen = info['AILab_QwenVL_Advanced']['input']['required']
            assert 'Qwen3.5-4B-heretic-v2' in qwen['model_name'][0]
            assert '4-bit (VRAM-friendly)' in qwen['quantization'][0]
            assert 'MiniMax › PRISM I2VA' in qwen['preset_prompt'][0]
            for name, fields in {'BetaSamplingScheduler': {'model','steps','alpha','beta'},
                                 'MiniMaxH3SigmaShift': {'model','shift_video','shift_audio'},
                                 'MiniMaxH3AddGuide': {'positive','latent','frame_idx','image','vae'}}.items():
                inputs = info[name]['input']
                actual = set(inputs.get('required', {})) | set(inputs.get('optional', {}))
                if not fields <= actual:
                    raise RuntimeError(f'{name}: missing inputs {fields-actual}')
            print('PASS: all PRISM and 10Eros two-pass backend nodes registered on CPU', flush=True)
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
