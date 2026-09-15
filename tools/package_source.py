"""Archive tracked and untracked non-ignored source; excludes env, caches and artifacts."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile
import tomllib
ROOT=Path(__file__).resolve().parents[1]
files=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode('utf-8').split('\0')
version=tomllib.loads((ROOT/'blender_manifest.toml').read_text(encoding='utf-8'))['version']
target=ROOT/f'dist/Mine2Blend-Editor-{version}-source.zip'
with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as archive:
    for name in sorted(set(files)):
        if name and (ROOT/name).is_file():
            archive.write(ROOT/name,'Mine2Blend-Editor/'+name)
report={}
for path in sorted((ROOT/'dist').glob('*.zip')):
    report[path.name]={'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
(ROOT/'dist/artifacts.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
