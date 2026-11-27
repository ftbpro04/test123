"""CPU smoke: use the exact pinned tokenizer/processor pair with a synthetic image."""
import tempfile
from huggingface_hub import snapshot_download, hf_hub_download
from PIL import Image
from transformers import AutoProcessor
from provision_heretic import HERETIC_REV, QWEN_REV

with tempfile.TemporaryDirectory() as folder:
    snapshot_download('tvall43/Qwen3.5-4B-heretic-v2', revision=HERETIC_REV,
        local_dir=folder, allow_patterns=['config.json', 'tokenizer*.json', '*.jinja'])
    for name in ('preprocessor_config.json', 'video_preprocessor_config.json'):
        hf_hub_download('Qwen/Qwen3.5-4B', name, revision=QWEN_REV, local_dir=folder)
    processor = AutoProcessor.from_pretrained(folder, local_files_only=True)
    image = Image.new('RGB', (64, 64), 'blue')
    messages = [{'role': 'system', 'content': 'Describe the requested motion.'},
                {'role': 'user', 'content': [{'type': 'image', 'image': image},
                                             {'type': 'text', 'text': 'Slow camera pan.'}]}]
    prompt = processor.apply_chat_template(messages, tokenize=False,
        add_generation_prompt=True, enable_thinking=False)
    inputs = processor(text=[prompt], images=[image], return_tensors='pt')
    assert 'pixel_values' in inputs and 'image_grid_thw' in inputs
    assert inputs['input_ids'].numel() > 0
    print('PASS: Heretic tokenizer, image processor and chat template encode an image.')
