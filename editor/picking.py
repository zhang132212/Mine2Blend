"""Grid DDA with model-triangle intersections, independent of Blender object layout."""
import math
from .grid import blender_to_mc,mc_to_blender

def sub(a,b):return tuple(x-y for x,y in zip(a,b))
def dot(a,b):return sum(x*y for x,y in zip(a,b))
def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def triangle(origin,direction,a,b,c):
    e1,e2=sub(b,a),sub(c,a);h=cross(direction,e2);det=dot(e1,h)
    if abs(det)<1e-9:return None
    inv=1/det;s=sub(origin,a);u=inv*dot(s,h)
    if not 0<=u<=1:return None
    q=cross(s,e1);v=inv*dot(direction,q)
    if v<0 or u+v>1:return None
    t=inv*dot(e2,q)
    return (t,cross(e1,e2)) if t>=0 else None

def raycast(grid,library,origin,direction):
    from .render import visible
    from .fluids import quads as fluid_quads
    if not grid.bounds:return None
    lo,hi=grid.bounds;start,end=0,float('inf')
    for i in range(3):
        if abs(direction[i])<1e-12:
            if not lo[i]-1<=origin[i]<=hi[i]+2:return None
        else:
            a,b=sorted(((lo[i]-1-origin[i])/direction[i],(hi[i]+2-origin[i])/direction[i]));start=max(start,a);end=min(end,b)
    if start>end:return None
    cell=[math.floor(origin[i]+direction[i]*(start+1e-7)) for i in range(3)]
    step=[1 if d>0 else -1 for d in direction]
    delta=[abs(1/d) if abs(d)>1e-12 else float('inf') for d in direction]
    next_t=[(cell[i]+(1 if step[i]>0 else 0)-origin[i])/direction[i] if abs(direction[i])>1e-12 else float('inf') for i in range(3)]
    tested=set();best=None
    for _ in range(100000):
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                for dz in (-1,0,1):
                    p=(cell[0]+dx,cell[1]+dy,cell[2]+dz)
                    if p in tested or p not in grid.blocks or not visible(grid,p):continue
                    tested.add(p);block=grid.blocks[p]
                    quads=list(library.quads(block.state))+fluid_quads(block,p,grid.blocks.get,library.opaque_cube)
                    local=sub(origin,p)
                    for quad,*_rest in quads:
                        for ids in ((0,1,2),(0,2,3)):
                            hit=triangle(local,direction,*(quad[i] for i in ids))
                            if hit and (best is None or hit[0]<best['distance']):best={'position':p,'distance':hit[0],'normal':hit[1],'location':tuple(origin[i]+direction[i]*hit[0] for i in range(3))}
        axis=min(range(3),key=lambda i:next_t[i])
        if best and best['distance']<=next_t[axis]+1e-7:return best
        if next_t[axis]>end:break
        cell[axis]+=step[axis];next_t[axis]+=delta[axis]
    return best
