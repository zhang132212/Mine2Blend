"""Reframe export regions while retaining world-space entities and scheduled ticks."""
import copy
from .grid import Region

def validate_disjoint(regions):
    bounds=[]
    for r in regions:
        end=tuple(r.origin[i]+r.size[i]-(1 if r.size[i]>0 else -1) for i in range(3))
        lo=tuple(min(a,b) for a,b in zip(r.origin,end));hi=tuple(max(a,b) for a,b in zip(r.origin,end))
        for other,a,b in bounds:
            if all(x<=v and u<=y for x,y,u,v in zip(lo,hi,a,b)):
                raise ValueError(f'Export regions overlap: {other} and {r.name}')
        bounds.append((r.name,lo,hi))

def shifted_entities(region,origin):
    import nbtlib as n
    result=[]
    for text in region.entities:
        tag=n.parse_nbt(text)
        tag['Pos']=n.List[n.Double]([float(tag['Pos'][i])+region.origin[i]-origin[i] for i in range(3)])
        for i,a in enumerate('XYZ'):
            if 'Tile'+a in tag:tag['Tile'+a]=n.Int(int(tag['Tile'+a])+region.origin[i]-origin[i])
        result.append(tag.snbt())
    return result

def shifted_ticks(region,origin):
    import nbtlib as n
    result={}
    for key,text in region.pending_ticks.items():
        tags=n.parse_nbt(text)
        for tag in tags:
            for i,a in enumerate('xyz'):
                if a in tag:tag[a]=n.Int(int(tag[a])+region.origin[i]-origin[i])
        result[key]=tags.snbt()
    return result

def fit(grid,name='Main'):
    import nbtlib as n
    points=list(grid.bounds or [])
    for r in grid.regions:
        points.extend((r.origin,tuple(r.origin[i]+r.size[i]-(1 if r.size[i]>0 else -1) for i in range(3))))
    if not points:raise ValueError('Grid has no blocks or regions')
    lo=tuple(min(p[i] for p in points) for i in range(3));hi=tuple(max(p[i] for p in points) for i in range(3))
    result=Region(name,lo,tuple(b-a+1 for a,b in zip(lo,hi)))
    ticks={}
    for r in grid.regions:
        result.entities.extend(shifted_entities(r,lo))
        for key,text in shifted_ticks(r,lo).items():ticks.setdefault(key,[]).extend(n.parse_nbt(text))
    result.pending_ticks={key:n.List[n.Compound](items).snbt() for key,items in ticks.items()}
    return result
