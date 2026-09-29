#!/usr/bin/env python3
from __future__ import annotations

import base64
import hmac
import json
import os
import shutil
import socket
import subprocess
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

WORKSPACE = Path(os.getenv("WORKSPACE", "/workspace"))
LOG_DIR = WORKSPACE / "logs"
COMFY_PORT = int(os.getenv("COMFY_PORT", "8188"))
JUPYTER_PORT = int(os.getenv("JUPYTER_PORT", "8888"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "8080"))
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
BASE_IMAGE = os.getenv("LTX23_BASE_IMAGE", "antilopax/ltx23:v14")

LOG_FILES = {
    "models": LOG_DIR / "ltx23-model-download.log",
    "container": LOG_DIR / "ltx23-container.log",
    "jupyter": LOG_DIR / "jupyter.log",
    "dashboard": LOG_DIR / "ltx23-dashboard.log",
}

HTML = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LTX 2.3 Control Panel</title>
<style>
:root{color-scheme:dark;--bg:#0b0e14;--panel:#151a25;--line:#2a3345;--text:#eef3ff;--muted:#9aa8bd;--ok:#42d392;--bad:#ff6b7a;--warn:#f7c65f;--accent:#7c9cff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% -10%,#20304d 0,transparent 35%),radial-gradient(circle at 90% 0,#192d42 0,transparent 28%),var(--bg);color:var(--text);font:14px/1.45 Inter,system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh}.wrap{max-width:1180px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:20px}.eyebrow{color:#a8b8ff;font-weight:800;letter-spacing:.12em;text-transform:uppercase;font-size:11px}.h1{font-size:30px;font-weight:850;margin:4px 0}.sub{color:var(--muted);max-width:720px}.pill{display:inline-flex;gap:8px;align-items:center;border:1px solid var(--line);background:#101520;padding:8px 11px;border-radius:999px;color:var(--muted)}.dot,.svc-dot{width:9px;height:9px;border-radius:50%;background:var(--warn)}.ok{background:var(--ok)!important}.bad{background:var(--bad)!important}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{background:linear-gradient(180deg,rgba(24,30,44,.96),rgba(16,21,31,.96));border:1px solid var(--line);border-radius:16px;padding:17px}.launch{grid-column:span 8}.stat{grid-column:span 4}.logs{grid-column:span 12}.title{font-weight:760;font-size:15px;margin-bottom:10px}.muted,.tiny{color:var(--muted)}.tiny{font-size:12px}.btns{display:grid;grid-template-columns:1fr 1fr;gap:11px;margin-top:14px}.btn{display:flex;align-items:center;justify-content:center;border:1px solid #4b5f99;background:linear-gradient(135deg,#5878ff,#6659ef);color:#fff;text-decoration:none;padding:14px 16px;border-radius:12px;font-weight:800;font-size:15px}.btn.secondary{background:#171e2d;border-color:#3a465d}.btn.disabled{opacity:.42;pointer-events:none}.row{display:flex;justify-content:space-between;gap:12px;margin-top:8px}.service{display:flex;align-items:center;gap:8px}.metric{font-size:24px;font-weight:800;margin-top:5px}.tabs{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px}.tab{border:1px solid var(--line);background:#101622;color:var(--muted);border-radius:9px;padding:7px 10px;cursor:pointer}.tab.active{background:#222c42;color:#fff}.log{height:420px;overflow:auto;white-space:pre-wrap;word-break:break-word;background:#090d13;border:1px solid #242c3b;border-radius:11px;padding:12px;font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#c7d2e2}.footer{margin-top:16px;color:var(--muted);font-size:12px;text-align:center}@media(max-width:850px){.launch,.stat,.logs{grid-column:span 12}.top{display:block}.btns{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div>
      <div class="eyebrow">Vast.ai · LTX 2.3</div>
      <div class="h1">Control Panel</div>
      <div class="sub">Open ComfyUI and JupyterLab, inspect GPU and workspace usage, and follow startup logs. Base image: <span id="baseImage">antilopax/ltx23:v14</span></div>
    </div>
    <div class="pill"><span id="overallDot" class="dot"></span><span id="overallText">Starting…</span></div>
  </div>
  <div class="grid">
    <section class="card launch">
      <div class="title">Launch apps</div>
      <div class="muted">Buttons use Vast's mapped public ports automatically.</div>
      <div class="btns">
        <a id="comfyBtn" class="btn disabled" href="#" target="_blank" rel="noopener">Open ComfyUI</a>
        <a id="jupyterBtn" class="btn secondary disabled" href="#" target="_blank" rel="noopener">Open JupyterLab</a>
      </div>
      <div style="margin-top:14px">
        <div class="row"><span class="service"><span id="comfyDot" class="svc-dot"></span>ComfyUI</span><span id="comfyState" class="tiny">checking</span></div>
        <div class="row"><span class="service"><span id="jupyterDot" class="svc-dot"></span>JupyterLab</span><span id="jupyterState" class="tiny">checking</span></div>
        <div class="row"><span class="service"><span id="modelDot" class="svc-dot"></span>Exact workflow models</span><span id="modelState" class="tiny">checking</span></div>
      </div>
    </section>
    <section class="card stat"><div class="tiny">GPU</div><div id="gpuName" class="metric" style="font-size:18px">—</div><div id="gpuUtil" class="muted">—</div></section>
    <section class="card stat"><div class="tiny">VRAM</div><div id="vram" class="metric">—</div><div id="gpuTemp" class="muted">—</div></section>
    <section class="card stat"><div class="tiny">Workspace disk</div><div id="disk" class="metric">—</div><div id="diskSub" class="muted">—</div></section>
    <section class="card logs">
      <div class="title">Live logs</div>
      <div class="tabs">
        <button class="tab active" data-log="models">Models</button>
        <button class="tab" data-log="container">LTX / ComfyUI</button>
        <button class="tab" data-log="jupyter">Jupyter</button>
        <button class="tab" data-log="dashboard">Dashboard</button>
      </div>
      <pre id="logBox" class="log">Loading…</pre>
    </section>
  </div>
  <div class="footer">Dashboard port 8080 · workspace /workspace</div>
</div>
<script>
let activeLog='models';
const $=id=>document.getElementById(id);
function extUrl(host,port,path=''){if(!port)return null; return 'http://'+(host||window.location.hostname)+':'+port+path}
function setSvc(name,up){$(name+'Dot').className='svc-dot '+(up?'ok':'bad');$(name+'State').textContent=up?'ready':'starting / unavailable'}
function fmtGB(n){return Number.isFinite(n)?(n/1024).toFixed(1)+' GB':'—'}
async function status(){
  try{
    const r=await fetch('/api/status',{cache:'no-store'}),s=await r.json();
    $('baseImage').textContent=s.base_image||'antilopax/ltx23:v14';
    if(s.gpu){$('gpuName').textContent=s.gpu.name||'GPU';$('gpuUtil').textContent=(s.gpu.utilization_pct??'—')+'% utilization';$('vram').textContent=s.gpu.memory_total_mb?((s.gpu.memory_used_mb/1024).toFixed(1)+' / '+(s.gpu.memory_total_mb/1024).toFixed(1)+' GB'):'—';$('gpuTemp').textContent=s.gpu.temperature_c!=null?(s.gpu.temperature_c+' °C · '+(s.gpu.power_w??'—')+' W'):'—'}
    if(s.disk){$('disk').textContent=fmtGB(s.disk.used_mb);$('diskSub').textContent=fmtGB(s.disk.free_mb)+' free of '+fmtGB(s.disk.total_mb)}
    setSvc('comfy',s.services.comfy);setSvc('jupyter',s.services.jupyter);
    const mr=s.models||{ready:0,total:5,complete:false,running:false};
    $('modelDot').className='svc-dot '+(mr.complete?'ok':(mr.running?'':'bad'));
    $('modelState').textContent=mr.complete?('ready '+mr.ready+'/'+mr.total):(mr.running?('downloading '+mr.ready+'/'+mr.total):('not running '+mr.ready+'/'+mr.total));
    const host=s.public_host||window.location.hostname;
    const comfy=extUrl(host,s.public_ports.comfy,'/');
    const jp=s.jupyter_token?('/lab?token='+encodeURIComponent(s.jupyter_token)):'/lab';
    const jupyter=extUrl(host,s.public_ports.jupyter,jp);
    if(comfy){$('comfyBtn').href=comfy;$('comfyBtn').classList.remove('disabled')}
    if(jupyter){$('jupyterBtn').href=jupyter;$('jupyterBtn').classList.remove('disabled')}
    const good=s.services.comfy;
    $('overallDot').className='dot '+(good?'ok':'');
    $('overallText').textContent=good?'Ready':'Starting';
  }catch(e){$('overallDot').className='dot bad';$('overallText').textContent='Dashboard API error'}
}
async function logs(){
  try{
    const box=$('logBox'),near=box.scrollHeight-box.scrollTop-box.clientHeight<80;
    const r=await fetch('/api/log?name='+encodeURIComponent(activeLog)+'&lines=300',{cache:'no-store'}),d=await r.json();
    box.textContent=d.text||'(no log output yet)';if(near)box.scrollTop=box.scrollHeight
  }catch(e){}
}
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');activeLog=b.dataset.log;logs()}));
status();logs();setInterval(status,1500);setInterval(logs,1500);
</script>
</body>
</html>"""


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def gpu_info():
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw", "--format=csv,noheader,nounits"],
            text=True, timeout=2, stderr=subprocess.DEVNULL
        ).strip().splitlines()[0]
        p = [x.strip() for x in out.split(",")]
        return {"name": p[0], "utilization_pct": float(p[1]), "memory_used_mb": float(p[2]), "memory_total_mb": float(p[3]), "temperature_c": float(p[4]), "power_w": float(p[5])}
    except Exception:
        return None


def disk_info():
    try:
        d = shutil.disk_usage(WORKSPACE); mb=1024*1024
        return {"total_mb":d.total/mb,"used_mb":d.used/mb,"free_mb":d.free/mb}
    except Exception:
        return {}


def public_port(internal: int):
    value = os.getenv(f"VAST_TCP_PORT_{internal}")
    if value:
        try: return int(value)
        except ValueError: pass
    return internal


def public_host():
    return os.getenv("PUBLIC_IPADDR") or os.getenv("VAST_IPADDR") or os.getenv("VAST_PUBLIC_IP") or ""


def model_status():
    path = LOG_DIR / "ltx23-model-status.json"
    out = {"ready": 0, "total": 5, "complete": False, "running": False}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        out["ready"] = int(data.get("ready", 0))
        out["total"] = int(data.get("total", 5))
        out["complete"] = out["total"] > 0 and out["ready"] >= out["total"]
    except Exception:
        pass
    try:
        pid_path = LOG_DIR / "ltx23-model-download.pid"
        pid = int(pid_path.read_text().strip())
        os.kill(pid, 0)
        out["running"] = True
    except Exception:
        pass
    return out


def read_token():
    for p in [WORKSPACE/".jupyter_token", Path("/root/.jupyter_token")]:
        try:
            v=p.read_text().strip()
            if v:return v
        except Exception: pass
    return os.getenv("JUPYTER_TOKEN","")


def tail(path: Path, lines=300, max_bytes=256*1024):
    try:
        with path.open("rb") as f:
            f.seek(0,os.SEEK_END); size=f.tell(); f.seek(max(0,size-max_bytes)); raw=f.read().decode("utf-8",errors="replace")
        return "\n".join(raw.splitlines()[-lines:])
    except FileNotFoundError:return ""
    except Exception as exc:return f"Unable to read log: {exc}"


class Handler(BaseHTTPRequestHandler):
    server_version="LTX23Dashboard/1.0"
    def authorized(self):
        if not DASHBOARD_PASSWORD:return True
        h=self.headers.get("Authorization","")
        if not h.startswith("Basic "):return False
        try:
            u,p=base64.b64decode(h.split(" ",1)[1]).decode().split(":",1)
            return hmac.compare_digest(u,"ltx23") and hmac.compare_digest(p,DASHBOARD_PASSWORD)
        except Exception:return False
    def require_auth(self):
        self.send_response(HTTPStatus.UNAUTHORIZED);self.send_header("WWW-Authenticate",'Basic realm="LTX 2.3 Dashboard"');self.send_header("Content-Length","0");self.end_headers()
    def log_message(self,fmt,*args): print(f"[dashboard] {self.address_string()} - {fmt%args}",flush=True)
    def send_json(self,obj,status=200):
        body=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path!="/api/health" and not self.authorized():self.require_auth();return
        if parsed.path=="/":
            body=HTML.encode();self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8");self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body);return
        if parsed.path=="/api/health":self.send_json({"ok":True,"time":time.time()});return
        if parsed.path=="/api/status":
            self.send_json({
                "base_image":BASE_IMAGE,
                "gpu":gpu_info(),
                "disk":disk_info(),
                "services":{"comfy":port_open(COMFY_PORT),"jupyter":port_open(JUPYTER_PORT)},
                "models":model_status(),
                "public_ports":{"dashboard":public_port(DASHBOARD_PORT),"comfy":public_port(COMFY_PORT),"jupyter":public_port(JUPYTER_PORT)},
                "public_host":public_host(),
                "jupyter_token":read_token(),
                "instance":os.getenv("VAST_CONTAINERLABEL","Vast instance"),
            });return
        if parsed.path=="/api/log":
            q=parse_qs(parsed.query);name=(q.get("name") or ["container"])[0]
            try:lines=max(20,min(int((q.get("lines") or ["300"])[0]),1000))
            except ValueError:lines=300
            if name not in LOG_FILES:self.send_json({"error":"unknown log"},404);return
            self.send_json({"name":name,"text":tail(LOG_FILES[name],lines)});return
        self.send_json({"error":"not found"},404)


def main():
    LOG_DIR.mkdir(parents=True,exist_ok=True)
    srv=ThreadingHTTPServer(("0.0.0.0",DASHBOARD_PORT),Handler)
    print(f"[dashboard] LTX 2.3 control panel listening on 0.0.0.0:{DASHBOARD_PORT}",flush=True)
    try:srv.serve_forever(poll_interval=.5)
    except KeyboardInterrupt:pass
    finally:srv.server_close()
    return 0


if __name__=="__main__":
    raise SystemExit(main())
