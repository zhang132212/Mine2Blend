from pathlib import Path
import sys,json
import bpy
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from editor.grid import BlockGrid,BlockRecord
from editor.render import ModelLibrary,rebuild
from editor.resource_loader import load
from editor.ctm import INDEX,BASES
from editor.grid import DIRECTIONS
library=ModelLibrary();report=load(library,root/'test-output/ctm-test-pack.zip')
g=BlockGrid('CTM 47 cases');stone=BlockRecord.parse('minecraft:stone')
centers={}
basis=[DIRECTIONS[d] for d in BASES['north']]
for tile in range(47):
    mask=INDEX.index(tile);p=((tile%8)*4,(tile//8)*4,0);centers[p]=tile;g._set(p,stone)
    for i in range(8):
        if mask&(1<<i):
            a=basis[i//2];b=basis[(i//2+1)%4] if i%2 else (0,0,0)
            g._set(tuple(p[k]+a[k]+b[k] for k in range(3)),stone)
stats=rebuild(g,library)
checked=set()
for obj in bpy.data.objects:
    if obj.get('m2b_grid_id')!=g.id:continue
    for f in obj.data.polygons:
        p=tuple(obj.data.attributes['mc_'+k].data[f.index].value for k in 'xyz')
        if p in centers and f.normal.y>0.99:
            tile=centers[p];tex='optifine/ctm/qa/'+str(tile)
            path=library.texture_overrides[tex]
            material=obj.data.materials[f.material_index]
            images=[n.image.filepath for n in material.node_tree.nodes if n.type=='TEX_IMAGE']
            assert path in images,(p,tile,images,path)
            checked.add(tile)
assert len(checked)==47,checked
before=len(g.blocks)
g.view['slice_min']=10;g.dirty.update(g.chunks);rebuild(g,library)
assert len(g.blocks)==before
g.view['slice_min']=None;g.dirty.update(g.chunks);rebuild(g,library)
bpy.ops.wm.save_as_mainfile(filepath=str(root/'test-output/ctm-47.blend'))
(root/'test-output/ctm-qa.json').write_text(json.dumps({'cases':len(checked),'pack':report,'render':stats},indent=2))
print('CTM_47_BLENDER_OK',len(checked))
