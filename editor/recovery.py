"""Atomic compressed snapshots, retaining five revisions per scene."""
from pathlib import Path
import gzip,json,os,tempfile,time
from .grid import BlockGrid

def save(grids,folder,scene_id):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    safe=''.join(c for c in scene_id if c.isalnum() or c in '_-')
    target=folder/f'{safe}-{time.time_ns()}.m2b.json.gz'
    payload=json.dumps({'schema':1,'created':time.time(),'grids':[g.to_dict() for g in grids]},separators=(',',':')).encode()
    fd,temp=tempfile.mkstemp(dir=folder,suffix='.tmp');os.close(fd)
    try:
        with gzip.open(temp,'wb') as stream:stream.write(payload)
        os.replace(temp,target)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    for older in sorted(folder.glob(safe+'-*.m2b.json.gz'),reverse=True)[5:]:older.unlink()
    return str(target)

def load(path):
    with gzip.open(path,'rb') as stream:data=json.load(stream)
    if data.get('schema')!=1:raise ValueError('Unknown recovery format')
    return [BlockGrid.from_dict(d) for d in data['grids']]
