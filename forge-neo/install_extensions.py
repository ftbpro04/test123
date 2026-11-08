import json,subprocess
from pathlib import Path
for e in json.loads(Path('/opt/template/extensions.json').read_text()):
 p=Path('/opt/forge-neo/extensions')/e['name']
 subprocess.run(['git','clone',e['url'],str(p)],check=True)
 subprocess.run(['git','-C',str(p),'checkout',e['ref']],check=True)
