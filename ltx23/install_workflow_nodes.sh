#!/usr/bin/env bash
set -Eeuo pipefail
COMFY_ROOT="${1:-/opt/ComfyUI}"
export GIT_LFS_SKIP_SMUDGE=1
python - "$COMFY_ROOT" <<'PY'
import json, pathlib, subprocess, sys
root=pathlib.Path(sys.argv[1]); manifest=json.load(open('/opt/ltx23/node_manifest.json'))
for item in manifest['packages']:
    if item['repo']=='Comfy-Org/ComfyUI':continue
    dest=root/'custom_nodes'/item['directory']
    dest.mkdir(parents=True,exist_ok=True)
    subprocess.run(['git','init','-q',str(dest)],check=True)
    subprocess.run(['git','-C',str(dest),'fetch','--depth','1','https://github.com/'+item['repo']+'.git',item['commit']],check=True)
    subprocess.run(['git','-C',str(dest),'checkout','--detach','FETCH_HEAD'],check=True)
    if (dest/'requirements.txt').is_file():
        subprocess.run([sys.executable,'-m','pip','install','--no-cache-dir','-r',str(dest/'requirements.txt')],check=True)
    else:
        import tomllib
        if (dest/'pyproject.toml').is_file():
            config=tomllib.loads((dest/'pyproject.toml').read_text())
            deps=config.get('project',{}).get('dependencies',[])
            if deps:subprocess.run([sys.executable,'-m','pip','install','--no-cache-dir',*deps],check=True)
    actual=subprocess.check_output(['git','-C',str(dest),'rev-parse','HEAD'],text=True).strip()
    assert actual==item['commit'],(item['repo'],actual)
    print('Installed pinned node repository:',item['repo'],actual,flush=True)
PY
