import json
import torch
print(json.dumps({'torch':str(torch.__version__),'cuda':torch.version.cuda,
                  'cuda_available':torch.cuda.is_available(),
                  'gpu':torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}))
assert torch.version.cuda and torch.version.cuda.startswith('13.'), 'CUDA 13.x runtime required'
