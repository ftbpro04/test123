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
PERSIST_ROOT = Path(os.getenv("LTX23_PERSIST_ROOT", "/workspace/ltx23-data"))
LOG_DIR = WORKSPACE / "logs"
STATUS_FILE = LOG_DIR / "ltx23-model-status.json"
COMFY_PORT = int(os.getenv("COMFY_PORT", "8188"))
JUPYTER_PORT = int(os.getenv("JUPYTER_PORT", "8888"))
DASHBOARD_PORT = int(os.getenv("DASHBOARD_PORT", "18080"))
PROFILE = "Exact 5-model"
BASE_IMAGE = os.getenv("LTX23_BASE_IMAGE", "antilopax/ltx23:v14")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")

LOG_FILES = {
    "models": LOG_DIR / "ltx23-model-download.log",
    "container": LOG_DIR / "ltx23-container.log",
    "jupyter": LOG_DIR / "jupyter.log",
    "dashboard": LOG_DIR / "ltx23-dashboard.log",
}

HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>LTX 2.3 Control Panel</title>
<style>
:root{color-scheme:dark;--bg:#0b0e14;--panel:#121722;--panel2:#171d2a;--line:#2a3345;--text:#eef3ff;--muted:#9aa8bd;--ok:#42d392;--warn:#f7c65f;--bad:#ff6b7a;--accent:#7c9cff;--accent2:#9a7cff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(circle at 15% -10%,#202a4d 0,transparent 35%),radial-gradient(circle at 90% 0,#2a1742 0,transparent 28%),var(--bg);color:var(--text);font:14px/1.45 Inter,ui-sans-serif,system-ui,-apple-system,Segoe UI,sans-serif;min-height:100vh}.wrap{max-width:1320px;margin:auto;padding:28px}.top{display:flex;justify-content:space-between;gap:20px;align-items:flex-start;margin-bottom:22px}.eyebrow{color:#a8b8ff;font-weight:700;letter-spacing:.12em;text-transform:uppercase;font-size:11px}.h1{font-size:30px;font-weight:800;margin:4px 0}.sub{color:var(--muted);max-width:760px}.pill{display:inline-flex;gap:8px;align-items:center;border:1px solid var(--line);background:#0f1420;padding:8px 11px;border-radius:999px;color:var(--muted)}.dot{width:9px;height:9px;border-radius:50%;background:var(--warn);box-shadow:0 0 12px currentColor}.dot.ok{background:var(--ok)}.dot.bad{background:var(--bad)}.grid{display:grid;grid-template-columns:repeat(12,1fr);gap:14px}.card{background:linear-gradient(180deg,rgba(24,30,44,.95),rgba(16,21,31,.95));border:1px solid var(--line);border-radius:16px;padding:17px;box-shadow:0 10px 30px rgba(0,0,0,.16)}.launch{grid-column:span 6}.stat{grid-column:span 3}.models{grid-column:span 7}.logs{grid-column:span 5}.title{font-weight:750;font-size:15px;margin-bottom:10px}.muted{color:var(--muted)}.btns{display:grid;grid-template-columns:1fr 1fr;gap:11px;margin-top:14px}.btn{display:flex;align-items:center;justify-content:center;gap:10px;border:1px solid #4b5f99;background:linear-gradient(135deg,#5878ff,#8059ef);color:#fff;text-decoration:none;padding:14px 16px;border-radius:12px;font-weight:800;font-size:15px;transition:.15s transform,.15s filter}.btn:hover{transform:translateY(-1px);filter:brightness(1.08)}.btn.secondary{background:#171e2d;border-color:#3a465d}.btn.disabled{opacity:.42;pointer-events:none}.metric{font-size:25px;font-weight:800;margin-top:4px}.tiny{font-size:12px;color:var(--muted)}.progress{height:10px;background:#0b1018;border-radius:999px;overflow:hidden;border:1px solid #263044}.bar{height:100%;width:0;background:linear-gradient(90deg,var(--accent),var(--accent2));transition:width .4s}.progressline{display:flex;justify-content:space-between;margin:10px 0 7px}.model-list{max-height:360px;overflow:auto;padding-right:4px}.model{display:grid;grid-template-columns:1fr auto;gap:8px;padding:10px 0;border-bottom:1px solid #242d3e}.model:last-child{border-bottom:0}.modelname{font-weight:650}.badge{align-self:start;border-radius:999px;padding:3px 8px;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.04em;background:#252d3b;color:#bac7da}.badge.ready{background:rgba(66,211,146,.13);color:#63e0a7}.badge.downloading{background:rgba(124,156,255,.14);color:#9db5ff}.badge.error{background:rgba(255,107,122,.14);color:#ff8996}.badge.queued{background:rgba(247,198,95,.13);color:#f7cc72}.tabs{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:10px}.tab{border:1px solid var(--line);background:#101622;color:var(--muted);border-radius:9px;padding:7px 10px;cursor:pointer;font:inherit}.tab.active{background:#222c42;color:#fff;border-color:#405176}.log{height:405px;overflow:auto;white-space:pre-wrap;word-break:break-word;background:#090d13;border:1px solid #242c3b;border-radius:11px;padding:12px;font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;color:#c7d2e2}.row{display:flex;justify-content:space-between;gap:12px;margin-top:7px}.service{display:flex;align-items:center;gap:8px}.svc-dot{width:8px;height:8px;border-radius:50%;background:var(--warn)}.svc-dot.ok{background:var(--ok)}.svc-dot.bad{background:var(--bad)}.footer{margin-top:16px;color:var(--muted);font-size:12px;text-align:center}@media(max-width:900px){.launch,.models,.logs{grid-column:span 12}.stat{grid-column:span 6}}@media(max-width:560px){.wrap{padding:17px}.top{display:block}.btns{grid-template-columns:1fr}.stat{grid-column:span 12}.h1{font-size:25px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div><div class="eyebrow">Vast.ai · LTX 2.3</div><div class="h1">Control Panel</div><div class="sub">One place to open ComfyUI and JupyterLab, watch the exact 5-model workflow download, inspect GPU usage, and follow live startup logs.</div></div>
    <div class="pill"><span id="overallDot" class="dot"></span><span id="overallText">Starting…</span></div>
  </div>

  <div class="grid">
    <section class="card launch">
      <div class="title">Launch apps</div>
      <div class="muted">The buttons automatically use the public ports assigned by Vast for this instance.</div>
      <div class="btns">
        <a id="comfyBtn" class="btn disabled" href="#" target="_blank" rel="noopener">Open ComfyUI</a>
        <a id="jupyterBtn" class="btn secondary disabled" href="#" target="_blank" rel="noopener">Open JupyterLab</a>
      </div>
      <div style="margin-top:14px">
        <div class="row"><span class="service"><span id="comfyDot" class="svc-dot"></span>ComfyUI</span><span id="comfyState" class="tiny">checking</span></div>
        <div class="row"><span class="service"><span id="jupyterDot" class="svc-dot"></span>JupyterLab</span><span id="jupyterState" class="tiny">checking</span></div>
        <div class="row"><span class="service"><span id="downloadDot" class="svc-dot"></span>Model downloader</span><span id="downloadState" class="tiny">checking</span></div>
      </div>
    </section>

    <section class="card stat"><div class="tiny">GPU</div><div id="gpuName" class="metric" style="font-size:18px">—</div><div id="gpuUtil" class="muted">—</div></section>
    <section class="card stat"><div class="tiny">VRAM</div><div id="vram" class="metric">—</div><div id="gpuTemp" class="muted">—</div></section>
    <section class="card stat"><div class="tiny">LTX persistent data</div><div id="disk" class="metric">—</div><div id="diskSub" class="muted">—</div></section>
    <section class="card stat"><div class="tiny">Workflow pack</div><div id="profile" class="metric" style="font-size:18px">—</div><div id="instance" class="muted">—</div></section>

    <section class="card models">
      <div class="title">Model download progress</div>
      <div class="progressline"><span id="modelSummary" class="muted">Waiting for downloader…</span><strong id="modelPct">0%</strong></div>
      <div class="progress"><div id="modelBar" class="bar"></div></div>
      <div id="modelList" class="model-list" style="margin-top:10px"></div>
    </section>

    <section class="card logs">
      <div class="title">Live logs</div>
      <div class="tabs">
        <button class="tab active" data-log="models">Models</button>
        <button class="tab" data-log="container">ComfyUI / container</button>
        <button class="tab" data-log="jupyter">Jupyter</button>
        <button class="tab" data-log="dashboard">Dashboard</button>
      </div>
      <pre id="logBox" class="log">Loading…</pre>
    </section>
  </div>
  <div class="footer">Auto-refreshes every 1.5 seconds · Dashboard port 18080</div>
</div>
<script>
let activeLog='models';
const $=id=>document.getElementById(id);
const fmtGB=n=>Number.isFinite(n)?(n/1024).toFixed(1)+' GB':'—';
function extUrl(host,publicPort,path=''){
  if(!publicPort) return null;
  return `http://${host||window.location.hostname}:${publicPort}${path}`;
}
function setSvc(name,up,text){
  $(name+'Dot').className='svc-dot '+(up?'ok':'bad');
  $(name+'State').textContent=text;
}
function renderModels(m){
  const list=$('modelList'); list.innerHTML='';
  const rows=m.models||[]; const ready=rows.filter(x=>['present','downloaded','ready'].includes((x.status||'').toLowerCase())).length;
  const sized=rows.filter(x=>Number(x.size_bytes)>0);
  const totalBytes=sized.reduce((a,x)=>a+Number(x.size_bytes||0),0);
  const doneBytes=sized.reduce((a,x)=>{
    const st=(x.status||'').toLowerCase();
    const n=['present','downloaded','ready'].includes(st)?Number(x.size_bytes||0):Math.min(Number(x.downloaded_bytes||0),Number(x.size_bytes||0));
    return a+n;
  },0);
  const pct=totalBytes>0?Math.min(100,Math.round(doneBytes/totalBytes*100)):(rows.length?Math.round(ready/rows.length*100):0);
  const bytesText=totalBytes>0?` · ${(doneBytes/1024/1024/1024).toFixed(1)} / ${(totalBytes/1024/1024/1024).toFixed(1)} GB`:'';
  $('modelSummary').textContent=rows.length?`${ready} of ${rows.length} models ready${bytesText}`:'No models selected';
  $('modelPct').textContent=pct+'%'; $('modelBar').style.width=pct+'%';
  for(const x of rows){
    const st=(x.status||'queued').toLowerCase();
    const cls=['present','downloaded','ready'].includes(st)?'ready':st==='downloading'?'downloading':st==='error'?'error':'queued';
    const el=document.createElement('div'); el.className='model';
    let progress='';
    if(Number(x.size_bytes)>0){
      const got=['present','downloaded','ready'].includes(st)?Number(x.size_bytes):Math.min(Number(x.downloaded_bytes||0),Number(x.size_bytes));
      const p=Math.min(100,Math.round(got/Number(x.size_bytes)*100));
      progress=` · ${(got/1024/1024/1024).toFixed(1)} / ${(Number(x.size_bytes)/1024/1024/1024).toFixed(1)} GB (${p}%)`;
    }
    el.innerHTML=`<div><div class="modelname"></div><div class="tiny"></div></div><span class="badge ${cls}"></span>`;
    el.querySelector('.modelname').textContent=x.name||'Model';
    el.querySelector('.tiny').textContent=(x.repo||'')+progress+(x.error?' · '+x.error:'');
    el.querySelector('.badge').textContent=st;
    list.appendChild(el);
  }
}
async function status(){
  try{
    const r=await fetch('/api/status',{cache:'no-store'}); const s=await r.json();
    $('profile').textContent=s.profile||'—';
    const rt=s.runtime||{};
    $('instance').textContent=(rt.torch||rt.cuda)?`Torch ${rt.torch||'—'} · CUDA ${rt.cuda||'—'}`:(s.instance||'Vast instance');
    if(s.gpu){$('gpuName').textContent=s.gpu.name||'GPU';$('gpuUtil').textContent=`${s.gpu.utilization_pct ?? '—'}% utilization`; $('vram').textContent=s.gpu.memory_total_mb?`${(s.gpu.memory_used_mb/1024).toFixed(1)} / ${(s.gpu.memory_total_mb/1024).toFixed(1)} GB`:'—'; $('gpuTemp').textContent=s.gpu.temperature_c!=null?`${s.gpu.temperature_c} °C · ${s.gpu.power_w ?? '—'} W`:'—';}
    if(s.disk){$('disk').textContent=fmtGB(s.disk.data_used_mb ?? 0);$('diskSub').textContent=`${fmtGB(s.disk.free_mb)} free of ${fmtGB(s.disk.total_mb)} volume`;}
    setSvc('comfy',s.services.comfy,s.services.comfy?'ready':'starting / unavailable');
    setSvc('jupyter',s.services.jupyter,s.services.jupyter?'ready':'starting / unavailable');
    $('downloadDot').className='svc-dot '+(s.services.downloader?'ok':(s.models.complete?'ok':'bad'));
    $('downloadState').textContent=s.models.complete?'complete':(s.services.downloader?'running':'not running');
    const host=s.public_host||window.location.hostname;
    const comfy=extUrl(host,s.public_ports.comfy,'/');
    const jupPath=s.jupyter_token?`/lab?token=${encodeURIComponent(s.jupyter_token)}`:'/lab';
    const jupyter=extUrl(host,s.public_ports.jupyter,jupPath);
    if(comfy){$('comfyBtn').href=comfy;$('comfyBtn').classList.remove('disabled')}
    if(jupyter){$('jupyterBtn').href=jupyter;$('jupyterBtn').classList.remove('disabled')}
    renderModels(s.models);
    const allGood=s.services.comfy && s.services.jupyter && (s.models.complete || s.services.downloader);
    $('overallDot').className='dot '+(allGood?'ok':''); $('overallText').textContent=s.models.complete&&s.services.comfy?'Ready':'Starting / downloading';
  }catch(e){$('overallDot').className='dot bad';$('overallText').textContent='Dashboard API error'}
}
async function logs(){
  try{const box=$('logBox');const nearBottom=box.scrollHeight-box.scrollTop-box.clientHeight<80;const r=await fetch(`/api/log?name=${encodeURIComponent(activeLog)}&lines=260`,{cache:'no-store'});const d=await r.json();box.textContent=d.text||'(no log output yet)';if(nearBottom)box.scrollTop=box.scrollHeight}catch(e){}
}
document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');activeLog=b.dataset.log;logs()}));
status();logs();setInterval(status,1500);setInterval(logs,1500);
</script>
</body></html>'''


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def pid_alive(path: Path) -> bool:
    try:
        pid = int(path.read_text().strip())
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def gpu_info() -> dict | None:
    cmd = [
        "nvidia-smi",
        "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw",
        "--format=csv,noheader,nounits",
    ]
    try:
        out = subprocess.check_output(cmd, text=True, timeout=2, stderr=subprocess.DEVNULL).strip().splitlines()[0]
        parts = [x.strip() for x in out.split(",")]
        return {
            "name": parts[0],
            "utilization_pct": float(parts[1]),
            "memory_used_mb": float(parts[2]),
            "memory_total_mb": float(parts[3]),
            "temperature_c": float(parts[4]),
            "power_w": float(parts[5]),
        }
    except Exception:
        return None


def runtime_info() -> dict:
    try:
        import torch
        return {"torch": str(torch.__version__), "cuda": str(torch.version.cuda or "unknown")}
    except Exception as exc:
        return {"torch": "unknown", "cuda": "unknown", "error": str(exc)}


def _dir_size_bytes(root: Path) -> int:
    total = 0
    try:
        for base, dirs, files in os.walk(root):
            for name in files:
                path = Path(base) / name
                try:
                    total += path.stat().st_size
                except (OSError, FileNotFoundError):
                    pass
    except Exception:
        pass
    return total


_disk_cache = {"at": 0.0, "data_used_bytes": 0}


def disk_info() -> dict:
    try:
        d = shutil.disk_usage(WORKSPACE)
        now_ts = time.time()
        if now_ts - _disk_cache["at"] > 10:
            _disk_cache["data_used_bytes"] = _dir_size_bytes(PERSIST_ROOT)
            _disk_cache["at"] = now_ts
        mb = 1024 * 1024
        return {
            "total_mb": d.total / mb,
            "used_mb": d.used / mb,
            "free_mb": d.free / mb,
            "data_used_mb": _disk_cache["data_used_bytes"] / mb,
        }
    except Exception:
        return {}


def load_model_status() -> dict:
    data = {"profile": PROFILE, "models": []}
    try:
        data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    rows = data.get("models") or []
    ready = sum(1 for r in rows if str(r.get("status", "")).lower() in {"present", "downloaded", "ready"})
    complete = bool(rows) and ready == len(rows) and not any(str(r.get("status", "")).lower() == "error" for r in rows)
    return {"profile": PROFILE, "models": rows, "ready": ready, "total": len(rows), "complete": complete}


def tail(path: Path, lines: int = 250, max_bytes: int = 256 * 1024) -> str:
    try:
        with path.open("rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - max_bytes), os.SEEK_SET)
            raw = f.read().decode("utf-8", errors="replace")
        return "\n".join(raw.splitlines()[-lines:])
    except FileNotFoundError:
        return ""
    except Exception as exc:
        return f"Unable to read log: {exc}"


def public_port(internal: int) -> int | None:
    value = os.getenv(f"VAST_TCP_PORT_{internal}")
    try:
        return int(value) if value else None
    except ValueError:
        return None


def public_host() -> str:
    return (
        os.getenv("PUBLIC_IPADDR")
        or os.getenv("VAST_IPADDR")
        or os.getenv("VAST_PUBLIC_IP")
        or ""
    )


def read_token() -> str:
    for path in [WORKSPACE / ".jupyter_token", Path("/root/.jupyter_token")]:
        try:
            token = path.read_text().strip()
            if token:
                return token
        except Exception:
            pass
    return os.getenv("JUPYTER_TOKEN", "")


class Handler(BaseHTTPRequestHandler):
    server_version = "LTX23Dashboard/1.0"

    def authorized(self) -> bool:
        if not DASHBOARD_PASSWORD:
            return True
        header = self.headers.get("Authorization", "")
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header.split(" ", 1)[1]).decode("utf-8")
            user, password = decoded.split(":", 1)
            return hmac.compare_digest(user, "ltx23") and hmac.compare_digest(password, DASHBOARD_PASSWORD)
        except Exception:
            return False

    def require_auth(self) -> None:
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="LTX 2.3 Dashboard"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, fmt: str, *args) -> None:
        print(f"[dashboard] {self.address_string()} - {fmt % args}", flush=True)

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/health" and not self.authorized():
            self.require_auth()
            return
        if parsed.path == "/":
            body = HTML.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if parsed.path == "/api/health":
            self.send_json({"ok": True, "time": time.time()})
            return
        if parsed.path == "/api/status":
            models = load_model_status()
            self.send_json({
                "profile": PROFILE,
                "base_image": BASE_IMAGE,
                "instance": BASE_IMAGE,
                "gpu": gpu_info(),
                "runtime": runtime_info(),
                "disk": disk_info(),
                "services": {
                    "comfy": port_open(COMFY_PORT),
                    "jupyter": port_open(JUPYTER_PORT),
                    "downloader": pid_alive(LOG_DIR / "ltx23-model-download.pid"),
                },
                "models": models,
                "public_ports": {
                    "dashboard": public_port(DASHBOARD_PORT),
                    "comfy": public_port(COMFY_PORT),
                    "jupyter": public_port(JUPYTER_PORT),
                },
                "public_host": public_host(),
                "jupyter_token": read_token(),
            })
            return
        if parsed.path == "/api/log":
            q = parse_qs(parsed.query)
            name = (q.get("name") or ["models"])[0]
            try:
                lines = max(20, min(int((q.get("lines") or ["250"])[0]), 1000))
            except ValueError:
                lines = 250
            if name not in LOG_FILES:
                self.send_json({"error": "unknown log"}, 404)
                return
            self.send_json({"name": name, "text": tail(LOG_FILES[name], lines)})
            return
        self.send_json({"error": "not found"}, 404)


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer(("0.0.0.0", DASHBOARD_PORT), Handler)
    print(f"[dashboard] LTX 2.3 control panel listening on 0.0.0.0:{DASHBOARD_PORT}", flush=True)
    print(f"[dashboard] Vast public mapping env: VAST_TCP_PORT_{DASHBOARD_PORT}={os.getenv(f'VAST_TCP_PORT_{DASHBOARD_PORT}', '')}", flush=True)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
