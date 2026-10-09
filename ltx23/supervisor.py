#!/usr/bin/env python3
"""Own process lifetimes; only dashboard has a restart policy."""
import fcntl
import json
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
import secrets
import shlex
import signal
import subprocess
import sys
import threading
import time
import psutil
from common import APP, WORKSPACE, PERSIST, RUNTIME, LOGS, atomic_json, redact

children={};states={};stopping=threading.Event();state_lock=threading.Lock()

def logger(name):
    log=logging.getLogger('ltx23.'+name);log.setLevel(logging.INFO)
    if not log.handlers:
        h=RotatingFileHandler(LOGS/(name+'.log'),maxBytes=5*1024**2,backupCount=2)
        h.setFormatter(logging.Formatter('%(asctime)s %(message)s'));log.addHandler(h)
    return log

def save():
    atomic_json(RUNTIME/'services.json',states)

def drain(name,proc):
    for line in iter(proc.stdout.readline,''):
        logger(name).info(redact(line.rstrip()))
    proc.stdout.close()

def start(name,command,cwd=None):
    with state_lock:
        try:
            p=subprocess.Popen(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                               text=True,bufsize=1,start_new_session=True,close_fds=True)
            children[name]=p
            try: created=psutil.Process(p.pid).create_time()
            except psutil.NoSuchProcess: created=0
            states[name]={'state':'Starting','pid':p.pid,'create_time':created,
                          'command':command,'exit_code':None,'started_at':time.time()}
            threading.Thread(target=drain,args=(name,p),daemon=True).start()
        except Exception as exc:
            states[name]={'state':'Error','error':f'{type(exc).__name__}: could not start service'}
            logger('container').exception('Could not start %s',name)
        save()

def persist():
    PERSIST.mkdir(parents=True,exist_ok=True)
    lock=(PERSIST/'.runtime.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    # Retained by parent only; child processes must not inherit locks.
    root=Path(os.environ.get('COMFY_ROOT','/opt/ComfyUI'))
    for name in ('models','input','output','user'):
        target=PERSIST/name;target.mkdir(exist_ok=True);link=root/name
        if link.is_symlink():
            if link.resolve()==target.resolve():continue
            raise RuntimeError(f'{link} points elsewhere; inspect before changing it')
        if link.exists():
            if not link.is_dir() or any(link.iterdir()):
                raise RuntimeError(f'{link} contains existing application data; no automatic deletion')
            link.rmdir()
        link.symlink_to(target,target_is_directory=True)
    (PERSIST/'downloads').mkdir(exist_ok=True)
    workflow=PERSIST/'user/default/workflows/ltx23-exact-linux.json'
    workflow.parent.mkdir(parents=True,exist_ok=True)
    if not workflow.exists():
        with workflow.open('x') as out:out.write((APP/'workflows/ltx23-linux.json').read_text())
    return lock

def probe():
    try:
        p=subprocess.run([sys.executable,str(APP/'runtime_probe.py')],capture_output=True,text=True,timeout=60)
        info={}
        for line in p.stdout.splitlines():
            try:info=json.loads(line)
            except ValueError:pass
        info['check_exit_code']=p.returncode
        if p.returncode:info['error']='CUDA runtime check failed; inspect container log'
        logger('container').info(redact(p.stdout+'\n'+p.stderr));atomic_json(RUNTIME/'runtime.json',info)
    except Exception:
        atomic_json(RUNTIME/'runtime.json',{'error':'Runtime probe failed or timed out'})

def setup_token():
    path=WORKSPACE/'.jupyter_token'
    token=os.environ.get('JUPYTER_TOKEN') or (path.read_text().strip() if path.exists() else '') or secrets.token_urlsafe(32)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(fd,'w') as f:f.write(token)
    path.chmod(0o600);os.environ['JUPYTER_TOKEN']=token
    # Do not expose the token in process arguments.
    cfg=RUNTIME/'jupyter_config.json'
    atomic_json(cfg,{'IdentityProvider':{'token':token},'ServerApp':{'root_dir':str(WORKSPACE)}})
    cfg.chmod(0o600)
    return cfg

def stop(signum,frame):stopping.set()

def main():
    RUNTIME.mkdir(parents=True,exist_ok=True);WORKSPACE.mkdir(parents=True,exist_ok=True);LOGS.mkdir(parents=True,exist_ok=True)
    lock=(RUNTIME/'supervisor.lock').open('a')
    try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError:
        print('LTX supervisor already running; refusing duplicate services');return 0
    for name in ('models','validation','runtime','storage'):atomic_json(RUNTIME/(name+'.json'),{})
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    logger('container').info('LTX 2.3 Exact Workflow starting; one ComfyUI process per launch')
    enabled=lambda key:os.environ.get(key,'1').lower() in ('1','true','yes','on')
    if enabled('ENABLE_DASHBOARD'):start('dashboard',[sys.executable,str(APP/'dashboard.py')])
    else:states['dashboard']={'state':'Disabled'}
    volume_lock=None
    try:
        volume_lock=persist()
        command=[sys.executable,str(APP/'download_workflow_models.py')]
        if not enabled('DOWNLOAD_WORKFLOW_MODELS'):command+=['--check-only']
        start('models',command)
        if enabled('ENABLE_JUPYTER'):
            cfg=setup_token()
            start('jupyter',[sys.executable,'-m','jupyterlab','--ip=0.0.0.0',
                '--port='+os.environ.get('JUPYTER_PORT','8888'),'--ServerApp.port_retries=0',
                '--no-browser','--allow-root','--config='+str(cfg)])
        else:states['jupyter']={'state':'Disabled'}
        root=os.environ.get('COMFY_ROOT','/opt/ComfyUI')
        start('comfy',[sys.executable,root+'/main.py','--listen','0.0.0.0','--port',
              os.environ.get('COMFY_PORT','8188'),'--disable-auto-launch',
              *shlex.split(os.environ.get('COMFY_EXTRA_ARGS',''))],cwd=root)
        start('validation',[sys.executable,str(APP/'validate_workflow.py'),'--watch','--url',
              'http://127.0.0.1:'+os.environ.get('COMFY_PORT','8188')])
        threading.Thread(target=probe,daemon=True).start()
    except Exception as exc:
        logger('container').exception('Startup setup failed; dashboard remains available')
        states['startup']={'state':'Error','error':str(exc)};save()
    restart_at=None
    while not stopping.wait(0.5):
        with state_lock:
            for name,p in list(children.items()):
                code=p.poll()
                if code is None:continue
                if states[name].get('exit_code') is None:
                    states[name].update(state='Stopped' if code==0 else 'Error',exit_code=code,ended_at=time.time())
                    logger('container').info('%s exited code %s; %s',name,code,'dashboard restart scheduled' if name=='dashboard' else 'no automatic restart')
                    if name=='dashboard':restart_at=time.monotonic()+2
                    save()
        if restart_at and time.monotonic()>=restart_at:
            restart_at=None;start('dashboard',[sys.executable,str(APP/'dashboard.py')])
    for p in children.values():
        if p.poll() is None:
            try:os.killpg(p.pid,signal.SIGTERM)
            except ProcessLookupError:pass
    deadline=time.monotonic()+8
    for p in children.values():
        try:p.wait(timeout=max(0.1,deadline-time.monotonic()))
        except subprocess.TimeoutExpired:
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
    if volume_lock:volume_lock.close()
    return 0
if __name__=='__main__':raise SystemExit(main())
