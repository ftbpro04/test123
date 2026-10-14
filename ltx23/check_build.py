#!/usr/bin/env python3
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
from common import APP,read_json
from workflow_model_parser import audit

def main():
    p=argparse.ArgumentParser();p.add_argument('--require-sources',action='store_true');p.add_argument('--runtime',action='store_true');a=p.parse_args()
    m=read_json(APP/'model_manifest.json');w=read_json(APP/'workflows/ltx23-linux.json');result,_=audit(w)
    assert hashlib.sha256((APP/'workflows/original.json').read_bytes()).hexdigest()==m['workflow_sha256']
    for supplied,parsed in zip(sorted(m['models'],key=lambda x:x['destination']),sorted(result['models'],key=lambda x:x['destination'])):
        assert all(supplied[k]==parsed[k] for k in ('filename','category','selection','destination'))
    assert len(m['models'])==16 and len({x['destination'] for x in m['models']})==16
    assert {x['destination'] for x in m['models']}=={x['destination'] for x in result['models']}
    unresolved=[x['filename'] for x in m['models'] if not x.get('source_verified') or not x.get('sha256') or not x.get('expected_size')]
    print('Workflow-model inventory: 16/16; unresolved author-source verification:',unresolved)
    if a.require_sources:assert not unresolved,'Release blocked by unresolved author-source verification'
    if a.runtime:
        import torch
        # LTXVideo at the pinned commit imports this symbol (removed in Kornia 0.8.3).
        from kornia.geometry.transform.pyramid import pad
        assert torch.__version__.startswith('2.10.'),torch.__version__
        assert torch.version.cuda is not None and torch.version.cuda.startswith('13.'),torch.version.cuda
        assert torch.backends.cudnn.version() and torch.backends.cudnn.version()//10000==9
        assert Path('/opt/ComfyUI/main.py').is_file()
        for item in read_json(APP/'node_manifest.json')['packages']:
            if item['repo']!='Comfy-Org/ComfyUI':assert (Path('/opt/ComfyUI/custom_nodes')/item['directory']).is_dir()
        report={'torch':torch.__version__,'cuda':torch.version.cuda,'cudnn':torch.backends.cudnn.version(),
                'packages':sorted(f'{d.metadata["Name"]}=={d.version}' for d in importlib.metadata.distributions()),
                'node_pins':read_json(APP/'node_manifest.json'),'unresolved_sources':unresolved}
        (APP/'build_report.json').write_text(json.dumps(report,indent=2))
        print('CUDA userspace build assertion: PASS',report['torch'],report['cuda'])
if __name__=='__main__':main()
