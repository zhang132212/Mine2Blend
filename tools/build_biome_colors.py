"""Compile official biome tint defaults and colormaps for the pinned MC release."""
from pathlib import Path
import json,urllib.request,zipfile,io
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def fetch(url):
    with urllib.request.urlopen(url,timeout=60) as response:return json.load(response)
commit=fetch('https://api.github.com/repos/misode/mcmeta/commits/26.2-data')['sha']
listing=fetch('https://api.github.com/repos/misode/mcmeta/contents/data/minecraft/worldgen/biome?ref='+commit)
with zipfile.ZipFile(ROOT/'test-output/mcmeta-26.2-assets.zip') as z:
    maps={kind:Image.open(io.BytesIO(z.read(next(n for n in z.namelist() if n.endswith('/colormap/'+kind+'.png'))))).convert('RGB') for kind in ('grass','foliage','dry_foliage')}
def compile(item):
    biome=fetch(item['download_url']);t=max(0,min(1,biome['temperature']));h=max(0,min(1,biome['downfall']))*t
    colors={k:list(image.getpixel((int((1-t)*255),int((1-h)*255)))) for k,image in maps.items()}
    effects=biome.get('effects',{})
    for k in ('grass','foliage','dry_foliage','water'):
        value=effects.get(k+'_color')
        if value is not None:
            n=int(value.removeprefix('#'),16) if isinstance(value,str) else value
            colors[k]=[(n>>shift)&255 for shift in (16,8,0)]
    colors.setdefault('water',[63,118,228])
    if effects.get('grass_color_modifier')=='dark_forest':
        n=(colors['grass'][0]<<16)|(colors['grass'][1]<<8)|colors['grass'][2];n=((n&0xfefefe)+0x28340a)>>1
        colors['grass']=[(n>>shift)&255 for shift in (16,8,0)]
    colors['modifier']=effects.get('grass_color_modifier')
    return 'minecraft:'+item['name'][:-5],colors
with ThreadPoolExecutor(max_workers=8) as pool:result=dict(pool.map(compile,listing))
(ROOT/'editor/data/biome-colors.json').write_text(json.dumps({'version':'26.2','data_commit':commit,'biomes':result},separators=(',',':')))
print('BIOME_COLORS_OK',len(result),commit)
