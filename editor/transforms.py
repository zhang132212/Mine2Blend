"""Integer-grid transforms with directional property and typed NBT preservation."""
from .grid import BlockRecord, DIRECTIONS, position

HORIZONTAL = ("north", "east", "south", "west")
RAILS = {frozenset(v): k for k,v in {
    "north_south": ("north","south"), "east_west": ("east","west"),
    "north_east": ("north","east"), "north_west": ("north","west"),
    "south_east": ("south","east"), "south_west": ("south","west")}.items()}

def direction(value, turns=0, mirror=None):
    if value not in DIRECTIONS:
        return value
    if mirror == "x": value = {"east":"west","west":"east"}.get(value,value)
    if mirror == "z": value = {"north":"south","south":"north"}.get(value,value)
    if value in HORIZONTAL: value = HORIZONTAL[(HORIZONTAL.index(value)+turns)%4]
    return value

def coordinate(p, pivot=(0,0,0), turns=0, mirror=None, offset=(0,0,0)):
    x,y,z = (p[i]-pivot[i] for i in range(3))
    if mirror == "x": x = -x
    if mirror == "z": z = -z
    for _ in range(turns%4): x,z = -z,x
    return tuple(v+pivot[i]+offset[i] for i,v in enumerate((x,y,z)))

def state(block, turns=0, mirror=None, destination=None):
    if mirror not in (None,"x","z"):
        raise ValueError("Mirror axis must be x or z")
    props = dict(block.properties)
    output = {}
    for key,value in props.items():
        key = direction(key,turns,mirror)
        if key in ("facing","horizontal_facing","vertical_direction"):
            value = direction(value,turns,mirror)
        elif key == "axis" and turns%2:
            value = {"x":"z","z":"x"}.get(value,value)
        elif key == "rotation":
            n = int(value)
            if mirror == "x": n = -n
            if mirror == "z": n = 8-n
            value = str((n+turns*4)%16)
        elif key == "shape" and value.startswith("ascending_"):
            value = "ascending_" + direction(value[10:],turns,mirror)
        elif key == "shape" and frozenset(value.split("_")) in RAILS:
            value = RAILS[frozenset(direction(d,turns,mirror) for d in value.split("_"))]
        elif key == "orientation":
            value = "_".join(direction(d,turns,mirror) for d in value.split("_"))
        if mirror and (key == "hinge" or key == "type" and block.block_id.endswith("chest")):
            value = {"left":"right","right":"left"}.get(value,value)
        if mirror and key == "shape" and value.endswith(("_left","_right")):
            base,side=value.rsplit("_",1)
            value=base+"_"+{"left":"right","right":"left"}[side]
        output[key] = value
    nbt=block.nbt
    if nbt:
        from .formats import dependencies
        nl,_=dependencies()
        tag=nl.parse_nbt(nbt)
        if destination:
            for k,v in zip("xyz",destination): tag[k]=nl.Int(v)
        # Vanilla directional fields used by block entities (unknown payload stays typed).
        if "Rot" in tag:
            n=int(tag["Rot"])
            if mirror == "x": n=-n
            if mirror == "z": n=8-n
            tag["Rot"]=type(tag["Rot"])((n+4*turns)%16)
        ids={0:"down",1:"up",2:"north",3:"south",4:"west",5:"east"}
        for key in ("Facing","facing"):
            if key in tag and isinstance(tag[key], (nl.Byte,nl.Short,nl.Int)) and int(tag[key]) in ids:
                reverse={v:k for k,v in ids.items()}
                tag[key]=type(tag[key])(reverse[direction(ids[int(tag[key])],turns,mirror)])
        nbt=tag.snbt()
    return BlockRecord(block.block_id,tuple(sorted(output.items())),nbt)

def transform_region(grid, minimum, maximum, pivot=(0,0,0), turns=0, mirror=None, offset=(0,0,0), move=False, copies=1):
    lo,hi,pivot,offset=map(position,(minimum,maximum,pivot,offset))
    if any(a>b for a,b in zip(lo,hi)) or not 1<=copies<=1000:
        raise ValueError("Invalid transform bounds or copy count")
    rows=[(p,b) for p,b in grid.blocks.items() if all(a<=v<=z for a,v,z in zip(lo,p,hi))]
    if len(rows)*copies>1_000_000: raise ValueError("Transform exceeds transaction limit")
    changes=dict((p,None) for p,b in rows) if move else {}
    for index in range(1,copies+1):
        translation=tuple(v*index for v in offset)
        for p,b in rows:
            target=coordinate(p,pivot,turns,mirror,translation)
            changes[target]=state(b,turns,mirror,target)
    return changes.items()

def transform_metadata(grid,minimum,maximum,pivot=(0,0,0),turns=0,mirror=None,offset=(0,0,0),move=False,copies=1):
    """Transform region-local entity coordinates and fully selected named components."""
    from itertools import product
    from .formats import dependencies
    nl,_=dependencies();metadata=grid.metadata()
    inside=lambda p:all(a<=v<b+1 for a,v,b in zip(minimum,p,maximum))
    for index,region in enumerate(grid.regions):
        entities=[]
        for snbt in region.entities:
            tag=nl.parse_nbt(snbt)
            world=tuple(float(tag['Pos'][i])+region.origin[i] for i in range(3))
            selected=inside(world)
            if not selected or not move:entities.append(snbt)
            if not selected:continue
            for count in range(1,copies+1):
                out=nl.parse_nbt(snbt);delta=tuple(v*count for v in offset)
                destination=coordinate(tuple(v-.5 for v in world),pivot,turns,mirror,delta)
                out['Pos']=nl.List[nl.Double]([destination[i]+.5-region.origin[i] for i in range(3)])
                if 'Rotation' in out:
                    yaw=float(out['Rotation'][0])
                    if mirror=='x':yaw=-yaw
                    if mirror=='z':yaw=180-yaw
                    out['Rotation'][0]=nl.Float((yaw+turns*90)%360)
                if 'Motion' in out:out['Motion']=nl.List[nl.Double](coordinate(tuple(float(v) for v in out['Motion']),turns=turns,mirror=mirror))
                if all('Tile'+a in out for a in 'XYZ'):
                    anchor=tuple(int(out['Tile'+a])+region.origin[i] for i,a in enumerate('XYZ'))
                    transformed=coordinate(anchor,pivot,turns,mirror,delta)
                    for i,a in enumerate('XYZ'):out['Tile'+a]=nl.Int(transformed[i]-region.origin[i])
                entities.append(out.snbt())
        metadata['regions'][index]['entities']=entities
    for name,component in grid.components.items():
        lo,hi=component['bounds']
        if not inside(lo) or not inside(hi):continue
        if move:metadata['components'].pop(name,None)
        for count in range(1,copies+1):
            corners=[coordinate(p,pivot,turns,mirror,tuple(v*count for v in offset)) for p in product(*zip(lo,hi))]
            bounds=[tuple(min(p[i] for p in corners) for i in range(3)),tuple(max(p[i] for p in corners) for i in range(3))]
            key=name if move and count==1 else name+' copy '+str(count)
            while key in metadata['components']:key+=' copy'
            metadata['components'][key]={**component,'bounds':bounds}
    return metadata
