"""OptiFine/Continuity connected texture selection in face-local coordinates.

CTM index map and overlay tile topology adapted from Continuity, LGPL-3.0:
PepperCode1/Continuity e283f6e5ba2972d943be28809d80061974f0a6c4.
See LICENSES/Continuity-LGPL-3.0.txt and THIRD_PARTY.md.
"""
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import json
import re
from .grid import DIRECTIONS

INDEX = json.loads((Path(__file__).parent/'data/ctm-map.json').read_text())
BASES = {  # left, down, right, up in the face's canonical texture orientation
    'north':('east','down','west','up'), 'south':('west','down','east','up'),
    'west':('north','down','south','up'), 'east':('south','down','north','up'),
    'up':('west','south','east','north'), 'down':('west','north','east','south')}
def add(a,b): return tuple(x+y for x,y in zip(a,b))
def texture_id(name):
    name=name.removesuffix('.png')
    if ':' not in name: name='minecraft:'+name
    ns,path=name.split(':',1)
    if '/' not in path: path='block/'+path
    return ns+':'+path.removeprefix('textures/')

def properties(text):
    result={};pending=''
    for line in text.splitlines():
        line=pending+line.strip()
        if line.endswith('\\') and not line.endswith('\\\\'):
            pending=line[:-1];continue
        pending=''
        if not line or line[0] in '#!':continue
        pair=re.split(r'(?<!\\)\s*[=:]\s*',line,maxsplit=1)
        if len(pair)==2:result[pair[0].strip()]=pair[1].strip()
    return result

def block_match(pattern,block):
    if block is None:return False
    parts=pattern.split(':')
    if len(parts)>1 and '=' not in parts[1]: identifier=':'.join(parts[:2]);parts=parts[2:]
    else: identifier='minecraft:'+parts[0];parts=parts[1:]
    if block.block_id!=identifier:return False
    props=dict(block.properties)
    return all('=' in p and props.get(p.split('=',1)[0]) in p.split('=',1)[1].split(',') for p in parts)

def tile_list(text,source):
    base=str(PurePosixPath(source).parent)
    result=[]
    for token in text.split():
        match=re.fullmatch(r'(\d+)-(\d+)',token)
        names=[str(i) for i in range(int(match[1]),int(match[2])+1)] if match else [token]
        for name in names:
            if name.startswith('<'):result.append(name);continue
            if name.startswith('~/'):name='optifine/'+name[2:]
            elif name.startswith('/'):name=name[1:]
            elif ':' not in name and not name.startswith(('textures/','optifine/','mcpatcher/')):name=base+'/'+name
            result.append(texture_id(name))
    return result

@dataclass
class Rule:
    source:str
    data:dict
    tiles:list

    @classmethod
    def parse(cls,source,text):
        data=properties(text)
        method=data.setdefault('method','ctm')
        if method not in ('ctm','horizontal','vertical','overlay','repeat','fixed','overlay_ctm','overlay_repeat','overlay_fixed'):
            raise ValueError('Unsupported CTM method: '+method)
        if not data.get('matchBlocks') and not data.get('matchTiles'):
            stem=PurePosixPath(source).stem
            data['matchBlocks' if stem.startswith('block_') else 'matchTiles']=stem.removeprefix('block_')
        tiles=tile_list(data.get('tiles','0-46' if method=='ctm' else ''),source)
        amount={'ctm':47,'horizontal':4,'vertical':4,'overlay':17,'fixed':1,'overlay_ctm':47,'overlay_fixed':1}.get(method)
        if method in ('repeat','overlay_repeat'):
            w,h=int(data.get('width',0)),int(data.get('height',0))
            if w<1 or h<1:raise ValueError('Repeat dimensions must be positive')
            amount=w*h
        if len(tiles)<amount:raise ValueError(f'{source}: expected at least {amount} tiles')
        return cls(source,data,tiles)

    @property
    def order(self):return (0 if self.data.get('matchTiles') else 1,-int(self.data.get('weight',0)),self.source)

    def matches(self,block,texture,face,biome='minecraft:plains'):
        d=self.data
        if d.get('matchBlocks') and not any(block_match(p,block) for p in d['matchBlocks'].split()):return False
        if d.get('matchTiles') and texture_id(texture) not in [texture_id(p) for p in d['matchTiles'].split()]:return False
        faces=d.get('faces','all').split()
        if 'all' not in faces and face not in faces and {'up':'top','down':'bottom'}.get(face) not in faces and not ('sides' in faces and face not in ('up','down')):return False
        if 'biomes' in d:
            text=d['biomes'];neg=text.startswith('!');names=text.lstrip('!').split()
            found=biome in [n if ':' in n else 'minecraft:'+n for n in names]
            if found==neg:return False
        return True

    def select(self,p,block,texture,face,get,face_texture,biome='minecraft:plains',is_solid=lambda b:b is not None):
        if not self.matches(block,texture,face,biome):return []
        d=self.data;method=d['method'];basis=[DIRECTIONS[n] for n in BASES[face]]
        connect=d.get('connect','tile' if d.get('matchTiles') else 'block')
        def same(q):
            other=get(q)
            if other is None:return False
            return other.state==block.state if connect=='state' else texture_id(face_texture(other,face))==texture_id(texture) if connect=='tile' else other.block_id==block.block_id
        edges=[same(add(p,v)) for v in basis]
        mask=sum((1<<(2*i)) for i,v in enumerate(edges) if v)
        for i in range(4):
            if edges[i] and edges[(i+1)%4] and same(add(add(p,basis[i]),basis[(i+1)%4])):mask|=1<<(2*i+1)
        if method in ('ctm','overlay_ctm'):indices=[INDEX[mask]]
        elif method=='horizontal':indices=[(3,2,0,1)[int(edges[0])+2*int(edges[2])]]
        elif method=='vertical':indices=[(3,2,0,1)[int(edges[1])+2*int(edges[3])]]
        elif method in ('repeat','overlay_repeat'):
            x,y,z=p;u,v={'down':(x,-z-1),'up':(x,z),'north':(-x-1,-y),'south':(x,-y),'west':(z,-y),'east':(-z-1,-y)}[face]
            w,h=int(d['width']),int(d['height']);indices=[(v%h)*w+u%w]
        elif method in ('fixed','overlay_fixed'):indices=[0]
        else:
            def applies(q):
                other=get(q)
                if not is_solid(other) or same(q) or is_solid(get(add(q,DIRECTIONS[face]))):return False
                if d.get('connectBlocks') and not any(block_match(v,other) for v in d['connectBlocks'].split()):return False
                if d.get('connectTiles') and texture_id(face_texture(other,face)) not in [texture_id(v) for v in d['connectTiles'].split()]:return False
                return True
            applications=[applies(add(p,v)) for v in basis]
            m=sum(1<<i for i,v in enumerate(applications) if v)
            sides={15:[8],7:[5],11:[6],13:[13],14:[12],5:[9,7],10:[1,15],3:[4],6:[3],12:[10],9:[11],1:[9],2:[1],4:[7],8:[15],0:[]}
            indices=list(sides[m])
            for i,tile in enumerate((2,0,14,16)):
                j=(i+1)%4
                if not applications[i] and not applications[j]:
                    neighbors=[get(add(p,basis[k])) for k in (i,j)]
                    matching=any(self.matches(b,face_texture(b,face),face,biome) for b in neighbors if b)
                    if matching and applies(add(add(p,basis[i]),basis[j])):indices.append(tile)
        return [self.tiles[i] for i in indices if self.tiles[i]!='<skip>']

class CTM:
    def __init__(self,rules=()):self.rules=sorted(rules,key=lambda r:r.order)
    def select(self,p,block,texture,face,get,face_texture,biome='minecraft:plains',is_solid=lambda b:b is not None):
        base=texture;overlays=[]
        for rule in self.rules:
            found=rule.select(p,block,base,face,get,face_texture,biome,is_solid)
            if not found:continue
            if rule.data['method'].startswith('overlay'):overlays.extend(found)
            else:
                if found[0]!='<default>':base=found[0]
                break
        return base,overlays
