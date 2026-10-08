#!/usr/bin/env python3
import argparse
import json
import time
import urllib.request
from pathlib import Path
from common import APP, MANIFEST, PERSIST, RUNTIME, atomic_json, model_path, read_json
from workflow_model_parser import audit, graphs

FRONTEND = {'SetNode': 'ComfyUI-KJNodes/web/js', 'GetNode': 'ComfyUI-KJNodes/web/js'}

def validate(workflow, manifest, object_info=None, custom_root=None):
    parsed,_=audit(workflow)
    expected={m['destination'] for m in parsed['models']}
    supplied={m['destination'] for m in manifest['models']}
    manifest_ok=expected==supplied and len(supplied)==16 and len(manifest['models'])==16
    subgraphs={g for g,_ in graphs(workflow) if g!='root'}
    types={n['type'] for n in parsed['nodes']}-subgraphs
    frontend_ok=[];frontend_missing=[]
    for t in sorted(types & FRONTEND.keys()):
        folder=Path(custom_root or '/opt/ComfyUI/custom_nodes')/FRONTEND[t]
        # Set/Get are virtual JS nodes, deliberately absent from /object_info.
        found=folder.is_dir() and any(t in f.read_text(errors='replace') for f in folder.rglob('*.js'))
        (frontend_ok if found else frontend_missing).append(t)
    backend=types-FRONTEND.keys()
    missing=sorted(backend-set(object_info)) if object_info is not None else None
    metadata=read_json(PERSIST/'downloads/model_metadata.json')
    absent=[];present=[];selection_errors=[]
    for m in manifest['models']:
        size=m.get('expected_size') or metadata.get(m['destination'],{}).get('expected_size')
        path=model_path(PERSIST/'models',m['destination'])
        good=path.is_file() and bool(size) and path.stat().st_size==size
        (present if good else absent).append(m['destination'])
        if object_info is not None and good:
            for occurrence in m['occurrences']:
                kind=occurrence['node_type']
                if kind=='Power Lora Loader (rgthree)':continue
                from workflow_model_parser import LOADERS
                fields=LOADERS[kind]
                for field,index,category in fields:
                    if occurrence['field'] not in (f'widgets_values/{index}',f'widgets_values/{field}'):continue
                    schema=object_info.get(kind,{}).get('input',{})
                    spec={**schema.get('required',{}),**schema.get('optional',{})}.get(field)
                    if spec and isinstance(spec[0],list) and m['selection'] not in spec[0]:
                        selection_errors.append(f'{kind}.{field}: {m["selection"]} not listed')
    hashes=read_json(RUNTIME/'models.json')
    verified=sum(r.get('status')=='Ready' for r in hashes.get('models',[]))
    return {'manifest_ok':manifest_ok,'required_models':len(expected),'models_present_by_size':len(present),
            'models_verified':verified,'missing_models':absent,'missing_backend_nodes':missing,
            'frontend_nodes_verified':frontend_ok,'frontend_nodes_missing':frontend_missing,
            'backend_node_count':len(backend),'subgraph_count':len(subgraphs),'selection_errors':selection_errors,
            'node_types_ok':missing==[] and not frontend_missing,
            'ready':manifest_ok and missing==[] and not frontend_missing and not absent and verified==16 and not selection_errors,
            'checked_at':time.time()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8188');p.add_argument('--watch',action='store_true');p.add_argument('--static',action='store_true');p.add_argument('--nodes-only',action='store_true');p.add_argument('--custom-root',default='/opt/ComfyUI/custom_nodes');a=p.parse_args()
    w=read_json(APP/'workflows/ltx23-linux.json');m=read_json(MANIFEST)
    last=None
    while True:
        info=None;error=None
        if not a.static:
            try:
                with urllib.request.urlopen(a.url+'/object_info',timeout=15) as r:info=json.load(r)
            except Exception:error='ComfyUI object_info unavailable; backend registration not validated'
        result=validate(w,m,info,a.custom_root)
        if error:result['registration_error']=error
        atomic_json(RUNTIME/'validation.json',result)
        comparable={k:v for k,v in result.items() if k!='checked_at'}
        if comparable!=last:print(json.dumps(comparable),flush=True);last=comparable
        if not a.watch:return 0 if (result['manifest_ok'] and result['node_types_ok'] if a.nodes_only else result['ready']) else 2
        time.sleep(15)
if __name__=='__main__':raise SystemExit(main())
