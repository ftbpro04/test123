#!/usr/bin/env python3
"""Resolve candidate Civitai versions; refuse mismatched filenames or mirror hashes.
No weights are downloaded. Token comes only from CIVITAI_TOKEN in the environment.
"""
import argparse
import json
import os
import re
from urllib.parse import urlparse
import requests
from common import MANIFEST, atomic_json, read_json
from download_workflow_models import request, DownloadError

def verify(model, data):
    matches=[f for f in data.get('files',[]) if f.get('name')==model['filename']]
    if len(matches)!=1:raise DownloadError('Candidate version does not have exactly this filename')
    file=matches[0];sha=file.get('hashes',{}).get('SHA256','').lower()
    if not re.fullmatch('[0-9a-f]{64}',sha):raise DownloadError('Author source omitted SHA256')
    if model.get('sha256') and model['sha256']!=sha:
        raise DownloadError('Author hash differs from mirror; no automatic substitution')
    size=model.get('expected_size')
    if not size:
        headers={'Accept-Encoding':'identity'}
        if os.environ.get('CIVITAI_TOKEN'):headers['Authorization']='Bearer '+os.environ['CIVITAI_TOKEN']
        with request(file['downloadUrl'],headers,stream=True) as r:
            size=int(r.headers.get('Content-Length',0))
        if size<=0:raise DownloadError('Author download omitted exact byte length')
    return {**model,'source_verified':True,'sha256':sha,'expected_size':size,
            'provenance':'Civitai exact filename and author SHA256 verified; mirror hash matches' if model['source']=='huggingface' else 'Civitai exact filename, SHA256 and byte size verified',
            **({'url':file['downloadUrl']} if model['source']=='civitai' else {})}

def main():
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true',help='Update manifest only with verified source metadata');a=p.parse_args()
    manifest=read_json(MANIFEST);failures=[];headers={}
    if os.environ.get('CIVITAI_TOKEN'):headers['Authorization']='Bearer '+os.environ['CIVITAI_TOKEN']
    for i,model in enumerate(manifest['models']):
        if model.get('source_verified'):continue
        try:
            version=model['civitai_version_id']
            with request(f'https://civitai.com/api/v1/model-versions/{version}',headers) as r:data=r.json()
            manifest['models'][i]=verify(model,data)
            print('Verified:',model['filename'])
        except Exception as exc:
            reason=str(exc) if isinstance(exc,DownloadError) else type(exc).__name__
            failures.append({'filename':model['filename'],'error':reason});print('Unresolved:',model['filename'],reason)
    manifest['size_report']={'known_bytes':sum(m.get('expected_size') or 0 for m in manifest['models']),
        'unknown_files':[m['filename'] for m in manifest['models'] if not m.get('expected_size')]}
    if a.write:atomic_json(MANIFEST,manifest)
    print(json.dumps({'sizes':manifest['size_report'],'unresolved':failures},indent=2))
    return 2 if failures else 0
if __name__=='__main__':raise SystemExit(main())
