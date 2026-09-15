"""Static edit-time connectivity; no redstone power or game tick simulation."""
from collections import deque
from .grid import BlockRecord, DIRECTIONS
from .transforms import HORIZONTAL

def add(p,d): return tuple(p[i]+d[i] for i in range(3))
def opposite(d): return {"north":"south","south":"north","east":"west","west":"east","up":"down","down":"up"}[d]
def left(d): return HORIZONTAL[(HORIZONTAL.index(d)-1)%4]
def right(d): return HORIZONTAL[(HORIZONTAL.index(d)+1)%4]
def axis(d): return "x" if d in ("east","west") else "z"
def family(b):
    if not b: return "air"
    n=b.block_id
    if n.endswith("_fence_gate"): return "gate"
    if n.endswith("_fence"): return "fence"
    if n.endswith("_wall"): return "wall"
    if n.endswith("_pane") or n=="minecraft:iron_bars": return "pane"
    if n.endswith("_stairs"): return "stairs"
    if n.endswith("rail"): return "rail"
    if n=="minecraft:redstone_wire": return "wire"
    return "other"

def solid(block):
    if not block: return False
    n=block.block_id
    return n in {"minecraft:stone","minecraft:cobblestone","minecraft:dirt","minecraft:bedrock","minecraft:bricks","minecraft:deepslate","minecraft:glass"} or n.endswith(("_planks","_concrete","_log","_wood","_bricks","_terracotta"))

def derive(p,block,get,is_solid=solid):
    props=dict(block.properties)
    kind=family(block)
    def at(d): return get(add(p,DIRECTIONS[d]))
    if kind in ("fence","pane","wall"):
        for d in HORIZONTAL:
            neighbor=at(d); nk=family(neighbor)
            connect=is_solid(neighbor) or nk==kind
            if kind=="fence" and nk=="fence":
                connect=(block.block_id=="minecraft:nether_brick_fence")==(neighbor.block_id=="minecraft:nether_brick_fence")
            if nk=="gate" and kind in ("fence","wall"):
                connect=axis(dict(neighbor.properties).get("facing","north"))!=axis(d)
            props[d]=("low" if connect else "none") if kind=="wall" else str(connect).lower()
        if kind=="wall":
            above=at("up")
            if is_solid(above):
                for d in HORIZONTAL:
                    if props[d]!="none": props[d]="tall"
            ns=props["north"]!="none" and props["south"]!="none"
            ew=props["east"]!="none" and props["west"]!="none"
            count=sum(props[d]!="none" for d in HORIZONTAL)
            props["up"]=str(not ((ns or ew) and count==2) or family(above)=="wall" and dict(above.properties).get("up")=="true").lower()
    elif kind=="gate":
        facing=props["facing"]
        props["in_wall"]=str(any(family(at(d))=="wall" for d in (left(facing),right(facing)))).lower()
    elif kind=="stairs":
        facing=props["facing"];half=props["half"]
        def stair(b): return family(b)=="stairs" and dict(b.properties).get("half")==half
        def different(d):
            other=at(d)
            return not stair(other) or dict(other.properties).get("facing")!=facing
        props["shape"]="straight"
        front=at(facing)
        if stair(front):
            f=dict(front.properties)["facing"]
            if axis(f)!=axis(facing) and different(opposite(f)):
                props["shape"]="outer_left" if f==left(facing) else "outer_right"
        if props["shape"]=="straight":
            back=at(opposite(facing))
            if stair(back):
                f=dict(back.properties)["facing"]
                if axis(f)!=axis(facing) and different(f):
                    props["shape"]="inner_left" if f==left(facing) else "inner_right"
    elif kind=="rail":
        neighbors={}
        for d in HORIZONTAL:
            target=add(p,DIRECTIONS[d])
            heights=[dy for dy in (0,1,-1) if family(get(add(target,(0,dy,0))))=="rail"]
            if heights: neighbors[d]=heights[0]
        ns=any(d in neighbors for d in ("north","south"));ew=any(d in neighbors for d in ("east","west"))
        shape="east_west" if ew and not ns else "north_south"
        if block.block_id=="minecraft:rail" and len(neighbors)==2 and ns and ew:
            from .transforms import RAILS
            shape=RAILS[frozenset(neighbors)]
        elif ns and ew:
            shape=props.get("shape","north_south")
            if shape not in ("north_south","east_west"): shape="north_south"
        for d in HORIZONTAL:
            if neighbors.get(d)==1 and ((shape=="north_south" and axis(d)=="z") or (shape=="east_west" and axis(d)=="x")):
                shape="ascending_"+d
        props["shape"]=shape
    elif kind=="wire":
        above_solid=is_solid(at("up"))
        for d in HORIZONTAL:
            target=add(p,DIRECTIONS[d]);neighbor=get(target)
            nk=family(neighbor);np=dict(neighbor.properties) if neighbor else {}
            component=neighbor and (neighbor.block_id in ("minecraft:lever","minecraft:redstone_torch","minecraft:redstone_wall_torch","minecraft:redstone_block","minecraft:tripwire_hook","minecraft:daylight_detector","minecraft:target") or neighbor.block_id.endswith(("_button","_pressure_plate")))
            if neighbor and neighbor.block_id in ("minecraft:repeater","minecraft:comparator"):
                component=axis(np.get("facing","north"))==axis(d)
            if neighbor and neighbor.block_id=="minecraft:observer": component=np.get("facing")==d
            value="side" if nk=="wire" or component else "none"
            if is_solid(neighbor) and not above_solid and family(get(add(target,(0,1,0))))=="wire": value="up"
            elif not is_solid(neighbor) and family(get(add(target,(0,-1,0))))=="wire": value="side"
            props[d]=value
        connected=[d for d in HORIZONTAL if props[d]!="none"]
        if len(connected)==1: props[opposite(connected[0])]="side"
        if not connected:
            for d in HORIZONTAL: props[d]="side"
    return BlockRecord(block.block_id,tuple(sorted(props.items())),block.nbt)

def reconcile(grid,changes,is_solid=solid):
    """Compute fixed-point state delta without mutating grid, including diagonal rail steps."""
    staged=dict(changes)
    get=lambda p: staged[p] if p in staged else grid.blocks.get(p)
    pending=set()
    def enqueue(p):
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    q=add(p,(dx,dy,dz))
                    if family(get(q)) in ("fence","pane","wall","gate","stairs","rail","wire"): pending.add(q)
    candidates={p for p,b in staged.items() if family(b) in ("fence","pane","wall","gate","stairs","rail","wire")}
    for p,b in grid.blocks.items():
        if family(b) in ("fence","pane","wall","gate","stairs","rail","wire") and any(add(p,(dx,dy,dz)) in staged for dx in (-1,0,1) for dy in (-1,0,1) for dz in (-1,0,1)):
            candidates.add(p)
    pending.update(candidates)
    steps=0
    while pending:
        p=pending.pop();block=get(p)
        if not block: continue
        new=derive(p,block,get,is_solid)
        if new!=block:
            staged[p]=new;enqueue(p)
        steps+=1
        if steps>max(10000,len(staged)*100): raise ValueError("Neighbor rules did not converge; transaction cancelled")
    return staged.items()

def placement(registry,state,p,clicked_face="up",look="north",hit_y=0.5,hit_x=0.5,hit_z=0.5):
    block=registry.resolve(state);props=dict(block.properties)
    if look not in HORIZONTAL or clicked_face not in DIRECTIONS: raise ValueError("Invalid placement direction")
    if "facing" in props:
        props["facing"]=look if family(block)=="stairs" or block.block_id.endswith(("_door","_fence_gate")) else opposite(look)
        allowed=registry.blocks[block.block_id.removeprefix("minecraft:")][0]["facing"]
        if clicked_face in ("up","down") and clicked_face in allowed and not block.block_id.endswith(("_piston","piston")):
            props["facing"]=clicked_face
    if "axis" in props: props["axis"]="y" if clicked_face in ("up","down") else axis(clicked_face)
    if family(block)=="stairs" or block.block_id.endswith("_trapdoor"):
        props["half"]="top" if clicked_face=="down" or clicked_face not in ("up","down") and hit_y>0.5 else "bottom"
        if block.block_id.endswith('_trapdoor') and clicked_face in HORIZONTAL:props['facing']=clicked_face
    if block.block_id.endswith("_slab"):
        props["type"]="top" if clicked_face=="down" or clicked_face not in ("up","down") and hit_y>0.5 else "bottom"
    if "face" in props: props["face"]={"up":"floor","down":"ceiling"}.get(clicked_face,"wall")
    if "face" in props and clicked_face in HORIZONTAL:props['facing']=clicked_face
    if "rotation" in props: props["rotation"]=str({"south":0,"west":4,"north":8,"east":12}[opposite(look)])
    return BlockRecord(block.block_id,tuple(sorted(props.items())),block.nbt)
