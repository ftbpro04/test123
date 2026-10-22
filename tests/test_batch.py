import sys,tempfile,unittest,shutil,json
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import h3_batch as b

class BatchTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
  self.patches=[patch.object(b,'ROOT',root),patch.object(b,'COMFY',root/'ComfyUI'),patch.object(b,'JOBS',root/'jobs')]
  for p in self.patches:p.start()
  (b.COMFY/'input').mkdir(parents=True);(b.COMFY/'output').mkdir()
  self.submissions=[];self.history={};self.fail_second=False
 def tearDown(self):
  for p in self.patches:p.stop()
  self.tmp.cleanup()
 def mock_api(self,path,data=None):
  if path=='/system_stats':return {}
  if path=='/object_info/SaveVideo':return {'SaveVideo':{'input':{'required':{'format':['COMFY_DYNAMICCOMBO_V3',{}]}}}}
  if path=='/queue':return {'queue_running':[],'queue_pending':[]}
  if path=='/history':return self.history
  if path.startswith('/history/'):return {k:v for k,v in self.history.items() if k==path.split('/')[-1]}
  if path=='/prompt':
   if self.fail_second and len(self.submissions)==1:raise RuntimeError('simulated interruption')
   self.submissions.append(data);pid=str(len(self.submissions));g=data['prompt'];name=f'fake-{pid}.mp4'
   shutil.copy(b.COMFY/'input'/g['7']['inputs']['file'],b.COMFY/'output'/name)
   self.history[pid]={'status':{'status_str':'success'},'outputs':{'17':{'images':[{'filename':name,'type':'output'}]}},'prompt':[0,pid,g,data['extra_data']]}
   return {'prompt_id':pid}
  raise AssertionError(path)
 def make_job(self,duration=6.25,audio=True):
  s=b.create({'prompt':'Use <Picture 1> in <Video 1>','seed':'18446744073709551615','keep_audio':audio});d=b.jobdir(s['id'])
  args=['-f','lavfi','-i',f'testsrc2=size=96x64:rate=30:duration={duration}']
  if audio:args+=['-f','lavfi','-i',f'sine=frequency=440:duration={duration}','-c:a','aac']
  b.ff([*args,*b.video_args(),d/'source.mp4'])
  (b.COMFY/'input'/'reference.png').write_bytes(b'fake image for mocked Comfy')
  s['image']='reference.png';b.save(s);return s
 def test_full_pipeline_resume_and_audio(self):
  s=self.make_job();jid=s['id'];self.fail_second=True
  with patch.object(b,'api',self.mock_api):
   b.process(jid)
   self.assertEqual(b.read(jid)['done'],1);self.assertEqual(b.read(jid)['status'],'error')
   self.fail_second=False;b.process(jid)
  result=b.read(jid);self.assertEqual(result['status'],'complete',result.get('error'));self.assertEqual(len(self.submissions),2)
  g0,g1=[x['prompt'] for x in self.submissions]
  for key in ('2','3','4','5','6','10','11','12'):self.assertEqual(g0[key],g1[key])
  self.assertEqual(g0['10']['inputs']['noise_seed'],2**64-1)
  self.assertEqual(g0['17']['inputs']['format.codec'],'h264')
  info=b.probe(b.jobdir(jid)/'final.mp4');v=next(x for x in info['streams'] if x['codec_type']=='video')
  self.assertEqual(int(v['nb_frames']),150)
  self.assertTrue(any(x['codec_type']=='audio' for x in info['streams']))
  self.assertAlmostEqual(float(v['duration']),6.25,places=2)
 def test_tiny_tail_and_no_audio(self):
  s=self.make_job(5.08,False)
  with patch.object(b,'api',self.mock_api):b.process(s['id'])
  result=b.read(s['id']);self.assertEqual(result['status'],'complete',result.get('error'))
  self.assertEqual(result['total'],2)
  info=b.probe(b.jobdir(s['id'])/'final.mp4')
  self.assertFalse(any(x['codec_type']=='audio' for x in info['streams']))
  self.assertEqual(int(info['streams'][0]['nb_frames']),result['frames'])
 def test_validation(self):
  with self.assertRaises(ValueError):b.jobdir('../bad')
  with self.assertRaises(ValueError):b.create({'prompt':'x','seed':-1})
  with self.assertRaises(ValueError):b.create({'prompt':'x','strength':float('nan')})
  for n in [1,120,240]:self.assertGreaterEqual(b.supported(n),n);self.assertEqual(b.supported(n)%17,5)

if __name__=='__main__':unittest.main()

class HTTPTests(unittest.TestCase):
 def test_upload_auth_routes_and_download(self):
  import dashboard as dashboard
  import threading, urllib.request, urllib.error
  from http.server import ThreadingHTTPServer
  with tempfile.TemporaryDirectory() as tmp, patch.object(b,'JOBS',Path(tmp)/'jobs'),patch.object(b,'COMFY',Path(tmp)/'ComfyUI'),patch.object(dashboard,'DASHBOARD_PASSWORD','test'):
   server=ThreadingHTTPServer(('127.0.0.1',0),dashboard.Handler)
   threading.Thread(target=server.serve_forever,daemon=True).start()
   url=f'http://127.0.0.1:{server.server_port}'
   import base64
   auth='Basic '+base64.b64encode(b'minimax:test').decode()
   def req(path,data=None,method=None,headers=None):
    r=urllib.request.Request(url+path,data=data,method=method,headers={'Authorization':auth,**(headers or {})})
    return urllib.request.urlopen(r)
   try:
    with self.assertRaises(urllib.error.HTTPError) as cm:urllib.request.urlopen(url+'/batch')
    self.assertEqual(cm.exception.code,401)
    self.assertIn(b'Process a full video',req('/batch').read())
    jid=json.load(req('/api/batch',json.dumps({'prompt':'test'}).encode()))['id']
    req(f'/api/batch/{jid}/video',b'video-data','PUT')
    req(f'/api/batch/{jid}/image',b'image-data','PUT',{'X-Filename':'face.png'})
    self.assertEqual((b.jobdir(jid)/'source.mp4').read_bytes(),b'video-data')
    self.assertEqual(len(json.load(req('/api/batch'))),1)
    with patch.object(b,'process',lambda jid:None):
     req(f'/api/batch/{jid}/start',b'','POST')
    with self.assertRaises(urllib.error.HTTPError):req(f'/api/batch/{jid}/image',b'change','PUT',{'X-Filename':'face.png'})
    b.ACTIVE.discard(jid)
    s=b.read(jid);s['status']='complete';b.save(s);(b.jobdir(jid)/'final.mp4').write_bytes(b'result')
    self.assertEqual(req(f'/api/batch/{jid}/download').read(),b'result')
    with self.assertRaises(urllib.error.HTTPError):req('/api/batch',b'{}','POST',{'Origin':'https://elsewhere.example'})
   finally:server.shutdown();server.server_close()
