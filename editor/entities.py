"""Region entity previews, merged per chunk; unknown models use explicit markers."""
from pathlib import Path
import json,math
from .grid import mc_to_blender
CACHE={}

def rebuild(grid,library,collection):
    import bpy
    from .render import face_vertices,rotate,visible,asset_json
    signature=repr(([r.__dict__ for r in grid.regions],grid.view,tuple(grid.resource_packs)))
    key=(collection.as_pointer(),grid.id)
    if CACHE.get(key)==signature:return
    path=library.assets/'entity-models.json'
    if not hasattr(library,'entities'):
        data=asset_json(path) if path.exists() else {}
        library.entities=data.get('models',{});library.entity_variants=data.get('variants',{})
    prefix='M2B Entities '+grid.id+' / '
    chunks={};missing=set()
    for region in grid.regions:
        for text in region.entities:
            import nbtlib
            tag=nbtlib.parse_nbt(text);p=tuple(float(tag['Pos'][i])+region.origin[i] for i in range(3))
            if not visible(grid,tuple(math.floor(v) for v in p)):continue
            name=str(tag.get('id','minecraft:unknown'));quads=library.entities.get(name)
            variants=library.entity_variants.get(name,{})
            variant=str(tag.get('variant',tag.get('weather_state',''))).removeprefix('minecraft:')
            if variant in variants:quads=variants[variant]
            if int(tag.get('Age',tag.get('age',0)))<0 or bool(tag.get('IsBaby',tag.get('is_baby',False))):quads=variants.get('baby',quads)
            if quads is None:
                missing.add(name)
                quads=[(v,[(0,16),(16,16),(16,0),(0,0)],'',None,(1,.6,.05),False) for v in face_vertices((-.3,0,-.3),(.3,1.8,.3)).values()]
            yaw=float(tag.get('Rotation',[0,0])[0]);chunk=tuple(math.floor(v/16) for v in p)
            chunks.setdefault(chunk,[]).append((p,yaw,quads))
    used=set();atlas=bpy.data.images.load(str(library.assets/'atlas.png'),check_existing=True)
    material=bpy.data.materials.get('M2B Atlas Tint '+library.resource_version)
    marker=bpy.data.materials.get('M2B Entity Marker') or bpy.data.materials.new('M2B Entity Marker');marker.diffuse_color=(1,.6,.05,1)
    materials=[material,marker];overrides={}
    def texture_material(path):
        if path in overrides:return overrides[path]
        from .materials import shader
        image=bpy.data.images.load(path,check_existing=True)
        if not image.packed_file:image.pack()
        name='M2B Pack Tint '+Path(path).stem
        mat=bpy.data.materials.get(name)
        if mat is None:mat=bpy.data.materials.new(name);shader(mat,image)
        overrides[path]=len(materials);materials.append(mat);return overrides[path]
    for chunk,items in chunks.items():
        name=prefix+','.join(map(str,chunk));used.add(name)
        vertices=[];faces=[];uvs=[];colors=[];mats=[]
        for p,yaw,quads in items:
            for quad,uv,texture,cull,tint,translucent in quads:
                start=len(vertices)
                vertices.extend(mc_to_blender(tuple(v[i]+p[i] for i in range(3))) for v in (rotate(v,'y',-yaw,(0,0,0)) for v in quad))
                faces.append(tuple(range(start,start+4)));tile=library.uv.get(texture)
                override=library.texture_overrides.get(texture)
                if override:
                    uvs.extend((u/16,1-v/16) for u,v in uv);material_index=texture_material(override)
                elif tile:
                    x,y,w,h=tile;uvs.extend(((x+u*w/16)/atlas.size[0],1-(y+v*h/16)/atlas.size[1]) for u,v in uv)
                    material_index=0
                else:uvs.extend([(0,0)]*4);material_index=1
                mats.append(material_index);colors.extend([(*tint,.3 if grid.view.get('xray') else 1)]*4)
        mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces)
        for mat in materials:mesh.materials.append(mat)
        mesh.polygons.foreach_set('material_index',mats)
        layer=mesh.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',[v for pair in uvs for v in pair])
        layer=mesh.color_attributes.new(name='mc_tint',type='FLOAT_COLOR',domain='CORNER');layer.data.foreach_set('color_srgb',[v for c in colors for v in c])
        obj=bpy.data.objects.get(name)
        if obj:
            old=obj.data;obj.data=mesh
            if not old.users:bpy.data.meshes.remove(old)
        else:obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
        obj['m2b_entity_preview']=True;obj['m2b_derived']=True
    for obj in list(collection.objects):
        if obj.name.startswith(prefix) and obj.name not in used:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
            if not mesh.users:bpy.data.meshes.remove(mesh)
    CACHE[key]=signature
    return {'entity_placeholders':sorted(missing),'entity_chunks':len(chunks)}
