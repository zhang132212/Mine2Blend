"""Selection snapshots retain typed block/entity NBT and named components."""
import copy
from itertools import product
from .grid import BlockGrid,Region,position
from .transforms import state

def capture(grid,minimum,maximum):
    import nbtlib as n
    from .regions import shifted_entities,shifted_ticks
    lo,hi=position(minimum),position(maximum)
    if any(a>b for a,b in zip(lo,hi)):raise ValueError('Invalid selection bounds')
    fragment=BlockGrid('Clipboard',grid.data_version)
    size=tuple(b-a+1 for a,b in zip(lo,hi));region=Region('Clipboard',(0,0,0),size)
    inside=lambda p:all(a<=v<b+1 for a,v,b in zip(lo,p,hi))
    for p,b in grid.blocks.items():
        if inside(p):
            q=tuple(v-a for v,a in zip(p,lo));fragment._set(q,state(b,destination=q))
    ticks={}
    for source in grid.regions:
        for text in shifted_entities(source,lo):
            tag=n.parse_nbt(text)
            if all(0<=float(v)<s for v,s in zip(tag['Pos'],size)):region.entities.append(text)
        for key,text in shifted_ticks(source,lo).items():
            for tag in n.parse_nbt(text):
                if all(0<=int(tag[a])<s for a,s in zip('xyz',size)):ticks.setdefault(key,[]).append(tag)
    region.pending_ticks={k:n.List[n.Compound](v).snbt() for k,v in ticks.items()}
    fragment.regions=[region]
    for name,component in grid.components.items():
        if all(inside(p) for p in component['bounds']):
            item=copy.deepcopy(component);item['bounds']=[tuple(v-a for v,a in zip(p,lo)) for p in item['bounds']]
            fragment.components[name]=item
    return fragment.to_dict()

def paste(grid,data,origin,registry):
    import nbtlib as n
    from .regions import shifted_entities,shifted_ticks
    origin=position(origin);fragment=BlockGrid.from_dict(data)
    if len(fragment.blocks)>1_000_000:raise ValueError('Clipboard too large')
    changes=[]
    for p,b in fragment.blocks.items():
        q=tuple(v+a for v,a in zip(p,origin));b=registry.resolve(b.state,b.nbt)
        changes.append((q,state(b,destination=q)))
    metadata=grid.metadata()
    has_payload=any(r.entities or r.pending_ticks for r in fragment.regions)
    if has_payload:
        if not metadata['regions']:
            points=[origin,tuple(origin[i]+fragment.regions[0].size[i]-1 for i in range(3)),*(grid.bounds or [])]
            lo=tuple(min(p[i] for p in points) for i in range(3));hi=tuple(max(p[i] for p in points) for i in range(3))
            metadata['regions']=[Region('Main',lo,tuple(b-a+1 for a,b in zip(lo,hi))).__dict__]
        target=metadata['regions'][0]
        for source in fragment.regions:
            shifted=copy.deepcopy(source);shifted.origin=tuple(v+a for v,a in zip(source.origin,origin))
            target['entities'].extend(shifted_entities(shifted,target['origin']))
            for key,text in shifted_ticks(shifted,target['origin']).items():
                existing=list(n.parse_nbt(target['pending_ticks'].get(key,'[]')))
                target['pending_ticks'][key]=n.List[n.Compound](existing+list(n.parse_nbt(text))).snbt()
    for name,item in fragment.components.items():
        key=name
        while key in metadata['components']:key+=' copy'
        item=copy.deepcopy(item);item['bounds']=[tuple(v+a for v,a in zip(p,origin)) for p in item['bounds']]
        metadata['components'][key]=item
    return changes,metadata
