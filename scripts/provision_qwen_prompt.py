"""Install the pinned prompt model and original Qwen vision processor configs."""
from pathlib import Path
import tempfile
from huggingface_hub import snapshot_download, hf_hub_download

MODEL_REPO = 'tvall43/Qwen3.5-4B-heretic-v2'
MODEL_REVISION = '1e5898a664ccf8c8b3e5827138b533136b6d6d7f'
PROCESSOR_REVISION = '851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a'

def provision(target, processor_only=False):
    target = Path(target)
    patterns = ['*.json', '*.jinja']
    if not processor_only:
        patterns.append('*.safetensors')
    snapshot_download(MODEL_REPO, revision=MODEL_REVISION, local_dir=str(target), allow_patterns=patterns)
    for name in ('preprocessor_config.json', 'video_preprocessor_config.json'):
        hf_hub_download('Qwen/Qwen3.5-4B', name, revision=PROCESSOR_REVISION, local_dir=str(target))
    from transformers import AutoProcessor
    processor = AutoProcessor.from_pretrained(target, local_files_only=True)
    if processor_only:
        from PIL import Image
        image = Image.new('RGB', (64,64), 'blue')
        messages = [{'role':'user','content':[{'type':'image','image':image},
                    {'type':'text','text':'Write a short video prompt for a slow camera pan.'}]}]
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
        inputs = processor(text=[text], images=[image], return_tensors='pt')
        assert 'pixel_values' in inputs and inputs['input_ids'].numel() > 0
        print('PASS: H3 prompt model tokenizer and image processor', flush=True)
    elif not any(target.glob('*.safetensors')):
        raise RuntimeError('Prompt model weights are missing')
    return target

if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as d:
        provision(d, processor_only=True)
