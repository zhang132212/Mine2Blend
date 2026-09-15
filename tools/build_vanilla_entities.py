"""Bind extracted 26.2 model layers to pinned vanilla entity textures."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'editor/data/resources'

def build():
    layers=json.loads((ASSETS/'vanilla-model-layers.json').read_text())['layers']
    atlas=json.loads((ASSETS/'atlas-uv.json').read_text())
    old=json.loads((ASSETS/'entity-models.json').read_text())
    catalog=json.loads((ROOT/'resources/converter/win-x64/assets/entity-models/entity-catalog.json').read_text())
    aliases={'boat':'boat/oak','chest_boat':'chest_boat/oak','tropical_fish':'tropical_fish_small','pufferfish':'pufferfish_small','mooshroom':'cow'}
    extras={
        'armadillo':'entity/armadillo/armadillo','breeze':'entity/breeze/breeze','bogged':'entity/skeleton/bogged',
        'camel':'entity/camel/camel','camel_husk':'entity/camel/camel_husk','copper_golem':'entity/copper_golem/copper_golem',
        'creaking':'entity/creaking/creaking','happy_ghast':'entity/ghast/happy_ghast','nautilus':'entity/nautilus/nautilus',
        'zombie_nautilus':'entity/nautilus/zombie_nautilus','sniffer':'entity/sniffer/sniffer','bat':'entity/bat/bat',
        'ghast':'entity/ghast/ghast','magma_cube':'entity/slime/magmacube','vex':'entity/illager/vex'}
    for name,texture in extras.items():catalog['minecraft:'+name]={'model':name+'.json','texture':texture}
    special_overlays={'breeze':[('breeze#wind','entity/breeze/breeze_wind')],'bogged':[('bogged#outer','entity/skeleton/bogged_overlay')]}
    overlay_aliases={'sheep_fur':'sheep#wool','drowned_outer':'drowned#outer','slime_outer':'slime#outer','stray_outer':'stray#outer','creeper_armor':'creeper#armor'}
    models=dict(old['models']);updated={};variants={};unresolved=[]
    def quads(layer,texture):
        texture=texture.removeprefix('minecraft:');layer=layer if ':' in layer else 'minecraft:'+layer
        if layer not in layers or texture not in atlas:return None
        return [[p,uv,texture,None,[1,1,1],False] for p,uv,part in layers[layer]]
    for identifier,spec in catalog.items():
        name=identifier.split(':')[1];base=aliases.get(name,name)
        for suffix,folder in (('_chest_boat','chest_boat'),('_boat','boat'),('_chest_raft','chest_boat'),('_raft','boat')):
            if name not in aliases and name.endswith(suffix):base=folder+'/'+name.removesuffix(suffix);break
        if base+'#main' not in layers and 'minecraft:'+base+'#main' not in layers:base=Path(spec['model']).stem
        if name=='camel_husk':base='camel'
        layer=base+'#main';geometry=quads(layer,spec['texture'])
        if not geometry:unresolved.append(identifier);continue
        for overlay in spec.get('overlays',[]):
            stem=Path(overlay['model']).stem;extra=quads(overlay_aliases.get(stem,base+'#'+stem.removeprefix(base+'_')),overlay['texture'])
            if extra:geometry.extend(extra)
        for extra,texture in special_overlays.get(name,[]):geometry.extend(quads(extra,texture) or [])
        models[identifier]=geometry;updated[identifier]='minecraft:'+layer
        baby_layer=base+'_baby#main'
        baby_texture=spec['texture'].removeprefix('minecraft:')
        candidate=baby_texture+'_baby'
        if candidate in atlas:baby_texture=candidate
        if name=='sniffer':baby_texture='entity/sniffer/snifflet'
        baby=quads(baby_layer,baby_texture)
        if baby:variants.setdefault(identifier,{})['baby']=baby
        if name in ('cow','pig','chicken'):
            for climate in ('cold','warm'):
                candidate='entity/'+name+'/'+name+'_'+climate
                geometry=quads(climate+'_'+name+'#main',candidate) or quads(name+'#main',candidate)
                if geometry:variants.setdefault(identifier,{})[climate]=geometry
        if name=='copper_golem':
            for weather in ('exposed','weathered','oxidized'):
                geometry=quads(layer,'entity/copper_golem/copper_golem_'+weather)
                if geometry:variants.setdefault(identifier,{})[weather]=geometry
    data={'geometry_source':'Minecraft Java 26.2 baked ModelPart layers; fallback catalog explicitly listed',
          'models':models,'variants':variants,'vanilla_layers':updated,'legacy_geometry':sorted(set(models)-set(updated)),
          'unresolved':unresolved}
    (ASSETS/'entity-models.json').write_text(json.dumps(data,separators=(',',':')))
    print('VANILLA_ENTITIES_OK',len(updated),'updated;',len(data['legacy_geometry']),'legacy;',len(models),'total')
    return data

if __name__=='__main__':build()
