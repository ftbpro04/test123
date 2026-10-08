#!/usr/bin/env python3
"""Independent stdlib dashboard. No Torch imports, no subprocesses per HTTP poll."""
import base64
import hmac
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from common import APP, WORKSPACE, PERSIST, RUNTIME, LOGS, MANIFEST, atomic_json, process_alive, read_json, redact

PORT=int(os.environ.get('DASHBOARD_PORT','18080'))
PASSWORD=os.environ.get('DASHBOARD_PASSWORD','')
LOG_NAMES=('models','comfy','jupyter','dashboard','container','validation')
metrics={'storage':{'status':'Scanning'},'gpus':[]}

def scan_directory(path,seen):
    allocated=logical=0
    for base,dirs,files in os.walk(path,followlinks=False):
        dirs[:]=[d for d in dirs if not (Path(base)/d).is_symlink()]
        for name in files:
            try:
                p=Path(base)/name
                if p.is_symlink():continue
                st=p.stat();key=(st.st_dev,st.st_ino)
                if key in seen:continue
                seen.add(key);allocated+=st.st_blocks*512;logical+=st.st_size
            except OSError:continue
    return {'allocated_bytes':allocated,'logical_bytes':logical}

def storage_snapshot():
    d=shutil.disk_usage(WORKSPACE);seen=set();rows=[]
    paths=[PERSIST/'models',PERSIST/'output',PERSIST/'downloads',PERSIST/'input',PERSIST/'user',LOGS]
    paths.extend(p for p in WORKSPACE.iterdir() if p.is_dir() and not p.is_symlink() and p not in (PERSIST,LOGS))
    for p in paths:
        rows.append({'path':str(p),**scan_directory(p,seen),
                     'legacy':p in (WORKSPACE/'ComfyUI',WORKSPACE/'hf-cache')})
    # Show top-level files and otherwise unclassified persistent directories too.
    for p in PERSIST.iterdir() if PERSIST.exists() else []:
        if p.is_dir() and not p.is_symlink() and p not in paths:
            rows.append({'path':str(p),**scan_directory(p,seen),'legacy':p.name in ('.downloads','hf-cache')})
    return {'total_bytes':d.total,'used_bytes':d.used,'free_bytes':d.free,
            'directories':sorted(rows,key=lambda x:x['allocated_bytes'],reverse=True),'scanned_at':time.time(),
            'note':'Allocated bytes; symlinks skipped and hardlinks counted once. Filesystem usage includes other files/containers.'}

def gpu_snapshot():
    fields='name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,driver_version'
    try:
        out=subprocess.check_output(['nvidia-smi','--query-gpu='+fields,'--format=csv,noheader,nounits'],text=True,timeout=3,stderr=subprocess.DEVNULL)
        result=[]
        for line in out.splitlines():
            p=[s.strip() for s in line.split(',')]
            def number(s):
                try:return float(s)
                except ValueError:return None
            result.append(dict(zip(('name','utilization_pct','memory_used_mb','memory_total_mb','temperature_c','power_w','driver'),[p[0],*[number(v) for v in p[1:6]],p[6]])))
        return result
    except (OSError,subprocess.SubprocessError):return []

def poll_metrics():
    last=0
    while True:
        try:
            metrics['gpus']=gpu_snapshot()
            if time.monotonic()-last>=30:
                metrics['storage']=storage_snapshot();last=time.monotonic()
                atomic_json(RUNTIME/'storage.json',metrics['storage'])
        except Exception:metrics['storage']={'error':'Storage audit failed; verify workspace access'}
        time.sleep(3)

def port_open(port):
    try:
        with socket.create_connection(('127.0.0.1',int(port)),timeout=0.15):return True
    except (OSError,ValueError):return False

def service_status():
    result=read_json(RUNTIME/'services.json')
    ports={'comfy':os.environ.get('COMFY_PORT','8188'),'jupyter':os.environ.get('JUPYTER_PORT','8888'),'dashboard':str(PORT)}
    for name,info in result.items():
        if info.get('pid'):
            alive=process_alive(info)
            if alive:info['state']='Running' if name not in ports or port_open(ports[name]) else 'Starting'
            elif info.get('exit_code') is None:info['state']='Error'
    return result

def mapping(port):
    value=os.environ.get('VAST_TCP_PORT_'+str(port))
    try:
        parsed=int(value)
        return parsed if 0<parsed<65536 else None
    except (TypeError,ValueError):return None

def status():
    pack=read_json(MANIFEST);models=read_json(RUNTIME/'models.json')
    if not models.get('models'):
        models={'models':[{**m,'status':'Queued','final_path':str(PERSIST/'models'/m['destination'])} for m in pack.get('models',[])],'ready':0,'total':len(pack.get('models',[]))}
    ports={name:mapping(int(os.environ.get(env,default))) for name,env,default in [('comfy','COMFY_PORT','8188'),('jupyter','JUPYTER_PORT','8888'),('dashboard','DASHBOARD_PORT','18080')]}
    # Public unauthenticated dashboard never reveals the Jupyter credential.
    token=(WORKSPACE/'.jupyter_token').read_text().strip() if PASSWORD and (WORKSPACE/'.jupyter_token').exists() else None
    return {'services':service_status(),'models':models,'runtime':read_json(RUNTIME/'runtime.json'),
            'validation':read_json(RUNTIME/'validation.json'),**metrics,'public_ports':ports,
            'public_host':os.environ.get('PUBLIC_IPADDR') or os.environ.get('VAST_PUBLIC_IP') or '',
            'jupyter_token':token,'urls':{'comfy':os.environ.get('COMFY_PUBLIC_URL'),'jupyter':os.environ.get('JUPYTER_PUBLIC_URL')},
            'mapping_note':'Unmapped buttons remain disabled. Set explicit public URLs if your proxy does not expose Vast port variables.'}

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass  # No access-token URLs or endless polling noise in logs.
    def send(self,body,kind='application/json',code=200):
        if isinstance(body,dict):body=json.dumps(body).encode()
        elif isinstance(body,str):body=body.encode()
        self.send_response(code);self.send_header('Content-Type',kind+'; charset=utf-8')
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','no-referrer');self.send_header('Content-Length',str(len(body)))
        self.end_headers();self.wfile.write(body)
    def authenticated(self):
        if not PASSWORD:return True
        try:
            value=self.headers.get('Authorization','')
            if not value.startswith('Basic '):return False
            user,password=base64.b64decode(value[6:],validate=True).decode().split(':',1)
            return hmac.compare_digest(user,'ltx23') and hmac.compare_digest(password,PASSWORD)
        except Exception:return False
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=='/api/health':return self.send({'ok':True,'service':'dashboard'})
        if not self.authenticated():
            self.send_response(401);self.send_header('WWW-Authenticate','Basic realm="LTX23"');self.send_header('Content-Length','0');self.end_headers();return
        if parsed.path=='/':return self.send((APP/'dashboard.html').read_bytes(),'text/html')
        if parsed.path=='/api/status':return self.send(status())
        if parsed.path=='/api/logs':
            name=parse_qs(parsed.query).get('name',['container'])[0]
            if name not in LOG_NAMES:return self.send('Unknown log','text/plain',404)
            try:
                with (LOGS/(name+'.log')).open('rb') as f:
                    f.seek(0,2);f.seek(max(0,f.tell()-128*1024));data=f.read().decode(errors='replace')
                return self.send(redact(data),'text/plain')
            except OSError:return self.send('No log yet.','text/plain')
        return self.send('Not found','text/plain',404)

if __name__=='__main__':
    threading.Thread(target=poll_metrics,daemon=True).start()
    server=ThreadingHTTPServer(('0.0.0.0',PORT),Handler)
    print(f'Dashboard listening on {PORT}',flush=True);server.serve_forever()
