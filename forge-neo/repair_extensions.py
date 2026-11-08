import os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
root=Path(os.environ.get('NEO_PERSIST_ROOT','/workspace/neo-data'))
ext=Path('/opt/forge-neo/extensions').resolve()
backup=root/'extension-backups'/time.strftime('%Y%m%d-%H%M%S')
repos=[('sd-civitai-browser-plus','https://github.com/eduardoabreu81/sd-civitai-browser-neo.git','bccaaa78a3549944a302414d857bc5936a631ae5'),('sd-dynamic-prompts','https://github.com/abzaloff/sd-dynamic-prompts.git','3e62452776f52e2c641c2c52d3cd908140c3743e')]
def run(*args,**kwargs):subprocess.run(args,check=True,**kwargs)
root.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(prefix='neo-repair-',dir=root) as tmp:
 staging=Path(tmp)
 for name,url,ref in repos:
  p=staging/name
  run('git','clone','--quiet',url,str(p));run('git','-C',str(p),'checkout','--quiet',ref)
  if name=='sd-civitai-browser-plus':run(sys.executable,'-m','pip','install','-r',str(p/'requirements.txt'))
  else:
   run(sys.executable,str(p/'install.py'),cwd=p)
   old=ext/name/'wildcards'
   if old.is_dir():shutil.copytree(old,p/'wildcards',dirs_exist_ok=True)
 backup.mkdir(parents=True,exist_ok=False)
 for name,_,_ in repos:
  target=ext/name
  if target.exists():shutil.move(str(target),str(backup/name))
  try:shutil.move(str(staging/name),str(target))
  except Exception:
   if (backup/name).exists():shutil.move(str(backup/name),str(target))
   raise
print('Installed the Neo forks. Previous extensions backed up to:',backup)
print('Stop and start the SAME Vast instance. Models and generated images were not changed.')
