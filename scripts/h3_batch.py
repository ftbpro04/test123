"""Persistent, sequential H3 video jobs. Only talks to local ComfyUI."""
import json, math, os, re, shutil, subprocess, threading, time, uuid
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

ROOT = Path(os.getenv('WORKSPACE', '/workspace'))
COMFY = ROOT / 'ComfyUI'
JOBS = ROOT / 'h3-batch'
URL = 'http://127.0.0.1:' + os.getenv('COMFY_PORT', '8188')
LOCK = threading.Lock()
ACTIVE = set()
DEFAULT_PROMPT = 'Replace the face and head of the adult subject in <Video 1> with the identity, facial features, hair and head accessories from <Picture 1>. Keep the original clothing, body, motion, expressions, camera, background and lighting from <Video 1>. Use <Picture 1> only for head identity. Maintain consistent identity and natural neck blending throughout.'

def jobdir(jid):
    if not re.fullmatch(r'[a-f0-9]{32}', jid): raise ValueError('Invalid job ID')
    return JOBS / jid

def read(jid): return json.loads((jobdir(jid) / 'state.json').read_text())
def save(s):
    p = jobdir(s['id']) / 'state.json'
    tmp = p.with_suffix('.tmp')
    tmp.write_text(json.dumps(s, indent=2)); tmp.replace(p)

def api(path, data=None):
    req = Request(URL + path, data=None if data is None else json.dumps(data).encode(), headers={'Content-Type':'application/json'})
    try:
        with urlopen(req, timeout=60) as r: return json.load(r)
    except HTTPError as e: raise RuntimeError(e.read().decode()[:3000]) from e

def run(args):
    p = subprocess.run([str(x) for x in args], capture_output=True, text=True)
    if p.returncode: raise RuntimeError(p.stderr[-3000:])
    return p.stdout

def probe(p): return json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',p]))
def ff(args): return run(['ffmpeg','-hide_banner','-loglevel','error','-y',*args])
def video_args(): return ['-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p']
def supported(n): return max(124, n + (5-n)%17)

def create(data):
    seed = int(data.get('seed',123456789))
    chunk = int(data.get('chunk_seconds',5)); edge = int(data.get('long_edge',768))
    if not 0 <= seed < 2**64 or chunk not in (5,10) or edge not in (768,1024,1344): raise ValueError('Invalid seed, chunk length or resolution')
    prompt = str(data.get('prompt','')).strip()
    if not prompt or len(prompt)>20000: raise ValueError('Enter a prompt (up to 20,000 characters)')
    strength = float(data.get('strength',1))
    if not math.isfinite(strength) or not 0 <= strength <= 2: raise ValueError('LoRA strength must be 0–2')
    jid=uuid.uuid4().hex; jobdir(jid).mkdir(parents=True)
    s=dict(id=jid,status='uploading',seed=str(seed),chunk_seconds=chunk,long_edge=edge,prompt=prompt,strength=strength,keep_audio=bool(data.get('keep_audio',True)),done=0,total=0,created=time.time(),pending=None)
    save(s); return s

def graph(s, clip, frames, prefix):
    def node(kind, **inputs): return {'class_type':kind,'inputs':inputs}
    return {
      '1':node('UNETLoader',unet_name='minimax_h3_ref2va_pruned_int8_convrot.safetensors',weight_dtype='default'),
      '2':node('CLIPLoader',clip_name='qwen3vl_32b_heretic_minimax_h3_nvfp4.safetensors',type='minimax',device='default'),
      '3':node('VAELoader',vae_name='minimax_h3_video_vae_fp16.safetensors'),
      '4':node('VAELoader',vae_name='minimax_h3_audio_vae_fp32.safetensors'),
      '5':node('Power Lora Loader (rgthree)',model=['1',0],lora_1={'on':True,'lora':'h3_character_swap_v1.5.safetensors','strength':s['strength']},lora_2={'on':True,'lora':'minimax_h3_fl2v_turbo_8step_v1.0_768p_comfyui_bf16.safetensors','strength':1}),
      '6':node('LoadImage',image=s['image']),
      '7':node('LoadVideo',file=clip),
      '8':node('GetVideoComponents',video=['7',0]),
      '9':node('MiniMaxH3ReferenceToVideo',clip=['2',0],vae=['3',0],audio_vae=['4',0],prompt=s['prompt'],width=s['width'],height=s['height'],length=frames,ref_image_size='match',**{'ref_images.ref_image_0':['6',0],'ref_videos.ref_video_0':['8',0]}),
      '10':node('RandomNoise',noise_seed=int(s['seed'])),
      '11':node('KSamplerSelect',sampler_name='er_sde'),
      '12':node('BasicScheduler',model=['5',0],scheduler='normal',steps=8,denoise=1),
      '13':node('BasicGuider',model=['5',0],conditioning=['9',0]),
      '14':node('SamplerCustomAdvanced',noise=['10',0],guider=['13',0],sampler=['11',0],sigmas=['12',0],latent_image=['9',1]),
      '15':node('VAEDecode',samples=['14',0],vae=['3',0]),
      '16':node('CreateVideo',images=['15',0],fps=24),
      '17':node('SaveVideo',video=['16',0],filename_prefix=prefix,format='mp4',**({'format.codec':'h264'} if s.get('save_dynamic') else {'codec':'h264'}))}

def output_file(history):
    status=history.get('status',{})
    if status.get('status_str')=='error': raise RuntimeError('ComfyUI failed: '+json.dumps(status.get('messages',[]))[-2500:])
    for values in history.get('outputs',{}).get('17',{}).values():
        if not isinstance(values,list): continue
        for item in values:
            if not isinstance(item,dict) or not item.get('filename'): continue
            if item.get('type','output') != 'output': continue
            p=(COMFY/'output'/item.get('subfolder','')/item['filename']).resolve()
            if p.is_relative_to((COMFY/'output').resolve()) and p.suffix.lower() in ('.mp4','.webm','.mkv') and p.is_file(): return p
    raise RuntimeError('ComfyUI finished without a saved output video')

def await_output(pid):
    deadline=time.monotonic()+24*3600
    while time.monotonic()<deadline:
        h=api('/history/'+pid)
        if pid in h: return output_file(h[pid])
        q=api('/queue')
        queued=any(row[1]==pid for key in ('queue_running','queue_pending') for row in q.get(key,[]))
        if not queued:
            # Recheck history to avoid the completion/queue-removal race.
            h=api('/history/'+pid)
            if pid in h: return output_file(h[pid])
            raise RuntimeError('Pending chunk is no longer in ComfyUI. Resume to resubmit it.')
        time.sleep(3)
    raise RuntimeError('Chunk exceeded 24 hours; check ComfyUI before resuming')

def process(jid):
    s=read(jid); d=jobdir(jid)
    try:
        s.update(status='preparing',error=None);save(s)
        api('/system_stats')
        info=api('/object_info/SaveVideo')['SaveVideo']['input']['required']['format']
        s['save_dynamic']=info[0]=='COMFY_DYNAMICCOMBO_V3'
        source=d/'source.mp4'
        if not source.exists(): raise ValueError('Upload the source video first')
        image=COMFY/'input'/s.get('image','missing')
        if not image.is_file(): raise ValueError('Upload the reference image first')
        if not (d/'normalized.mp4').exists():
            info=probe(source); v=next(x for x in info['streams'] if x['codec_type']=='video')
            # FFmpeg autorotates metadata; use the decoded normalized dimensions below.
            ff(['-i',source,'-map','0:v:0','-vf',f"fps=24,scale=w='if(gte(iw,ih),{s['long_edge']},-2)':h='if(gte(iw,ih),-2,{s['long_edge']})'",'-an',*video_args(),d/'normalizing.mp4'])
            (d/'normalizing.mp4').replace(d/'normalized.mp4')
        v=next(x for x in probe(d/'normalized.mp4')['streams'] if x['codec_type']=='video')
        count=int(v['nb_frames']); ratio=s['long_edge']/max(int(v['width']),int(v['height']))
        s.update(width=max(32,round(int(v['width'])*ratio/32)*32),height=max(32,round(int(v['height'])*ratio/32)*32),frames=count,total=math.ceil(count/(s['chunk_seconds']*24)))
        save(s)
        for i in range(s['total']):
            target=d/f'part-{i:05d}.mp4'
            if target.exists():
                s['done']=i+1
                if s.get('pending',{} ) and s['pending']['index']==i: s['pending']=None
                save(s);continue
            start=i*s['chunk_seconds']*24; n=min(s['chunk_seconds']*24,count-start); gen=supported(n)
            s.update(status='processing',current=i+1);save(s)
            clip_rel=f'h3-batch/{jid}/chunk-{i:05d}.mp4';clip=COMFY/'input'/clip_rel;clip.parent.mkdir(parents=True,exist_ok=True)
            if not clip.exists():
                ff(['-ss',str(start/24),'-i',d/'normalized.mp4','-an','-vf',f'trim=end_frame={n},setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={gen/24}','-frames:v',str(gen),*video_args(),clip])
            p=graph(s,clip_rel,gen,f'h3-batch/{jid}/generated-{i:05d}')
            (d/f'prompt-{i:05d}.json').write_text(json.dumps(p,indent=2))
            if not s.get('pending'):
                # Save a submission marker first: interrupted submission is reconciled by job/chunk metadata.
                s['pending']={'index':i,'id':None};save(s)
            if not s['pending']['id']:
                found=None
                for row in sum([api('/queue').get(k,[]) for k in ('queue_running','queue_pending')],[]):
                    if row[3].get('h3_batch')=={'job':jid,'chunk':i}: found=row[1]
                if not found:
                    for pid,h in api('/history').items():
                        prompt=h.get('prompt',[])
                        if len(prompt)>3 and prompt[3].get('h3_batch')=={'job':jid,'chunk':i}:
                            try: output_file(h);found=pid
                            except RuntimeError: pass
                if not found:
                    response=api('/prompt',{'prompt':p,'client_id':jid,'extra_data':{'h3_batch':{'job':jid,'chunk':i}}})
                    if 'prompt_id' not in response: raise RuntimeError(json.dumps(response))
                    found=response['prompt_id']
                s['pending']['id']=found;save(s)
            try: generated=await_output(s['pending']['id'])
            except RuntimeError:
                q=api('/queue');pid=s['pending']['id']
                if not any(row[1]==pid for k in ('queue_running','queue_pending') for row in q.get(k,[])): s['pending']=None
                raise
            ff(['-i',generated,'-an','-vf',f'fps=24,scale={s["width"]}:{s["height"]},setsar=1,tpad=stop_mode=clone:stop_duration={gen/24}','-frames:v',str(n),*video_args(),d/'part-tmp.mp4'])
            (d/'part-tmp.mp4').replace(target);s.update(done=i+1,pending=None);save(s)
        s['status']='stitching';save(s)
        (d/'concat.txt').write_text(''.join(f"file 'part-{i:05d}.mp4'\n" for i in range(s['total'])))
        ff(['-f','concat','-safe','1','-i',d/'concat.txt','-c','copy',d/'joined.mp4'])
        args=['-i',d/'joined.mp4']
        if s['keep_audio']: args+=['-i',source,'-map','0:v:0','-map','1:a:0?','-c:v','copy','-c:a','aac']
        else: args+=['-map','0:v:0','-c:v','copy','-an']
        ff([*args,'-t',str(count/24),'-movflags','+faststart',d/'final-tmp.mp4'])
        (d/'final-tmp.mp4').replace(d/'final.mp4');s.update(status='complete',error=None);save(s)
    except Exception as e:
        s.update(status='error',error=str(e));save(s)
    finally:
        with LOCK: ACTIVE.discard(jid)

def start(jid):
    with LOCK:
        s=read(jid)
        if ACTIVE: raise ValueError('A video is already processing. Wait for it to finish.')
        if s['status']=='complete': return s
        if not s.get('image') or not (jobdir(jid)/'source.mp4').exists(): raise ValueError('Upload both files first')
        ACTIVE.add(jid);s['status']='queued';save(s)
        threading.Thread(target=process,args=(jid,),daemon=True).start()
    return s

def route(h, method):
    from urllib.parse import urlparse
    path=urlparse(h.path).path
    if path=='/batch' and method=='GET':
        body=Path(__file__).with_name('h3_batch.html').read_bytes();h.send_response(200);h.send_header('Content-Type','text/html; charset=utf-8');h.send_header('Content-Length',str(len(body)));h.end_headers();h.wfile.write(body);return True
    if not path.startswith('/api/batch'): return False
    try:
        if method in ('POST','PUT'):
            origin=h.headers.get('Origin')
            if origin and urlparse(origin).netloc != h.headers.get('Host'): raise ValueError('Cross-origin requests are not allowed')
        parts=path.strip('/').split('/')
        if parts==['api','batch']:
            if method=='GET':
                rows=[]
                for p in sorted(JOBS.glob('*/state.json'),key=lambda p:p.stat().st_mtime,reverse=True):
                    s=json.loads(p.read_text())
                    if s['status'] in ('queued','preparing','processing','stitching') and s['id'] not in ACTIVE: s['status']='paused'
                    rows.append(s)
                h.send_json(rows);return True
            if method=='POST':
                size=int(h.headers.get('Content-Length','0'))
                if not 0<size<65536: raise ValueError('Invalid request size')
                h.send_json(create(json.loads(h.rfile.read(size))));return True
        if len(parts)!=4: raise ValueError('Unknown batch route')
        jid,action=parts[2:];d=jobdir(jid);s=read(jid)
        if method=='PUT' and action in ('video','image'):
            with LOCK:
                if jid in ACTIVE or s['status']!='uploading': raise ValueError('Cannot replace files after a job starts')
                size=int(h.headers.get('Content-Length','0'))
                limit=50*1024**3 if action=='video' else 50*1024**2
                if not 0<size<=limit: raise ValueError('Invalid upload size')
                suffix=Path(h.headers.get('X-Filename','')).suffix.lower()
                if action=='image' and suffix not in ('.png','.jpg','.jpeg','.webp'): raise ValueError('Use PNG, JPEG or WebP')
                p=d/'source.mp4' if action=='video' else COMFY/'input'/'h3-batch'/jid/('reference'+suffix)
                p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix('.upload')
                with tmp.open('wb') as f:
                    remaining=size
                    while remaining:
                        block=h.rfile.read(min(1024*1024,remaining))
                        if not block: raise ValueError('Upload interrupted')
                        f.write(block);remaining-=len(block)
                tmp.replace(p)
                if action=='image': s['image']=p.relative_to(COMFY/'input').as_posix();save(s)
            h.send_json({'ok':True});return True
        if method=='POST' and action=='start': h.send_json(start(jid));return True
        if method=='GET' and action=='download':
            p=d/'final.mp4'
            if s['status']!='complete' or not p.exists(): raise ValueError('Video is not ready')
            h.send_response(200);h.send_header('Content-Type','video/mp4');h.send_header('Content-Disposition',f'attachment; filename="H3-{jid[:8]}.mp4"');h.send_header('Content-Length',str(p.stat().st_size));h.end_headers()
            with p.open('rb') as f: shutil.copyfileobj(f,h.wfile)
            return True
        raise ValueError('Unknown batch route')
    except (ValueError,FileNotFoundError,KeyError) as e: h.send_json({'error':str(e)},400)
    except Exception as e: h.send_json({'error':str(e)},500)
    return True
