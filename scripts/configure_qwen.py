"""Register the original H3 prompt model without replacing user configuration."""
import json
from pathlib import Path
import sys

MODEL_NAME = 'Qwen3.5-4B-heretic-v2'
MODEL_INFO = {'repo_id': 'tvall43/Qwen3.5-4B-heretic-v2', 'quantized': False,
              'vram_requirement': {'full': 9.0, '8bit': 5.0, '4bit': 3.0}}

def configure(node_dir):
    path = Path(node_dir)/'custom_models.json'
    data = json.loads(path.read_text()) if path.exists() else {}
    data.setdefault('hf_vl_models', {}).setdefault(MODEL_NAME, MODEL_INFO)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, indent=2)+'\n')
    tmp.replace(path)
    preset_path = Path(node_dir)/'presets/h3_prism.json'
    if not preset_path.exists():
        template = """You expand a short idea and its starting image into a complete MiniMax H3 PRISM image-to-video prompt for {duration}. Output only the final English video prompt, without explanations or markdown fences.
Use the image as Picture 1 and the opening frame. Preserve visible identity, clothing, composition, lighting and location. Expand the user's requested motion into a physically coherent single continuous shot, with clear temporal progression, camera movement, expression and environmental motion appropriate to the duration. Avoid inventing additional people, scene cuts, outfits, objects or dialogue unless requested. Use specific visual language rather than a list of quality tags. Keep audio natural to the scene and add music only if requested. Keep the scene non-explicit.
Use this exact structure:
For the target video, at 0.00 seconds into the target video, <Picture 1> (from [Shot 1]) is fully referenced.
integrated_multimodal_description: [Shot 1] Describe the starting scene, the requested action over {duration}, and the camera behavior.
overall_soundscape: Describe suitable ambient sounds or requested speech.
non_diegetic_music: None unless the user requests music.
Aim for 150-300 words; retain the user's intent and all supported image details."""
        data = {'vl': {'MiniMax › PRISM I2VA': {'durations': {duration: template.format(duration=duration) for duration in ('5s','10s','15s','20s')}, 'default': '5s'}}}
        preset_path.parent.mkdir(parents=True, exist_ok=True)
        preset_path.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')

if __name__ == '__main__':
    configure(sys.argv[1])
