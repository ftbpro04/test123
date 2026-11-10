import hashlib,json,os,time,struct,fcntl
from pathlib import Path
import requests
ROOT=Path(os.getenv('NEO_PERSIST_ROOT','/workspace/neo-data'))
LOG=Path(os.getenv('WORKSPACE','/workspace'))/'logs'
SPECS=[
 {'name':'FN Moment Anima Turbo','model_id':2733842,'kind':'Checkpoint','folder':'Stable-diffusion','version_env':'ANIMA_VERSION_ID'},
 {'name':'AIPlumpArt Style Anima','model_id':2507594,'kind':'LORA','folder':'Lora','version_env':'LORA_VERSION_ID'},
 {'name':'qwen_3_06b_base.safetensors','folder':'text_encoder','url':'https://huggingface.co/circlestone-labs/Anima/resolve/main/split_files/text_encoders/qwen_3_06b_base.safetensors'},
 {'name':'qwen_image_vae.safetensors','folder':'VAE','url':'https://huggingface.co/Comfy-Org/Qwen-Image_ComfyUI/resolve/main/split_files/vae/qwen_image_vae.safetensors'}]
SPECS += [
 {'name':'Nova 3DCG AM','model_id':2678095,'kind':'Checkpoint','folder':'Stable-diffusion','version_id':'3370060'},
 {'name':'General Butch GB Style Anima','model_id':2715148,'kind':'LORA','folder':'Lora','version_id':'3050606'},
 {'name':'Breast Size Slider','model_id':2692638,'kind':'LORA','folder':'Lora','version_id':'3144574'},
 {'name':'4x-AnimeSharp.pth','folder':'ESRGAN','format':'pth','sha':'e7a7de2dafd7331c1992862bbbcd9e9712a9f9f8e6303f0aaa59b4341d359bab','url':'https://huggingface.co/Kim2091/AnimeSharp/resolve/7696d95ced82b0c1f2a41f6ac73336133f0a90e1/4x-AnimeSharp.pth'},
 {'name':'4x-UltraSharp.pth','folder':'ESRGAN','format':'pth','sha':'a5812231fc936b42af08a5edba784195495d303d5b3248c24489ef0c4021fe01','url':'https://huggingface.co/lokCX/4x-Ultrasharp/resolve/1856559b50de25116a7c07261177dd128f1f5664/4x-UltraSharp.pth'}
]
def headers(url):
 from urllib.parse import urlparse
 token=os.getenv('CIVITAI_API_KEY','') if urlparse(url).hostname=='civitai.com' else os.getenv('HF_TOKEN','') if urlparse(url).hostname=='huggingface.co' else ''
 return {'Authorization':'Bearer '+token} if token else {}
def get(url,**kw):
 r=requests.get(url,headers=headers(url),timeout=(30,120),**kw)
 if not r.ok:raise RuntimeError(f'HTTP {r.status_code}: check access, API token, version and availability')
 return r

def valid(path,sha=None,format="safetensors"):
 if not path.is_file():return False
 try:
  if format == 'pth':
   if not sha: return False
   with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().lower()==sha.lower()
  with path.open('rb') as f:
   n=struct.unpack('<Q',f.read(8))[0]
   if not 2<n<100_000_000:return False
   h=json.loads(f.read(n));length=path.stat().st_size-8-n
   ends=[v['data_offsets'][1] for k,v in h.items() if k!='__metadata__']
   if not ends or max(ends)!=length:return False
  if sha:
   with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest().lower()==sha.lower()
  return True
 except Exception:return False

def resolve(s):
 pin=str(s['version_id']) if s.get('version_id') else os.getenv(s.get('version_env',''))
 cache=ROOT/'metadata'/f"{s['model_id']}-{pin or 'selected'}.json"
 if cache.exists():return json.loads(cache.read_text())
 d=get(f"https://civitai.com/api/v1/models/{s['model_id']}").json()
 if d.get('type','').lower()!=s['kind'].lower():raise RuntimeError('Unexpected model type')
 versions=d.get('modelVersions',[])
 versions=[v for v in versions if (not pin or str(v['id'])==pin) and 'anima' in v.get('baseModel','').lower()]
 if not versions:raise RuntimeError('No matching Anima version; set explicit version ID')
 v=versions[0];files=[f for f in v['files'] if f.get('type')=='Model' and f['name'].endswith('.safetensors')]
 files.sort(key=lambda f:not f.get('primary',False))
 if not files:raise RuntimeError('No safetensors model file available')
 f=files[0];result={'name':Path(f['name']).name,'url':f['downloadUrl'],'sha':f.get('hashes',{}).get('SHA256'),'version_id':v['id'],'baseModel':v['baseModel'],'trainedWords':v.get('trainedWords',[])}
 cache.parent.mkdir(parents=True,exist_ok=True);cache.write_text(json.dumps(result,indent=2));return result

def main():
 ROOT.mkdir(parents=True,exist_ok=True);LOG.mkdir(parents=True,exist_ok=True)
 lock=(ROOT/'.download.lock').open('w');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
 rows=[dict(name=s['name'],status='queued') for s in SPECS]
 def save():
  p=LOG/'neo-model-status.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps({'models':rows}));tmp.replace(p)
 save();failed=False
 for s,row in zip(SPECS,rows):
  try:
   m=resolve(s) if 'model_id' in s else s
   path=ROOT/'models'/s['folder']/m['name'];path.parent.mkdir(parents=True,exist_ok=True)
   row.update(name=m['name'],repo='Civitai' if 'model_id' in s else 'Hugging Face')
   if valid(path,m.get('sha'),m.get('format','safetensors')):row.update(status='present',size_bytes=path.stat().st_size);save();continue
   row['status']='downloading';save();part=path.with_suffix('.part')
   for attempt in range(3):
    try:
     with get(m['url'],stream=True) as r,part.open('wb') as out:
      if 'text/html' in r.headers.get('Content-Type',''):raise RuntimeError('Server returned HTML instead of model')
      row.update(size_bytes=int(r.headers.get('Content-Length',0)),downloaded_bytes=0);last=0
      for chunk in r.iter_content(4*1024*1024):
       out.write(chunk);row['downloaded_bytes']+=len(chunk)
       if time.monotonic()-last>1:save();last=time.monotonic()
     if not valid(part,m.get('sha'),m.get('format','safetensors')):raise RuntimeError('Model integrity verification failed')
     part.replace(path);break
    except Exception:
     if attempt==2:raise
     time.sleep(2**attempt)
   row.update(status='downloaded',size_bytes=path.stat().st_size)
  except Exception as e:
   failed=True;row.update(status='error',error=str(e) if isinstance(e,RuntimeError) else type(e).__name__);print(row['name']+': '+row['error'],flush=True)
  save()
 if not failed:
  config=ROOT/'config.json'
  import ast, shutil
  source=ast.parse(Path('/opt/forge-neo/modules/launch_utils.py').read_text())
  version=next(ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) and n.target.id=='VERSION_UID')
  if not config.exists():
   config.write_text(json.dumps({'VERSION_UID':version,'sd_model_checkpoint':rows[0]['name'],'forge_additional_modules':[str(ROOT/'models/text_encoder/qwen_3_06b_base.safetensors'),str(ROOT/'models/VAE/qwen_image_vae.safetensors')]},indent=2))
  else:
   settings=json.loads(config.read_text())
   # Repair only the small fresh config generated by this template, never migrate old user configs.
   if 'VERSION_UID' not in settings and set(settings)<= {'sd_model_checkpoint','forge_additional_modules'}:
    backup=config.with_name('config.before-version-fix.json')
    if not backup.exists(): shutil.copy2(config,backup)
    settings['VERSION_UID']=version
    tmp=config.with_suffix('.tmp');tmp.write_text(json.dumps(settings,indent=2));tmp.replace(config)
 return int(failed)
if __name__=='__main__':raise SystemExit(main())
