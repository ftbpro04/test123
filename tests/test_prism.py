import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
class PrismTests(unittest.TestCase):
    def test_workflow_wiring_and_recipe(self):
        w=json.loads((ROOT/'workflows/MiniMax-H3-PRISM-DMAD-PDMD-I2V-PowerLoRA.json').read_text())
        nodes={n['id']:n for n in w['nodes']}
        self.assertEqual(len(nodes),len(w['nodes']))
        for lid,src,slot,dst,inp,kind in w['links']:
            self.assertIn(lid,nodes[src]['outputs'][slot]['links'])
            self.assertEqual(nodes[dst]['inputs'][inp]['link'],lid)
            self.assertEqual(nodes[src]['outputs'][slot]['type'],kind)
            self.assertIn(kind,nodes[dst]['inputs'][inp]['type'].split(','))
        link_ids={l[0] for l in w['links']}
        for n in nodes.values():
            for i in n.get('inputs',[]):
                if i.get('link') is not None:self.assertIn(i['link'],link_ids)
            for o in n.get('outputs',[]):
                for lid in o.get('links') or []:self.assertIn(lid,link_ids)
        self.assertEqual(nodes[124]['widgets_values'],[8,.5,.7])
        self.assertEqual(nodes[151]['widgets_values'],[12.,3.])
        self.assertEqual(nodes[152]['widgets_values'],[0])
        self.assertEqual(nodes[127]['widgets_values'][0],'PRISM_DMAD_PDMD_int8.safetensors')
        self.assertFalse(any(n['type']=='LoadVideo' for n in nodes.values()))
        self.assertFalse(any(row.get('on') for row in nodes[147]['widgets_values']))
        self.assertIn([296,147,0,151,0,'MODEL'],w['links'])
        self.assertIn([300,137,0,152,4,'IMAGE'],w['links'])
    def test_manifest_matches_installer(self):
        tree=ast.parse((ROOT/'scripts/download_models.py').read_text())
        models=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MODELS' for t in n.targets))
        self.assertEqual(models,json.loads((ROOT/'MODEL_MANIFEST.json').read_text())['models'])
        prism=[m for m in models if m['remote_path']=='PRISM_DMAD_PDMD_int8.safetensors']
        self.assertEqual(len(prism),1)
        self.assertEqual(prism[0]['expected_size'],20284678584)
        self.assertEqual(prism[0]['sha256'],'948e1d56621f5e76677d515939c716ebf85de8131e4e498013c87ec9e4edba46')
    def test_checksum_rejects_same_size_corruption(self):
        # Exercise the pure verifier without importing inference/download dependencies.
        source=(ROOT/'scripts/download_models.py').read_text()
        tree=ast.parse(source)
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='verify_pinned_model')
        ns={'Path':Path,'hashlib':hashlib,'json':json,'os':__import__('os')}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'<verifier>','exec'),ns)
        data=b'checkpoint';model={'expected_size':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'weight.safetensors';p.write_bytes(data)
            self.assertTrue(ns['verify_pinned_model'](model,p))
            self.assertTrue(ns['verify_pinned_model'](model,p))
            p.write_bytes(b'x'*len(data))
            self.assertFalse(ns['verify_pinned_model'](model,p))

if __name__=='__main__':unittest.main()

class AutoPromptTests(unittest.TestCase):
    def test_image_and_text_reach_prompt_then_h3(self):
        w=json.loads((ROOT/'workflows/MiniMax-H3-PRISM-DMAD-PDMD-I2V-PowerLoRA-AutoPrompt.json').read_text())
        ns={n['id']:n for n in w['nodes']}
        for lid,src,slot,dst,inp,kind in w['links']:
            self.assertIn(lid,ns[src]['outputs'][slot]['links'])
            self.assertEqual(ns[dst]['inputs'][inp]['link'],lid)
        self.assertIn([301,138,0,153,0,'STRING'],w['links'])
        self.assertIn([302,137,0,153,1,'IMAGE'],w['links'])
        self.assertIn([279,153,0,136,9,'STRING'],w['links'])
        self.assertIn([303,153,0,154,0,'STRING'],w['links'])
        self.assertEqual(ns[153]['type'],'AILab_QwenVL_Advanced')
        self.assertEqual(ns[153]['widgets_values'][0],'Qwen3.5-4B-heretic-v2')
        self.assertFalse(ns[153]['widgets_values'][13])
        self.assertFalse(ns[153]['widgets_values'][17])
        self.assertEqual(ns[124]['widgets_values'],[8,.5,.7])
        self.assertEqual(ns[151]['widgets_values'],[12.,3.])
    def test_configuration_preserves_existing_models(self):
        spec=importlib.util.spec_from_file_location('configure_qwen',ROOT/'scripts/configure_qwen.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'custom_models.json';p.write_text(json.dumps({'hf_vl_models':{'mine':{'repo_id':'my/model'}}}))
            module.configure(d);module.configure(d)
            models=json.loads(p.read_text())['hf_vl_models']
            self.assertEqual(models['mine']['repo_id'],'my/model')
            self.assertEqual(models['Qwen3.5-4B-heretic-v2']['repo_id'],'tvall43/Qwen3.5-4B-heretic-v2')
