"""Verify GN prototype selection, surface equivalence and persistence."""
from pathlib import Path
import sys,json
import bpy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from editor.grid import BlockGrid
from editor.registry import Registry
from editor.render import ModelLibrary,rebuild
r=Registry();lib=ModelLibrary();g=BlockGrid('Instance QA')
states=['minecraft:stone','minecraft:oak_stairs[facing=east]','minecraft:chest','minecraft:glass','minecraft:oak_fence']
for x in range(20):
    for z in range(10):g._set((x*2,0,z*2),r.resolve(states[x%len(states)]))
rebuild(g,lib)
def objects():return [o for o in bpy.data.objects if o.get('m2b_grid_id')==g.id]
reference={o.name:sorted(tuple(round(v,5) for v in vertex.co) for vertex in o.data.vertices) for o in objects()}
faces=sum(len(o.data.polygons) for o in objects())
g.view['renderer']='instances';g.dirty.update(g.chunks);rebuild(g,lib)
assert sum(len(o.data.vertices) for o in objects())==len(g.blocks)
prototype_count=len([o for o in bpy.data.objects if o.get('m2b_prototype')])
assert prototype_count<=20,prototype_count
for obj in objects():
    tree=obj.modifiers['M2B Instances'].node_group
    out=next(n for n in tree.nodes if n.type=='GROUP_OUTPUT');instance=next(n for n in tree.nodes if n.bl_idname=='GeometryNodeInstanceOnPoints')
    realize=tree.nodes.new('GeometryNodeRealizeInstances');tree.links.new(instance.outputs['Instances'],realize.inputs['Geometry']);tree.links.new(realize.outputs['Geometry'],out.inputs['Geometry'])
    bpy.context.view_layer.update();evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=evaluated.to_mesh()
    actual=sorted(tuple(round(v,5) for v in vertex.co) for vertex in mesh.vertices)
    if actual!=reference[obj.name]:
        info=next(n for n in tree.nodes if n.bl_idname=='GeometryNodeCollectionInfo')
        print('SOURCES',[(i,p.name,len(p.data.vertices)) for i,p in enumerate(info.inputs['Collection'].default_value.objects)])
        print('POINTS',[(tuple(v.co),obj.data.attributes['m2b_instance'].data[i].value) for i,v in enumerate(obj.data.vertices)][-20:])
    assert actual==reference[obj.name],(obj.name,len(actual),len(reference[obj.name]),next(((a,b) for a,b in zip(actual,reference[obj.name]) if a!=b),None))
    evaluated.to_mesh_clear();tree.links.new(instance.outputs['Instances'],out.inputs['Geometry']);tree.nodes.remove(realize)
out=ROOT/'test-output';out.mkdir(exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'instances.blend'))
bpy.ops.wm.open_mainfile(filepath=str(out/'instances.blend'))
assert all(o.modifiers.get('M2B Instances') for o in objects())
g.view['renderer']='mesh';g.dirty.update(g.chunks);rebuild(g,lib)
assert not any(o.get('m2b_prototype') for o in bpy.data.objects)
print('BLENDER_INSTANCES_OK',json.dumps({'blocks':len(g.blocks),'prototypes':prototype_count,'chunks':len(objects()),'faces':faces}))
