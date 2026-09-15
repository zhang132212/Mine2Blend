"""Mixed transparent/model-heavy 100k and 500k GN scenes; outputs measured results."""
from pathlib import Path
import sys,time,json
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from editor.grid import BlockGrid
from editor.registry import Registry
from editor.render import ModelLibrary,rebuild
from editor import instancing
r=Registry();library=ModelLibrary();results=[]
states=[r.resolve('minecraft:'+s) for s in ('stone_bricks','glass','oak_stairs[facing=east]','stone_slab','oak_fence','lantern','chest','red_banner')]
for height in (10,50):
    g=BlockGrid('Mixed benchmark');g.view['renderer']='instances';start=time.perf_counter()
    for x in range(100):
        for y in range(height):
            for z in range(100):g._set((x*2,y*2,z*2),states[(x+y+z)%len(states)])
    fill=time.perf_counter()-start;start=time.perf_counter();iteration=0
    while g.dirty:
        stats=rebuild(g,library,max_chunks=16);iteration+=1
        if iteration%10==0:print('PROGRESS',len(g.blocks),'pending chunks',len(g.dirty),flush=True)
    mesh=time.perf_counter()-start
    objects=[o for o in bpy.data.objects if o.get('m2b_grid_id')==g.id]
    start=time.perf_counter();g.apply([((16,4,16),r.resolve('minecraft:glass'))],g.revision);rebuild(g,library);edit=time.perf_counter()-start
    report={'blocks':len(g.blocks),'fill_seconds':fill,'preview_seconds':mesh,'single_edit_seconds':edit,'chunk_objects':len(objects),'prototype_objects':sum(bool(o.get('m2b_prototype')) for o in bpy.data.objects),'point_vertices':sum(len(o.data.vertices) for o in objects),'fixture':'8 materials: opaque, glass, stairs, slab, fence, lantern, chest, banner; spaced 2 blocks; GN backend'}
    results.append(report);print('COMPLEX_RESULT',json.dumps(report),flush=True)
    for obj in objects:
        instancing.detach(obj);data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if not data.users:bpy.data.meshes.remove(data)
    instancing.prune()
(ROOT/'test-output/complex-benchmark.json').write_text(json.dumps(results,indent=2))
print('COMPLEX_BENCHMARK_OK',flush=True)
