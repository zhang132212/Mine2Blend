"""Exact union coverage for axis-aligned model boundary rectangles."""
from functools import lru_cache

AXIS={'west':0,'east':0,'down':1,'up':1,'north':2,'south':2}
OPPOSITE={'west':'east','east':'west','up':'down','down':'up','north':'south','south':'north'}

def rectangle(vertices,face,boundary=True):
    axis=AXIS[face];plane=1 if face in ('east','up','south') else 0
    if boundary and any(abs(v[axis]-plane)>1e-6 for v in vertices):return None
    axes=[i for i in range(3) if i!=axis]
    points=[tuple(round(v[i],6) for i in axes) for v in vertices]
    lo=tuple(min(p[i] for p in points) for i in range(2));hi=tuple(max(p[i] for p in points) for i in range(2))
    if len(set(points))!=4 or set(points)!={(x,y) for x in (lo[0],hi[0]) for y in (lo[1],hi[1])}:return None
    return (*lo,*hi)

@lru_cache(maxsize=32768)
def covered(target,rectangles):
    x0,y0,x1,y1=target
    clipped=[(max(x0,a),max(y0,b),min(x1,c),min(y1,d)) for a,b,c,d in rectangles if a<x1 and c>x0 and b<y1 and d>y0]
    if not clipped:return False
    xs=sorted({x0,x1,*[v for r in clipped for v in (r[0],r[2])]})
    for a,b in zip(xs,xs[1:]):
        cursor=y0
        for low,high in sorted((r[1],r[3]) for r in clipped if r[0]<=a and r[2]>=b):
            if low>cursor+1e-6:return False
            cursor=max(cursor,high)
        if cursor<y1-1e-6:return False
    return True
