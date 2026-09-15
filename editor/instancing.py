"""Geometry Nodes backend: one point per visible block, shared local mesh prototypes.

Input is the same culled/CTM-resolved chunk surface used by the mesh backend.
Only identical surfaces, UVs, materials and colors share a prototype.
"""
import hashlib
from itertools import groupby
from .grid import mc_to_blender

def build(name,vertices,uvs,mats,positions,colors,materials,surface_keys,library,prebuilt=()):
    import bpy
    if not hasattr(library,'prototype_cache'):library.prototype_cache={}
    cache=library.prototype_cache
    prototypes=[proto for p,proto in prebuilt];points=[(p,mc_to_blender(p)) for p,proto in prebuilt]
    for p,group in groupby(enumerate(positions),key=lambda pair:pair[1]):
        indices=[i for i,_ in group];origin=mc_to_blender(p)
        key=surface_keys[p]
        proto=bpy.data.objects.get(cache.get(key,''))
        if proto is not None:
            prototypes.append(proto);points.append((p,origin));continue
        local=[tuple(round(vertices[i*4+j][axis]-origin[axis],6)+0.0 for axis in range(3)) for i in indices for j in range(4)]
        uv=[tuple(round(v,8) for v in uvs[i*4+j]) for i in indices for j in range(4)]
        rgba=[colors[i*4+j] for i in indices for j in range(4)]
        material_names=[materials[mats[i]].name for i in indices]
        digest=hashlib.sha256(repr((local,uv,rgba,material_names)).encode()).hexdigest()
        # Blender sorts collection children naturally; an alphabet-only digest
        # makes this ordering identical to Python's lexical sort.
        proto_name='M2B Prototype '+digest.translate(str.maketrans('0123456789','ghijklmnop'))
        proto=bpy.data.objects.get(proto_name)
        if proto is None:
            mesh=bpy.data.meshes.new(proto_name)
            mesh.from_pydata(local,[],[tuple(range(i,i+4)) for i in range(0,len(local),4)])
            names=list(dict.fromkeys(material_names))
            for material_name in names:mesh.materials.append(bpy.data.materials[material_name])
            mesh.polygons.foreach_set('material_index',[names.index(n) for n in material_names])
            layer=mesh.uv_layers.new(name='UVMap');layer.data.foreach_set('uv',[v for pair in uv for v in pair])
            layer=mesh.color_attributes.new(name='mc_tint',type='FLOAT_COLOR',domain='CORNER');layer.data.foreach_set('color_srgb',[v for c in rgba for v in c])
            mesh.update();proto=bpy.data.objects.new(proto_name,mesh);proto['m2b_prototype']=True
        cache[key]=proto.name
        if len(cache)>65536:cache.pop(next(iter(cache)))
        prototypes.append(proto);points.append((p,origin))
    source_name=name+' / Instance Sources'
    sources=bpy.data.collections.get(source_name) or bpy.data.collections.new(source_name)
    for obj in list(sources.objects):sources.objects.unlink(obj)
    # Collection Info enumerates separate children in name order.
    unique=sorted(set(prototypes),key=lambda obj:obj.name)
    for obj in unique:sources.objects.link(obj)
    lookup={obj.name:i for i,obj in enumerate(unique)}
    mesh=bpy.data.meshes.new(name+' / Points');mesh.from_pydata([origin for p,origin in points],[],[])
    attr=mesh.attributes.new('m2b_instance','INT','POINT');attr.data.foreach_set('value',[lookup[obj.name] for obj in prototypes])
    for axis,key in enumerate('xyz'):
        attr=mesh.attributes.new('mc_'+key,'INT','POINT');attr.data.foreach_set('value',[p[axis] for p,origin in points])
    return mesh,sources

def attach(obj,sources):
    import bpy
    name='M2B Shared Instancing'
    group=bpy.data.node_groups.get(name)
    if group is None:
        group=bpy.data.node_groups.new(name,'GeometryNodeTree')
        group.interface.new_socket(name='Geometry',in_out='INPUT',socket_type='NodeSocketGeometry')
        group.interface.new_socket(name='Geometry',in_out='OUTPUT',socket_type='NodeSocketGeometry')
        group.interface.new_socket(name='Sources',in_out='INPUT',socket_type='NodeSocketCollection')
        nodes=group.nodes;links=group.links
        inp=nodes.new('NodeGroupInput');out=nodes.new('NodeGroupOutput')
        info=nodes.new('GeometryNodeCollectionInfo');links.new(inp.outputs['Sources'],info.inputs['Collection'])
        info.inputs['Separate Children'].default_value=True;info.inputs['Reset Children'].default_value=True
        index=nodes.new('GeometryNodeInputNamedAttribute');index.data_type='INT';index.inputs['Name'].default_value='m2b_instance'
        instance=nodes.new('GeometryNodeInstanceOnPoints');instance.inputs['Pick Instance'].default_value=True
        links.new(inp.outputs['Geometry'],instance.inputs['Points']);links.new(info.outputs['Instances'],instance.inputs['Instance']);links.new(index.outputs['Attribute'],instance.inputs['Instance Index']);links.new(instance.outputs['Instances'],out.inputs['Geometry'])
    modifier=obj.modifiers.get('M2B Instances') or obj.modifiers.new('M2B Instances','NODES')
    previous=modifier.node_group;modifier.node_group=group
    socket=next(s for s in group.interface.items_tree if s.name=='Sources' and s.in_out=='INPUT')
    if getattr(modifier,'properties',None) is not None:
        getattr(modifier.properties.inputs,socket.identifier).value=sources
    else:modifier[socket.identifier]=sources
    if previous and previous!=group and not previous.users:bpy.data.node_groups.remove(previous)

def detach(obj):
    import bpy
    if 'M2B Instances' in obj.modifiers:
        modifier=obj.modifiers['M2B Instances'];group=modifier.node_group
        if group and group.name=='M2B Shared Instancing':
            socket=next(s for s in group.interface.items_tree if s.name=='Sources' and s.in_out=='INPUT')
            if getattr(modifier,'properties',None) is not None:getattr(modifier.properties.inputs,socket.identifier).value=None
            else:modifier[socket.identifier]=None
        obj.modifiers.remove(obj.modifiers['M2B Instances'])
        if group and not group.users:bpy.data.node_groups.remove(group)
    collection=bpy.data.collections.get(obj.name+' / Instance Sources')
    if collection and not collection.users:bpy.data.collections.remove(collection)

def prune():
    import bpy
    for obj in list(bpy.data.objects):
        if obj.get('m2b_prototype') and not obj.users:
            mesh=obj.data;bpy.data.objects.remove(obj)
            if not mesh.users:bpy.data.meshes.remove(mesh)
