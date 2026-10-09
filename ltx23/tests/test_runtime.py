import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from unittest.mock import patch
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import download_workflow_models as dm
from common import model_path,atomic_json
from workflow_model_parser import audit,safe_selection
APP=Path(__file__).resolve().parents[1]

class ParserTests(unittest.TestCase):
    def setUp(self):self.workflow=json.loads((APP/'workflows/original.json').read_text())
    def test_complete_inventory_and_metadata(self):
        a,w=audit(self.workflow)
        self.assertEqual(a['model_count'],16);self.assertEqual(len(a['nodes']),95)
        self.assertEqual(sum(o['classification']=='C' for m in a['models'] for o in m['occurrences']),6)
        self.assertEqual(sum(o['classification']=='B' for m in a['models'] for o in m['occurrences']),5)
        self.assertTrue(any('GLSLShader'==n['type'] for n in a['nodes']))
        self.assertFalse(any('x2-1.0' in m['filename'] for m in a['models']))
        self.assertEqual(len(a['metadata_references']),6)
        self.assertIn('ltx23/LTX2.3_reasoning_I2V_V3.safetensors',[m['selection'] for m in a['models']])
    def test_named_widgets(self):
        for n in self.workflow['nodes']:
            if n['type']=='UNETLoader':n['widgets_values']={'unet_name':n['widgets_values'][0]}
        self.assertEqual(audit(self.workflow)[0]['model_count'],16)
    def test_unknown_loader_fails_closed(self):
        self.workflow['nodes'].append({'id':999,'type':'UnknownLoader','widgets_values':['missing.safetensors']})
        with self.assertRaises(ValueError):audit(self.workflow)
    def test_path_traversal(self):
        for v in ('../oops.safetensors','/tmp/oops.safetensors','C:\\oops.safetensors'):
            with self.assertRaises(ValueError):safe_selection(v)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'models';root.mkdir();(root/'outside').symlink_to('/tmp')
            with self.assertRaises(ValueError):model_path(root,'outside/test')

DATA=b'fixture-safetensors-bytes'*10000
class RangeHandler(BaseHTTPRequestHandler):
    mode='range';received_ranges=[]
    def log_message(self,*a):pass
    def do_GET(self):
        self.__class__.received_ranges.append(self.headers.get('Range'))
        start=int(self.headers.get('Range','bytes=0-')[6:-1]);payload=DATA
        if self.mode=='range' and start:
            self.send_response(206);payload=DATA[start:];self.send_header('Content-Range',f'bytes {start}-{len(DATA)-1}/{len(DATA)}')
        elif self.mode=='invalid' and start:
            self.send_response(206);self.send_header('Content-Range',f'bytes 0-{len(DATA)-1}/{len(DATA)}')
        else:self.send_response(200)
        self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)

class DownloaderTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.parts=self.root/'downloads';self.parts.mkdir();self.target=self.root/'models/test.safetensors'
        self.server=ThreadingHTTPServer(('127.0.0.1',0),RangeHandler);threading.Thread(target=self.server.serve_forever,daemon=True).start()
        RangeHandler.mode='range';RangeHandler.received_ranges=[]
        self.m={'source_verified':True,'source':'civitai','url':f'http://127.0.0.1:{self.server.server_port}/model','destination':'test.safetensors','expected_size':len(DATA),'sha256':hashlib.sha256(DATA).hexdigest()}
        self.env=patch.dict(os.environ,{'LTX23_TEST_HTTP':'1'});self.env.start();self.bytes=0
    def tearDown(self):self.server.shutdown();self.server.server_close();self.env.stop();self.tmp.cleanup()
    def partial(self,n):
        key=hashlib.sha256(self.m['destination'].encode()).hexdigest()[:24]
        p=self.parts/(key+'.part');p.write_bytes(DATA[:n]);atomic_json(self.parts/(key+'.json'),{k:self.m[k] for k in ('destination','expected_size','sha256')});return p
    def receive(self,n):self.bytes+=n
    def run_transfer(self):dm.transfer(self.m,self.target,self.parts,lambda *a:None,self.receive,0)
    def test_resume_and_atomic_placement(self):
        self.partial(10000);self.run_transfer();self.assertEqual(self.target.read_bytes(),DATA);self.assertEqual(self.bytes,len(DATA)-10000);self.assertEqual(list(self.parts.iterdir()),[])
    def test_ignored_range_restarts(self):
        RangeHandler.mode='ignore';self.partial(10000);self.run_transfer();self.assertEqual(self.target.read_bytes(),DATA);self.assertEqual(self.bytes,len(DATA))
    def test_invalid_range_never_appends(self):
        RangeHandler.mode='invalid';part=self.partial(10000)
        with patch.object(dm.time,'sleep'),self.assertRaises(dm.DownloadError):self.run_transfer()
        self.assertEqual(part.stat().st_size,10000);self.assertFalse(self.target.exists())
    def test_hash_mismatch_not_ready(self):
        self.m['sha256']='0'*64
        with patch.object(dm.time,'sleep'),self.assertRaises(dm.DownloadError):self.run_transfer()
        self.assertFalse(self.target.exists())
    def test_disk_guard(self):
        with patch.object(dm.shutil,'disk_usage',return_value=shutil._ntuple_diskusage(100,95,5)),self.assertRaisesRegex(dm.DownloadError,'Insufficient disk space'):
            dm.disk_guard(self.root,6,1)
    def test_partial_identity_preserved(self):
        part=self.partial(10000);self.m['sha256']='1'*64
        with self.assertRaisesRegex(dm.DownloadError,'identity'):self.run_transfer()
        self.assertTrue(part.exists())
    def test_existing_models_use_zero_network(self):
        persist=self.root/'persist';(persist/'models').mkdir(parents=True);(persist/'models/test.safetensors').write_bytes(DATA)
        manifest=self.root/'manifest.json';atomic_json(manifest,{'models':[{**self.m,'filename':'test.safetensors','category':'loras'}]})
        with patch.object(dm,'PERSIST',persist),patch.object(dm,'RUNTIME',self.root/'runtime'),patch.object(dm,'MANIFEST',manifest),patch.object(dm,'request',side_effect=AssertionError('Network forbidden')):
            self.assertEqual(dm.run(),0);self.assertEqual(dm.run(),0)
        status=json.loads((self.root/'runtime/models.json').read_text());self.assertEqual(status['downloaded_this_launch'],0);self.assertEqual(status['reused_bytes'],len(DATA))
    def test_second_downloader_exits_without_mutation(self):
        import fcntl
        with (self.root/'.model-downloader.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch.object(dm,'PERSIST',self.root),patch.object(dm,'MANIFEST',Path('/missing')):self.assertEqual(dm.run(),0)

class SupervisorTests(unittest.TestCase):
    def test_comfy_crash_dashboard_survives_and_duplicate_start_safe(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);comfy=root/'ComfyUI';comfy.mkdir();(comfy/'main.py').write_text('raise RuntimeError("intentional-test-crash")')
            with socket.socket() as s:s.bind(('127.0.0.1',0));port=s.getsockname()[1]
            env={**os.environ,'WORKSPACE':str(root/'workspace'),'LTX23_PERSIST_ROOT':str(root/'workspace/ltx23-data'),'LTX23_RUNTIME_DIR':str(root/'runtime'),'COMFY_ROOT':str(comfy),'DASHBOARD_PORT':str(port),'ENABLE_JUPYTER':'0','DOWNLOAD_WORKFLOW_MODELS':'0'}
            p=subprocess.Popen([sys.executable,str(APP/'supervisor.py')],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            try:
                deadline=time.monotonic()+20
                while time.monotonic()<deadline:
                    try:
                        response=requests.get(f'http://127.0.0.1:{port}/api/status',timeout=1)
                        if response.ok and response.json()['services'].get('comfy',{}).get('state')=='Error':break
                    except requests.RequestException:pass
                    time.sleep(.2)
                else:self.fail('Dashboard or crash state unavailable')
                self.assertIsNone(p.poll());self.assertEqual(requests.get(f'http://127.0.0.1:{port}/api/health').status_code,200)
                state=response.json();self.assertIsNone(state['jupyter_token'])
                before=(root/'runtime/services.json').read_text()
                second=subprocess.run([sys.executable,str(APP/'supervisor.py')],env=env,capture_output=True,timeout=10)
                self.assertEqual(second.returncode,0);self.assertIn(b'already running',second.stdout)
                self.assertEqual(before,(root/'runtime/services.json').read_text())
                log=requests.get(f'http://127.0.0.1:{port}/api/logs?name=comfy').text
                self.assertIn('intentional-test-crash',log)
                self.assertIsNone(state['public_ports']['comfy'])
            finally:
                p.terminate();p.wait(timeout=15)

class AuthorSourceTests(unittest.TestCase):
    def test_matching_author_hash_verifies_mirror(self):
        from verify_author_sources import verify
        m={'filename':'a.safetensors','sha256':'a'*64,'expected_size':123,'source':'huggingface'}
        data={'files':[{'name':'a.safetensors','hashes':{'SHA256':'A'*64}}]}
        self.assertTrue(verify(m,data)['source_verified'])
    def test_wrong_filename_refused(self):
        from verify_author_sources import verify
        with self.assertRaisesRegex(dm.DownloadError,'filename'):
            verify({'filename':'a.safetensors'},{'files':[{'name':'b.safetensors'}]})
    def test_different_author_hash_never_replaces_mirror(self):
        from verify_author_sources import verify
        with self.assertRaisesRegex(dm.DownloadError,'differs'):
            verify({'filename':'a.safetensors','sha256':'a'*64},{'files':[{'name':'a.safetensors','hashes':{'SHA256':'b'*64}}]})
