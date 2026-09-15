"""Numbered CTM tiles for pixel/UV verification, generated without game assets."""
from pathlib import Path
from PIL import Image,ImageDraw
import colorsys,json,zipfile
root=Path(__file__).resolve().parents[1]
out=root/'test-output/ctm-test-pack.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
    z.writestr('pack.mcmeta',json.dumps({'pack':{'pack_format':88,'description':'Mine2Blend CTM numbered QA'}}))
    base='assets/minecraft/optifine/ctm/qa/'
    z.writestr(base+'stone.properties','matchBlocks=minecraft:stone\nmethod=ctm\ntiles=0-46\nfaces=north\n')
    import io
    for i in range(47):
        rgb=tuple(int(c*220+25) for c in colorsys.hsv_to_rgb(i/47,0.65,0.85))
        im=Image.new('RGBA',(32,32),(*rgb,255));d=ImageDraw.Draw(im)
        d.rectangle((0,0,31,31),outline=(20,20,20,255),width=2)
        d.text((8,8),str(i),fill=(0,0,0,255))
        data=io.BytesIO();im.save(data,format='PNG');z.writestr(base+str(i)+'.png',data.getvalue())
print(out)
