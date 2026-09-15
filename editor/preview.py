"""Render a grid in an isolated temporary scene, preserving the working camera."""
from pathlib import Path
import math
from itertools import product
from .grid import mc_to_blender

def render(grid,path,size=1024):
    import bpy
    from mathutils import Vector
    size=max(128,min(int(size),4096))
    collection=bpy.data.collections.get('M2B Grid '+grid.id)
    if collection is None:raise ValueError('Build preview mesh first')
    bpy.context.view_layer.update()
    corners=[]
    if grid.bounds:
        lo,hi=grid.bounds
        corners.extend(Vector(mc_to_blender(p)) for p in product(*(tuple((lo[i],hi[i]+1)) for i in range(3))))
    for obj in collection.objects:
        if obj.type=='MESH':corners.extend(obj.matrix_world@Vector(p) for p in obj.bound_box)
    if not corners:raise ValueError('Grid has no visible geometry')
    path=Path(path).resolve();path.parent.mkdir(parents=True,exist_ok=True)
    scene=bpy.data.scenes.new('M2B Temporary Preview')
    created=[]
    world=None
    try:
        scene.collection.children.link(collection)
        lo=tuple(min(p[i] for p in corners) for i in range(3));hi=tuple(max(p[i] for p in corners) for i in range(3))
        center=Vector(tuple((a+b)/2 for a,b in zip(lo,hi)))
        radius=max(b-a for a,b in zip(lo,hi))
        data=bpy.data.cameras.new('M2B Preview Camera');camera=bpy.data.objects.new(data.name,data);created.append(camera);scene.collection.objects.link(camera)
        camera.location=center+Vector((1.3,1.6,1.15))*max(radius,3)
        camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        data.type='ORTHO';data.ortho_scale=max(4,radius*1.8);scene.camera=camera
        data=bpy.data.lights.new('M2B Preview Sun','SUN');light=bpy.data.objects.new(data.name,data);created.append(light);scene.collection.objects.link(light)
        light.rotation_euler=(math.radians(30),math.radians(-20),math.radians(20));data.energy=2
        world=bpy.data.worlds.new('M2B Preview World');scene.world=world;world.use_nodes=True
        world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.5,0.55,0.65,1)
        world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.7
        scene.render.engine='CYCLES';scene.cycles.samples=16
        scene.render.resolution_x=size;scene.render.resolution_y=size;scene.render.resolution_percentage=100
        scene.render.image_settings.file_format='PNG';scene.render.filepath=str(path)
        bpy.ops.render.render(write_still=True,scene=scene.name)
        return {'path':str(path),'revision':grid.revision,'width':size,'height':size}
    finally:
        bpy.data.scenes.remove(scene)
        for obj in created:
            data=obj.data;kind=obj.type;bpy.data.objects.remove(obj,do_unlink=True)
            if kind=='CAMERA':bpy.data.cameras.remove(data)
            else:bpy.data.lights.remove(data)
        if world and not world.users:bpy.data.worlds.remove(world)
