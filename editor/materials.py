"""Shared nearest-pixel atlas/pack shader and per-block tint attributes."""
from pathlib import Path
import json
from functools import lru_cache

@lru_cache(maxsize=1)
def biomes():return json.loads((Path(__file__).parent/'data/biome-colors.json').read_text())['biomes']

def color(block,tint,biome):
    if isinstance(tint,(tuple,list)):return tuple(tint)
    if tint<0:return (1,1,1)
    name=block.block_id.removeprefix('minecraft:');props=dict(block.properties)
    colors=biomes().get(biome,biomes()['minecraft:plains'])
    fixed={'spruce_leaves':(97,153,97),'birch_leaves':(128,167,85),'lily_pad':(32,128,48),'attached_melon_stem':(224,199,28),'attached_pumpkin_stem':(224,199,28)}
    if name in fixed:rgb=fixed[name]
    elif name in ('melon_stem','pumpkin_stem'):
        age=int(props.get('age',0));rgb=(age*32,255-age*8,age*4)
    elif name=='redstone_wire':
        power=int(props.get('power',0))/15
        return (power*.6+(.4 if power>0 else .3),max(0,power*power*.7-.5),max(0,power*power*.6-.7))
    elif name in ('water','water_cauldron','bubble_column'):rgb=colors['water']
    elif 'dry_' in name:rgb=colors['dry_foliage']
    elif name.endswith('_leaves') or name=='vine':rgb=colors['foliage']
    else:rgb=colors['grass']
    return tuple(v/255 for v in rgb)

def shader(mat,image):
    mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bsdf=nodes.get('Principled BSDF')
    tex=nodes.new('ShaderNodeTexImage');tex.image=image;tex.interpolation='Closest'
    tint=nodes.new('ShaderNodeVertexColor');tint.layer_name='mc_tint'
    multiply=nodes.new('ShaderNodeMixRGB');multiply.blend_type='MULTIPLY';multiply.inputs[0].default_value=1
    links.new(tex.outputs['Color'],multiply.inputs[1]);links.new(tint.outputs['Color'],multiply.inputs[2])
    ao=nodes.new('ShaderNodeAmbientOcclusion');ao.inputs['Distance'].default_value=1
    ao_mix=nodes.new('ShaderNodeMixRGB');ao_mix.blend_type='MULTIPLY';ao_mix.inputs[0].default_value=.35
    links.new(multiply.outputs[0],ao_mix.inputs[1]);links.new(ao.outputs['Color'],ao_mix.inputs[2]);links.new(ao_mix.outputs[0],bsdf.inputs['Base Color'])
    alpha=nodes.new('ShaderNodeMath');alpha.operation='MULTIPLY'
    links.new(tex.outputs['Alpha'],alpha.inputs[0]);links.new(tint.outputs['Alpha'],alpha.inputs[1]);links.new(alpha.outputs[0],bsdf.inputs['Alpha'])
    bsdf.inputs['Roughness'].default_value=.85
    if hasattr(mat,'surface_render_method'):mat.surface_render_method='DITHERED'
