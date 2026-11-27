"""Run vision prompt expansion outside ComfyUI's dependency environment."""
import json
import sys
from pathlib import Path

def main():
    import torch
    from PIL import Image
    from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig
    request = json.loads(Path(sys.argv[1]).read_text())
    root = Path(request['root'])
    model_dir = root/'models/LLM/Qwen-VL/Qwen3.5-4B-heretic-v2'
    if not (model_dir/'.ltx-ready').is_file():
        raise RuntimeError('Heretic download is not ready. Check the dashboard heretic log, then retry.')
    system = (root/'config/heretic_system.txt').read_text()
    processor = AutoProcessor.from_pretrained(model_dir, local_files_only=True)
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16,
                              bnb_4bit_quant_type='nf4', bnb_4bit_use_double_quant=True)
    model = AutoModelForImageTextToText.from_pretrained(model_dir, local_files_only=True,
        quantization_config=quant, device_map={'': 0}, attn_implementation='sdpa', dtype=torch.bfloat16)
    content = []
    image = Image.open(request['image']).convert('RGB') if request.get('image') else None
    if image is not None:
        image.thumbnail((1024, 1024))
        content.append({'type': 'image', 'image': image})
    content.append({'type': 'text', 'text': f"Duration: {request['seconds']:.2f} seconds. Idea: {request['idea']}"})
    messages = [{'role': 'system', 'content': system}, {'role': 'user', 'content': content}]
    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    inputs = processor(text=[text], images=[image] if image else None, return_tensors='pt').to(model.device)
    torch.manual_seed(request['seed'])
    with torch.inference_mode():
        result = model.generate(**inputs, max_new_tokens=request['max_tokens'], do_sample=True,
            temperature=request['temperature'], top_p=0.9, top_k=20, repetition_penalty=1.1)
    prompt = processor.batch_decode(result[:, inputs['input_ids'].shape[1]:], skip_special_tokens=True)[0].strip()
    if not prompt: raise RuntimeError('Empty prompt returned by model')
    Path(request['result']).write_text(json.dumps({'prompt': prompt}))

if __name__ == '__main__': main()
