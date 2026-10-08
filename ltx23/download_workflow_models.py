#!/usr/bin/env python3
"""One locked sequential downloader, one partial per target, no HF blob cache."""
import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path
from urllib.parse import quote, urlparse
import requests
from common import MANIFEST, PERSIST, RUNTIME, atomic_json, digest, model_path, read_json

CHUNK = 4 * 1024 * 1024

class DownloadError(RuntimeError): pass

def request(url, headers=None, stream=False):
    if urlparse(url).scheme != 'https' and os.environ.get('LTX23_TEST_HTTP') != '1':
        raise DownloadError('Download sources must use HTTPS')
    try:
        r = requests.get(url, headers=headers or {}, timeout=(20, 90), stream=stream)
    except requests.RequestException:
        raise DownloadError('Network request failed or timed out; retry is safe') from None
    if r.status_code not in (200, 206):
        code=r.status_code; r.close()
        raise DownloadError(f'HTTP {code}; check access and HF_TOKEN/CIVITAI_TOKEN if required')
    return r

def source_info(model, cache):
    m=dict(model)
    if m.get('expected_size') and m.get('sha256'): return m
    cached=cache.get(m['destination'])
    if cached and cached.get('civitai_version_id')==m.get('civitai_version_id'):
        m.update(cached); return m
    if m['source'] != 'civitai': raise DownloadError('Authoritative size and SHA256 are unresolved')
    headers={}
    if os.environ.get('CIVITAI_TOKEN'): headers['Authorization']='Bearer '+os.environ['CIVITAI_TOKEN']
    with request(f'https://civitai.com/api/v1/model-versions/{m["civitai_version_id"]}', headers) as r:
        data=r.json()
    matches=[f for f in data.get('files',[]) if f.get('name')==m['filename']]
    if len(matches)!=1: raise DownloadError('Civitai version does not contain one exact matching filename')
    file=matches[0]; sha=file.get('hashes',{}).get('SHA256','').lower()
    if not re.fullmatch('[a-f0-9]{64}',sha): raise DownloadError('Civitai file has no usable SHA256')
    url=file['downloadUrl']
    # Resolve an exact integer Content-Length; rounded sizeKB is not sufficient.
    with request(url, headers, stream=True) as r:
        expected=int(r.headers.get('Content-Length',0))
    if expected<=0: raise DownloadError('Civitai response omitted exact file size')
    m.update(expected_size=expected,sha256=sha,url=url,source_verified=True)
    cache[m['destination']]={k:m[k] for k in ('civitai_version_id','expected_size','sha256','url','source_verified')}
    return m

def download_url(m):
    headers={'Accept-Encoding':'identity'}
    if m['source']=='huggingface':
        url=f'https://huggingface.co/{m["repo_id"]}/resolve/{m["revision"]}/{quote(m["repo_filename"],safe="/")}'
        token=os.environ.get('HF_TOKEN') or os.environ.get('HUGGING_FACE_HUB_TOKEN')
    else:
        url=m['url'];token=os.environ.get('CIVITAI_TOKEN')
    if token:headers['Authorization']='Bearer '+token
    return url,headers

def disk_guard(directory, remaining, margin):
    free=shutil.disk_usage(directory).free
    if free < remaining+margin:
        raise DownloadError(f'Insufficient disk space: remaining {remaining/1e9:.2f} GB; '
                            f'available {free/1e9:.2f} GB; recommended free {(remaining+margin)/1e9:.2f} GB')

def transfer(m, target, partials, update, received, margin):
    expected,sha=m['expected_size'],m['sha256']
    key=hashlib.sha256(m['destination'].encode()).hexdigest()[:24]
    part=partials/(key+'.part');meta=partials/(key+'.json')
    identity={'destination':m['destination'],'expected_size':expected,'sha256':sha}
    if part.exists() and read_json(meta)!=identity:
        raise DownloadError(f'Partial identity differs; inspect {part} before removing it')
    atomic_json(meta,identity)
    if target.exists():
        if not part.exists() and target.stat().st_size < expected:
            os.replace(target,part)
        else:
            # A target is removed only after its expected size/hash has proved invalid.
            target.unlink()
    target.parent.mkdir(parents=True,exist_ok=True)
    if partials.stat().st_dev != target.parent.stat().st_dev:
        raise DownloadError('Downloads and models must share one filesystem for atomic placement')
    url,headers=download_url(m)
    for attempt in range(3):
        offset=part.stat().st_size if part.exists() else 0
        if offset>expected:part.unlink();offset=0
        disk_guard(partials,expected-offset,margin)
        try:
            if offset<expected:
                request_headers=dict(headers)
                if offset:request_headers['Range']=f'bytes={offset}-'
                update('Downloading',offset)
                with request(url,request_headers,stream=True) as response:
                    if response.headers.get('Content-Encoding','identity') not in ('','identity'):
                        raise DownloadError('Unexpected compressed transfer')
                    if response.status_code==206:
                        match=re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                        if not match or int(match[1])!=offset or int(match[2])!=expected-1 or int(match[3])!=expected:
                            raise DownloadError('Invalid resume range; refusing to append')
                    elif offset:
                        # Server ignored Range. Reclaim our own partial before restarting.
                        part.unlink();offset=0
                        disk_guard(partials,expected,margin)
                    content_length=response.headers.get('Content-Length')
                    if content_length and int(content_length)!=expected-offset:
                        raise DownloadError('Remote size differs from manifest')
                    with part.open('ab' if offset else 'wb') as f:
                        last=0
                        for block in response.iter_content(CHUNK):
                            if not block:continue
                            if offset+len(block)>expected:raise DownloadError('Response exceeds expected size')
                            disk_guard(partials,len(block),margin)
                            f.write(block);offset+=len(block);received(len(block))
                            if time.monotonic()-last>0.5:
                                update('Downloading',offset);last=time.monotonic()
                        f.flush();os.fsync(f.fileno())
            if part.stat().st_size!=expected:raise DownloadError('Transfer ended before expected size')
            update('Verifying',expected)
            if digest(part)!=sha:
                part.unlink()
                raise DownloadError('SHA256 mismatch; corrupt partial removed for retry')
            os.replace(part,target);meta.unlink(missing_ok=True)
            update('Ready',expected);return
        except (requests.RequestException, DownloadError, OSError):
            if attempt==2:raise DownloadError('Download failed after 3 attempts; partial retained if resumable') from None
            time.sleep(2**attempt)

def run(check_only=False):
    PERSIST.mkdir(parents=True,exist_ok=True)
    with (PERSIST/'.model-downloader.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print('Another model downloader is already active. Exiting.',flush=True);return 0
        models=read_json(MANIFEST)['models'];root=PERSIST/'models';partials=PERSIST/'downloads'
        root.mkdir(exist_ok=True);partials.mkdir(exist_ok=True)
        cachefile=partials/'model_metadata.json';cache=read_json(cachefile)
        rows=[{**m,'status':'Queued','downloaded_bytes':0,'final_path':str(model_path(root,m['destination']))} for m in models]
        payload={'models':rows,'downloaded_this_launch':0,'reused_bytes':0,'checked_at':None}
        def save():
            payload.update(updated_at=time.time(),ready=sum(r['status']=='Ready' for r in rows),total=len(rows))
            atomic_json(RUNTIME/'models.json',payload)
        def received(n):payload['downloaded_this_launch']+=n
        save();failures=0
        for row in rows:
            def update(status,amount=0):row.update(status=status,downloaded_bytes=amount);save()
            try:
                update('Checking')
                if check_only and not row.get('expected_size') and row['destination'] not in cache:
                    raise DownloadError('Size/hash unresolved; automatic downloading disabled')
                m=source_info(row,cache);row.update({k:m[k] for k in ('expected_size','sha256','source_verified')})
                atomic_json(cachefile,cache)
                target=model_path(root,m['destination'])
                if target.is_file() and target.stat().st_size==m['expected_size']:
                    update('Verifying',m['expected_size'])
                    if digest(target)==m['sha256']:
                        payload['reused_bytes']+=m['expected_size'];update('Ready',m['expected_size'])
                        print(f'SKIP verified {m["destination"]}',flush=True);continue
                if check_only:raise DownloadError('Missing or corrupt model; downloads disabled')
                print(f'GET {m["destination"]}',flush=True)
                transfer(m,target,partials,update,received,int(os.environ.get('MIN_FREE_BYTES',10*1024**3)))
            except Exception as exc:
                failures+=1;row['error']=str(exc) if isinstance(exc,DownloadError) else f'{type(exc).__name__}: metadata or filesystem operation failed'
                update('Error');print(f'ERROR {row["filename"]}: {row["error"]}',flush=True)
        payload['checked_at']=time.time();save()
        print(f'{payload["ready"]}/{len(rows)} verified models; received {payload["downloaded_this_launch"]} bytes; reused {payload["reused_bytes"]} bytes',flush=True)
        return 2 if failures else 0

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check-only',action='store_true');a=p.parse_args()
    raise SystemExit(run(a.check_only))
