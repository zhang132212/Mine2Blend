from pathlib import Path
import sys
import json
import time
import bpy
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from editor.grid import BlockGrid, BlockRecord
from editor.render import ModelLibrary, rebuild

results=[]
for hi in ((99,9,99),(99,49,99)):
    g=BlockGrid("Solid benchmark")
    t=time.perf_counter()
    g.fill((0,0,0),hi,BlockRecord.parse("minecraft:stone"))
    fill=time.perf_counter()-t
    t=time.perf_counter()
    stats=rebuild(g,ModelLibrary())
    render=time.perf_counter()-t
    objects=[o for o in bpy.data.objects if o.get("m2b_grid_id")==g.id]
    t=time.perf_counter()
    g.apply([((15,5,15),None)],g.revision)
    rebuild(g,ModelLibrary())
    edit=time.perf_counter()-t
    results.append({"blocks":(hi[0]+1)*(hi[1]+1)*(hi[2]+1),"fill_seconds":fill,"mesh_seconds":render,
                    "single_edit_seconds":edit,"chunk_objects":len(objects),"faces":sum(len(o.data.polygons) for o in objects),
                    "fixture":"solid stone volume; not representative of complex transparent/model-heavy buildings"})
    for o in objects:
        mesh=o.data
        bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.meshes.remove(mesh)
(ROOT/'test-output/benchmark.json').write_text(json.dumps(results,indent=2))
print('BENCHMARK_OK',json.dumps(results))
