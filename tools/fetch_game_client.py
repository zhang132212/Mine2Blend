"""Fetch checksum-verified public client/build dependencies for offline extraction.

Artifacts stay under ignored test-output. Never authenticates or starts the game.
"""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,urllib.request
ROOT=Path(__file__).resolve().parents[1];DEST=ROOT/'test-output/game-client'

def download(spec,path):
    if path.exists() and hashlib.sha1(path.read_bytes()).hexdigest()==spec['sha1']:return
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_suffix(path.suffix+'.download')
    urllib.request.urlretrieve(spec['url'],temp)
    if hashlib.sha1(temp.read_bytes()).hexdigest()!=spec['sha1']:raise ValueError('Checksum mismatch: '+str(path))
    temp.replace(path)

def main():
    manifest=json.load(urllib.request.urlopen('https://piston-meta.mojang.com/mc/game/version_manifest_v2.json'))
    version=next(v for v in manifest['versions'] if v['id']=='26.2')
    folder=DEST/'versions/26.2';metadata=folder/'26.2.json';download(version,metadata)
    data=json.loads(metadata.read_text());artifacts=[(data['downloads']['client'],folder/'26.2.jar')]
    for lib in data['libraries']:
        artifact=lib.get('downloads',{}).get('artifact')
        if artifact and 'natives-' not in artifact['path']:artifacts.append((artifact,DEST/'libraries'/artifact['path']))
    with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(lambda pair:download(*pair),artifacts))
    print('VANILLA_BUILD_CLIENT_OK',len(artifacts),'artifacts',version['sha1'])

if __name__=='__main__':main()
