"""Debounced scene serialization; background work receives immutable snapshots."""
import copy,json,logging
from concurrent.futures import ThreadPoolExecutor
POOL=None
PENDING={}
SAVED={}

def signature(grids):return tuple((g.id,g.revision) for g in grids)

def snapshots(grids):
    result=[]
    for g in grids:
        clone=copy.copy(g);clone.blocks=dict(g.blocks)
        for key in ('regions','components','source_metadata','view','resource_packs'):setattr(clone,key,copy.deepcopy(getattr(g,key)))
        result.append(clone)
    return result

def encode(grids):return json.dumps([g.to_dict() for g in grids],separators=(',',':'))

def schedule(key,grids):
    global POOL
    sig=signature(grids)
    if key in PENDING or SAVED.get(key)==sig:return
    if POOL is None:POOL=ThreadPoolExecutor(max_workers=1,thread_name_prefix='m2b-scene-save')
    frozen=snapshots(grids);PENDING[key]=(sig,POOL.submit(encode,frozen))

def collect(key):
    if key not in PENDING:return None
    sig,future=PENDING[key]
    if not future.done():return None
    PENDING.pop(key)
    try:
        value=future.result();SAVED[key]=sig;return value
    except Exception:logging.getLogger('mine2blend').exception('Scene serialization failed');return None

def clear():
    for sig,future in PENDING.values():future.cancel()
    PENDING.clear();SAVED.clear()

def stop():
    global POOL
    clear()
    if POOL is not None:POOL.shutdown(wait=False,cancel_futures=True);POOL=None
