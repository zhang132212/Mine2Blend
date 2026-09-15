"""Chunk meshes derived from BlockGrid. Legacy atlas is an explicitly labelled fallback."""
from pathlib import Path
import json
import math
from functools import lru_cache
from .grid import DIRECTIONS, mc_to_blender
from .registry import matches
from .ctm import CTM

LEGACY_ASSETS = Path(__file__).resolve().parent.parent / "resources/converter/win-x64/assets/mcmeta"
CURRENT_ASSETS = Path(__file__).resolve().parent / "data/resources"
ASSETS = CURRENT_ASSETS if (CURRENT_ASSETS / "resource-info.json").exists() else LEGACY_ASSETS

def rotate(p, axis, angle, origin=(0.5, 0.5, 0.5)):
    a = math.radians(angle)
    c, s = math.cos(a), math.sin(a)
    q = [p[i] - origin[i] for i in range(3)]
    i, j = {"x": (1, 2), "y": (2, 0), "z": (0, 1)}[axis]
    q[i], q[j] = c*q[i]-s*q[j], s*q[i]+c*q[j]
    return tuple(q[i] + origin[i] for i in range(3))

def face_vertices(lo, hi):
    x, y, z = lo
    X, Y, Z = hi
    return {
        "north": [(X,y,z),(x,y,z),(x,Y,z),(X,Y,z)],
        "south": [(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],
        "east": [(X,y,Z),(X,y,z),(X,Y,z),(X,Y,Z)],
        "west": [(x,y,z),(x,y,Z),(x,Y,Z),(x,Y,z)],
        "up": [(x,Y,Z),(X,Y,Z),(X,Y,z),(x,Y,z)],
        "down": [(x,y,z),(X,y,z),(X,y,Z),(x,y,Z)],
    }

def quad_face(quad):
    a=[quad[1][i]-quad[0][i] for i in range(3)]
    b=[quad[2][i]-quad[0][i] for i in range(3)]
    n=(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
    axis=max(range(3),key=lambda i:abs(n[i]))
    if abs(n[axis])<1e-8 or any(abs(n[i])>1e-6 for i in range(3) if i!=axis):return None
    return (("west","east"),("down","up"),("north","south"))[axis][n[axis]>0]

def visible(grid,p):
    v=grid.view
    if p[1] in v['hidden_layers']:return False
    if v['slice_min'] is not None and p[1]<v['slice_min']:return False
    if v['slice_max'] is not None and p[1]>v['slice_max']:return False
    if v['isolate']:
        bounds=v['isolate']
        if any(not a<=x<=b for a,x,b in zip(bounds[0],p,bounds[1])):return False
    return True

class ModelLibrary:
    def __init__(self):
        self.assets = ASSETS
        self.resource_version = json.loads((ASSETS / "resource-info.json").read_text())["version"] if (ASSETS / "resource-info.json").exists() else "legacy 2026-02-26"
        self.models = json.loads((ASSETS / "block-models.json").read_text())
        special_path=ASSETS/'special-models.json'
        self.special=json.loads(special_path.read_text())['models'] if special_path.exists() else {}
        self.definitions = json.loads((ASSETS / "block-definitions.json").read_text())
        self.uv = json.loads((ASSETS / "atlas-uv.json").read_text())
        self.pack = None
        self.missing = set()
        self.texture_overrides = {}
        self.ctm = CTM()
        alpha_path=ASSETS/'texture-alpha.json'
        self.texture_alpha=json.loads(alpha_path.read_text()) if alpha_path.exists() else {}

    def face_texture(self,block,face):
        if not block:return ''
        return next((q[2] for q in self.quads(block.state) if quad_face(q[0])==face),'')

    @lru_cache(maxsize=8192)
    def model(self, name, chain=()):
        name = name.removeprefix("minecraft:")
        if name in chain or len(chain) > 64:
            raise ValueError("Cyclic model parent")
        item = self.models[name]
        parent = self.model(item["parent"], (*chain, name)) if "parent" in item and not item["parent"].startswith("builtin/") else {}
        return {**parent, **item, "textures": {**parent.get("textures", {}), **item.get("textures", {})}}

    @lru_cache(maxsize=8192)
    def quads(self, state):
        from .grid import BlockRecord
        block = BlockRecord.parse(state)
        if block.block_id in ("minecraft:air", "minecraft:cave_air", "minecraft:void_air"):
            return []
        if block.block_id in ('minecraft:water','minecraft:lava','minecraft:bubble_column','minecraft:barrier','minecraft:light','minecraft:structure_void','minecraft:moving_piston'):
            return []
        props = dict(block.properties)
        if '_wall_head' in block.block_id or '_wall_skull' in block.block_id:
            from .grid import BlockRecord
            standing=BlockRecord(block.block_id.replace('_wall_','_'),(('rotation','0'),))
            angle={'north':0,'east':-90,'south':180,'west':90}[props.get('facing','north')]
            return [([rotate((v[0],v[1]+.25,v[2]+.25),'y',angle) for v in q],uv,tex,cull,tint,translucent) for q,uv,tex,cull,tint,translucent in self.quads(standing.state)]
        if block.block_id in ('minecraft:end_portal','minecraft:end_gateway'):
            faces=face_vertices((0,0,0),(1,.75 if block.block_id.endswith('end_portal') else 1,1))
            return [(v,[(0,16),(16,16),(16,0),(0,0)],'entity/end_portal/end_portal',None,-1,False) for f,v in faces.items() if f=='up' or block.block_id.endswith('end_gateway')]
        special=self.special.get(block.block_id.removeprefix('minecraft:'))
        try:
            if self.pack:
                selected = self.pack.select(block)
            else:
                definition = self.definitions[block.block_id.removeprefix("minecraft:")]
                selected = []
                for key, value in definition.get("variants", {}).items():
                    if matches(dict(k.split("=", 1) for k in key.split(",") if k), props):
                        selected.append(value[0] if isinstance(value, list) else value)
                        break
                for part in definition.get("multipart", []):
                    if matches(part.get("when", {}), props):
                        value = part["apply"]
                        selected.append(value[0] if isinstance(value, list) else value)
            out = []
            for selection in selected:
                model = self.pack.model(selection["model"]) if self.pack else self.model(selection["model"])
                for element in model.get("elements", []):
                    lo, hi = ([v / 16 for v in element[k]] for k in ("from", "to"))
                    vertices = face_vertices(lo, hi)
                    for face, data in element.get("faces", {}).items():
                        verts = vertices[face]
                        rotation = element.get("rotation")
                        if rotation:
                            origin = tuple(v / 16 for v in rotation["origin"])
                            verts = [rotate(v, rotation["axis"], rotation["angle"], origin) for v in verts]
                            if rotation.get("rescale"):
                                scale = 1 / math.cos(math.radians(rotation["angle"]))
                                axis = "xyz".index(rotation["axis"])
                                verts = [tuple(v[i] if i == axis else origin[i]+(v[i]-origin[i])*scale for i in range(3)) for v in verts]
                        cull = DIRECTIONS.get(data.get("cullface"))
                        for axis in ("x", "y"):
                            angle = -selection.get(axis, 0)
                            verts = [rotate(v, axis, angle) for v in verts]
                            if cull:
                                cull = tuple(round(v) for v in rotate(cull, axis, angle, (0,0,0)))
                        texture = data.get("texture", "")
                        if isinstance(texture,str) and texture in model.get('textures',{}):texture='#'+texture
                        translucent=False
                        visited = set()
                        while isinstance(texture, dict) or texture.startswith("#"):
                            if isinstance(texture, dict):
                                translucent=translucent or texture.get('force_translucent',False)
                                texture = texture.get("sprite", "")
                                continue
                            if texture in visited:
                                raise ValueError("Cyclic texture reference")
                            visited.add(texture)
                            texture = model.get("textures", {}).get(texture[1:], "")
                        texture = texture.removeprefix("minecraft:")
                        uvs = data.get("uv")
                        if uvs is None:
                            x,y,z = [v*16 for v in lo]; X,Y,Z = [v*16 for v in hi]
                            uvs = {"north": [16-X,16-Y,16-x,16-y], "south": [x,16-Y,X,16-y],
                                   "west": [z,16-Y,Z,16-y], "east": [16-Z,16-Y,16-z,16-y],
                                   "up": [x,z,X,Z], "down": [x,16-Z,X,16-z]}[face]
                        a,b,c,d = uvs
                        uv = [(a,d),(c,d),(c,b),(a,b)]
                        turns = data.get("rotation", 0)//90
                        uv = uv[turns:] + uv[:turns]
                        if selection.get('uvlock'):
                            world_face=quad_face(verts)
                            if world_face:
                                def projection(v):
                                    x,y,z=v
                                    return {'north':(1-x,1-y),'south':(x,1-y),'west':(z,1-y),'east':(1-z,1-y),'up':(x,z),'down':(x,1-z)}[world_face]
                                uv=[tuple(c*16 for c in projection(v)) for v in verts]
                        out.append((verts, uv, texture, cull,data.get('tintindex',-1),translucent))
            if out:
                return out
        except (KeyError, FileNotFoundError):
            pass
        if special:
            key=','.join(k+'='+props.get(k,'') for k in special['keys'])
            if key in special['variants']:return special['variants'][key]
        self.missing.add(block.block_id)
        return [(v, [(0,16),(16,16),(16,0),(0,0)], "", None,-1,False) for v in face_vertices((0,0,0),(1,1,1)).values()]

    @lru_cache(maxsize=8192)
    def boundary(self,state,face,opaque=True):
        from .occlusion import rectangle
        result=[]
        for quad,uv,texture,cull,tint,translucent in self.quads(state):
            if quad_face(quad)!=face:continue
            if opaque and (translucent or texture in self.texture_overrides or self.texture_alpha.get(texture)!='opaque'):continue
            rect=rectangle(quad,face)
            if rect:result.append(rect)
        return tuple(result)

    @lru_cache(maxsize=8192)
    def full_opaque(self,state):
        from .occlusion import covered
        return all(covered((0,0,1,1),self.boundary(state,face)) for face in DIRECTIONS)

    def opaque_cube(self,block):
        return bool(block and self.full_opaque(block.state))

    def occluded(self,block,neighbor,quad,cull):
        if neighbor is None:return False
        return self.occluded_cached(block.state,neighbor.state,tuple(tuple(v) for v in quad),cull)

    @lru_cache(maxsize=65536)
    def occluded_cached(self,state,neighbor_state,quad,cull):
        from .occlusion import rectangle,covered,OPPOSITE
        from .grid import BlockRecord
        block=BlockRecord.parse(state);neighbor=BlockRecord.parse(neighbor_state)
        face=next((f for f,d in DIRECTIONS.items() if d==cull),None)
        if face is None:return False
        # Cullface may also annotate an inset face: use its projected footprint.
        target=rectangle(quad,face,False)
        if target is None:return False
        same_transparent=block.block_id==neighbor.block_id and ('glass' in block.block_id or block.block_id in ('minecraft:ice','minecraft:slime_block','minecraft:honey_block'))
        return covered(target,self.boundary(neighbor.state,OPPOSITE[face],not same_transparent))

def rebuild(grid, library, max_chunks=None):
    import bpy
    from .materials import shader as make_shader,color as tint_color
    from .fluids import quads as fluid_quads
    name = "M2B Grid " + grid.id
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    atlas = bpy.data.images.load(str(library.assets / "atlas.png"), check_existing=True)
    if not atlas.packed_file:atlas.pack()
    material_name = "M2B Atlas Tint " + library.resource_version
    material = bpy.data.materials.get(material_name)
    if material is None:
        material = bpy.data.materials.new(material_name)
        make_shader(material,atlas)
    missing = bpy.data.materials.get("M2B Missing Preview") or bpy.data.materials.new("M2B Missing Preview")
    missing.diffuse_color = (1, 0, 0.7, 1)
    materials=[material,missing]
    material_indices={}
    def override_material(path):
        if path in material_indices:return material_indices[path]
        image=bpy.data.images.load(path,check_existing=True)
        if not image.packed_file:image.pack()
        key='M2B Pack Tint '+Path(path).stem
        mat=bpy.data.materials.get(key)
        if mat is None:
            mat=bpy.data.materials.new(key);make_shader(mat,image)
        material_indices[path]=len(materials);materials.append(mat)
        return material_indices[path]
    processed=sorted(grid.dirty)
    if max_chunks is not None:processed=processed[:max_chunks]
    for chunk in processed:
        obj_name = name + " / " + ",".join(map(str, chunk))
        existing = bpy.data.objects.get(obj_name)
        vertices, faces, uvs, mats, block_positions = [], [], [], [], []
        colors=[]
        for p in sorted(grid.chunks.get(chunk, ())):
            if not visible(grid,p):continue
            block = grid.blocks[p]
            if library.opaque_cube(block) and all(visible(grid,q) and library.opaque_cube(grid.blocks.get(q)) for q in (tuple(p[i]+d[i] for i in range(3)) for d in DIRECTIONS.values())):
                continue
            expanded=[]
            source=list(library.quads(block.state))
            source.extend(fluid_quads(block,p,lambda q:grid.blocks.get(q) if visible(grid,q) else None,library.opaque_cube))
            for quad,uv,tex,cull,tint,translucent in source:
                face=quad_face(quad)
                if face and library.ctm.rules:
                    tex,overlays=library.ctm.select(p,block,tex,face,grid.blocks.get,library.face_texture,grid.view.get('biome','minecraft:plains'),library.opaque_cube)
                    for index,overlay in enumerate(overlays):
                        delta=DIRECTIONS[face]
                        expanded.append(([tuple(v[i]+delta[i]*0.0002*(index+1) for i in range(3)) for v in quad],uv,overlay,None,tint,True))
                expanded.append((quad,uv,tex,cull,tint,translucent))
            for quad, uv, tex, cull,tint,translucent in expanded:
                neighbor=tuple(p[i]+cull[i] for i in range(3)) if cull else None
                if cull and visible(grid,neighbor) and library.occluded(block,grid.blocks.get(neighbor),quad,cull):
                    continue
                idx = len(vertices)
                vertices.extend(mc_to_blender(tuple(v[i]+p[i] for i in range(3))) for v in quad)
                faces.append((idx, idx+1, idx+2, idx+3))
                tex=tex.removeprefix('minecraft:')
                tile = library.uv.get(tex)
                override=library.texture_overrides.get(tex)
                if override:
                    uvs.extend((u/16,1-v/16) for u,v in uv)
                    material_index=override_material(override)
                elif tile:
                    tx,ty,tw,th = tile
                    uvs.extend(((tx+u*tw/16)/atlas.size[0], 1-(ty+v*th/16)/atlas.size[1]) for u,v in uv)
                    material_index=0
                else:
                    uvs.extend([(0,0)]*4)
                    material_index=1
                mats.append(material_index)
                block_positions.append(p)
                tint_block=block
                if tex.startswith('block/water_'):
                    from .grid import BlockRecord
                    tint_block=BlockRecord('minecraft:water')
                opacity=.3 if grid.view.get('xray') else .7 if tex.startswith('block/water_') else 1
                colors.extend([(*tint_color(tint_block,tint,grid.view.get('biome','minecraft:plains')),opacity)]*4)
        if not faces:
            if existing:
                mesh = existing.data
                bpy.data.objects.remove(existing, do_unlink=True)
                if mesh.users == 0:
                    bpy.data.meshes.remove(mesh)
            continue
        mesh = bpy.data.meshes.new(obj_name)
        mesh.from_pydata(vertices, [], faces)
        for mat in materials:mesh.materials.append(mat)
        mesh.polygons.foreach_set("material_index", mats)
        layer = mesh.uv_layers.new(name="UVMap")
        layer.data.foreach_set("uv", [f for pair in uvs for f in pair])
        color_layer=mesh.color_attributes.new(name='mc_tint',type='FLOAT_COLOR',domain='CORNER')
        color_layer.data.foreach_set('color_srgb',[v for rgba in colors for v in rgba])
        for i, axis in enumerate("xyz"):
            attr = mesh.attributes.new("mc_" + axis, "INT", "FACE")
            attr.data.foreach_set("value", [p[i] for p in block_positions])
        mesh.update()
        if existing:
            old = existing.data
            existing.data = mesh
            if old.users == 0:
                bpy.data.meshes.remove(old)
        else:
            existing = bpy.data.objects.new(obj_name, mesh)
            collection.objects.link(existing)
        existing["m2b_grid_id"] = grid.id
        existing["m2b_derived"] = True
        existing.show_in_front=grid.view.get('xray',False)
    grid.dirty.difference_update(processed)
    return {"objects": len(collection.objects), "missing_models": sorted(library.missing), "preview_resources": library.resource_version,"pending_chunks":len(grid.dirty)}
