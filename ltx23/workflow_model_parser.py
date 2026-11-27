#!/usr/bin/env python3
"""Audit actual graph selections; never promote catalogs/history to downloads."""
import argparse
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath

# Explicit schemas keep non-model widgets and historical metadata out of the pack.
LOADERS = {
    'CheckpointLoaderSimple': [('ckpt_name', 0, 'checkpoints')],
    'UNETLoader': [('unet_name', 0, 'diffusion_models')],
    'VAELoader': [('vae_name', 0, 'vae')],
    'DualCLIPLoader': [('clip_name1', 0, 'text_encoders'), ('clip_name2', 1, 'text_encoders')],
    'LTXAVTextEncoderLoader': [('text_encoder', 0, 'text_encoders'), ('ckpt_name', 1, 'checkpoints')],
    'LTXVAudioVAELoader': [('ckpt_name', 0, 'checkpoints')],
    'LatentUpscaleModelLoader': [('model_name', 0, 'latent_upscale_models')],
    'LoraLoaderModelOnly': [('lora_name', 0, 'loras')],
    'LTXICLoRALoaderModelOnly': [('lora_name', 0, 'loras')],
}
EXTENSIONS = ('.safetensors', '.gguf', '.ckpt', '.pt', '.pth', '.bin')

def strings(value, path=''):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for i, v in enumerate(value): yield from strings(v, f'{path}/{i}')
    elif isinstance(value, dict):
        for k, v in value.items(): yield from strings(v, f'{path}/{k}')

def graphs(workflow):
    yield 'root', workflow
    def subgraphs(container):
        for graph in container.get('definitions', {}).get('subgraphs', []):
            yield str(graph['id']), graph
            yield from subgraphs(graph)
    yield from subgraphs(workflow)

def safe_selection(value):
    value = value.replace('\\', '/')
    p = PurePosixPath(value)
    if p.is_absolute() or '..' in p.parts or ':' in value or not value:
        raise ValueError(f'Unsafe model selection: {value!r}')
    return str(p)

def audit(workflow):
    normalized = copy.deepcopy(workflow)
    models, occurrences, nodes, metadata = {}, [], [], []
    for graph_id, graph in graphs(normalized):
        for node in graph.get('nodes', []):
            kind, mode = node['type'], node.get('mode', 0)
            props = node.get('properties', {})
            nodes.append({'graph': graph_id, 'id': node['id'], 'type': kind,
                          'mode': mode, 'aux_id': props.get('aux_id'),
                          'cnr_id': props.get('cnr_id'), 'version': props.get('ver')})
            widgets = node.get('widgets_values', [])
            selected = []
            if kind == 'Power Lora Loader (rgthree)':
                entries = enumerate(widgets) if isinstance(widgets, list) else widgets.items()
                for key, item in entries:
                    if isinstance(item, dict) and item.get('lora') not in (None, '', 'None'):
                        selected.append((item, 'lora', 'loras', f'widgets_values/{key}/lora', item.get('on', True)))
            elif kind in LOADERS:
                for name, index, category in LOADERS[kind]:
                    key = name if isinstance(widgets, dict) else index
                    try: value = widgets[key]
                    except (KeyError, IndexError, TypeError):
                        raise ValueError(f'Missing loader widget: {kind} {node["id"]} {name}')
                    if not isinstance(value, str) or not value.lower().endswith(EXTENSIONS):
                        raise ValueError(f'Invalid configured model: {kind} {value!r}')
                    selected.append((widgets, key, category, f'widgets_values/{key}', True))
            elif any(v.lower().endswith(EXTENSIONS) for _, v in strings(widgets)):
                raise ValueError(f'Unclassified model widget in {kind} node {node["id"]}; add its schema')
            for owner, key, category, field, enabled in selected:
                original = owner[key]
                value = safe_selection(original)
                owner[key] = value
                dest = category + '/' + value
                classification = 'B' if mode in (2, 4) else ('C' if not enabled else 'A')
                occurrence = {'graph': graph_id, 'node_id': node['id'], 'node_type': kind,
                              'field': field, 'classification': classification, 'mode': mode,
                              'enabled': enabled, 'original_selection': original, 'selection': value}
                occurrences.append(occurrence)
                row = models.setdefault(dest, {'filename': PurePosixPath(value).name,
                    'category': category, 'selection': value, 'destination': dest,
                    'required': True, 'occurrences': []})
                row['occurrences'].append(occurrence)
            for path, value in strings(props):
                if '.safetensors' in value:
                    metadata.append({'classification': 'D', 'graph': graph_id, 'node_id': node['id'],
                                     'path': 'properties'+path, 'value': value,
                                     'reason': 'Informational property, not a selected widget'})
    for path, value in strings(workflow.get('extra', {})):
        if '.safetensors' in value:
            metadata.append({'classification': 'E', 'path': 'extra'+path, 'value': value,
                             'reason': 'Execution/frontend metadata; not used to add models'})
    return {'model_count': len(models), 'models': sorted(models.values(), key=lambda m:m['destination']),
            'nodes': nodes, 'metadata_references': metadata}, normalized

def main():
    p=argparse.ArgumentParser()
    p.add_argument('workflow', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--normalized', type=Path)
    p.add_argument('--expect', type=int, default=16)
    a=p.parse_args()
    result, normalized=audit(json.loads(a.workflow.read_text()))
    result['workflow_sha256']=hashlib.sha256(a.workflow.read_bytes()).hexdigest()
    if result['model_count'] != a.expect: raise SystemExit(f'Expected {a.expect}, got {result["model_count"]}')
    if a.output: a.output.write_text(json.dumps(result, indent=2)+'\n')
    if a.normalized: a.normalized.write_text(json.dumps(normalized, indent=2)+'\n')
    print(f'{len(result["nodes"])} nodes; {result["model_count"]} configured models; {len(result["metadata_references"])} metadata references classified')
if __name__=='__main__': main()
