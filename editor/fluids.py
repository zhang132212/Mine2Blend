"""Static fluid surface preview from levels and adjacent fluid columns."""
from .grid import DIRECTIONS

def kind(block):
    if not block:return None
    if block.block_id in ('minecraft:water','minecraft:bubble_column') or dict(block.properties).get('waterlogged')=='true':return 'water'
    if block.block_id=='minecraft:lava':return 'lava'
    return None

def quads(block,p,get,solid):
    from .render import face_vertices
    fluid=kind(block)
    if not fluid:return []
    def at(dx,dy,dz):return get((p[0]+dx,p[1]+dy,p[2]+dz))
    def height(dx,dz):
        b=at(dx,0,dz)
        if kind(b)!=fluid:return -1 if solid(b) else 0
        if kind(at(dx,1,dz))==fluid:return 1
        level=int(dict(b.properties).get('level',0))
        return (8-(level if level<8 else 0))/9
    def corner(x,z):
        values=[height(dx,dz) for dx in (x-1,x) for dz in (z-1,z)]
        if 1 in values:return 1
        values=[v for v in values if v>=0]
        return sum(v*(10 if v>=.8 else 1) for v in values)/sum(10 if v>=.8 else 1 for v in values)
    heights={(x,z):corner(x,z) for x in (0,1) for z in (0,1)}
    result=[]
    for face,verts in face_vertices((0,0,0),(1,1,1)).items():
        d=DIRECTIONS[face];neighbor=at(*d)
        if kind(neighbor)==fluid:continue
        if solid(neighbor):continue
        verts=[(x,heights[x,z] if y else 0,z) for x,y,z in verts]
        texture='block/'+fluid+('_still' if face in ('up','down') else '_flow')
        result.append((verts,[(0,16),(16,16),(16,0),(0,0)],texture,None,0 if fluid=='water' else -1,fluid=='water'))
    return result
