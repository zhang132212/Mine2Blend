"""Backfill texture opacity metadata from an already compiled atlas."""
from pathlib import Path
import json
from PIL import Image
root=Path(__file__).resolve().parents[1]/'editor/data/resources'
atlas=Image.open(root/'atlas.png').convert('RGBA')
uv=json.loads((root/'atlas-uv.json').read_text());result={}
for name,(x,y,w,h) in uv.items():
    alpha=atlas.crop((x,y,x+w,y+h)).getchannel('A')
    result[name]='opaque' if alpha.getextrema()==(255,255) else 'cutout' if set(alpha.getdata())<={0,255} else 'translucent'
(root/'texture-alpha.json').write_text(json.dumps(result,separators=(',',':')))
