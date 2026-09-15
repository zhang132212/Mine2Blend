"""Compile a local Minecraft client/resource ZIP or pinned mcmeta asset archive.

No archive paths are extracted. Models and first animation frames form a local atlas.
Usage: python tools/build_resources.py archive.zip --output editor/data/resources
"""
import argparse
import io
import json
from pathlib import Path
import zipfile
from PIL import Image

def build(source, output, version="custom-unverified"):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    models, definitions, images = {}, {}, []
    with zipfile.ZipFile(source) as archive:
        names = archive.namelist()
        for name in names:
            marker = "assets/minecraft/"
            if marker not in name:
                continue
            relative = name.split(marker, 1)[1]
            if relative.startswith("models/") and name.endswith(".json"):
                models[relative[7:-5]] = json.loads(archive.read(name))
            elif relative.startswith("blockstates/") and name.endswith(".json"):
                definitions[relative[12:-5]] = json.loads(archive.read(name))
            elif relative.startswith("textures/") and name.endswith(".png"):
                if not relative.startswith(("textures/block/", "textures/entity/")):
                    continue
                image = Image.open(io.BytesIO(archive.read(name))).convert("RGBA")
                if name + ".mcmeta" in names:
                    animation = json.loads(archive.read(name + ".mcmeta")).get("animation", {})
                    width = animation.get("width", image.width)
                    height = animation.get("height", min(image.height, width))
                    frames = animation.get("frames", [0])
                    first = frames[0] if frames else 0
                    first = first.get("index", 0) if isinstance(first, dict) else first
                    columns = max(1, image.width // width)
                    x,y = (first % columns)*width, (first // columns)*height
                    image = image.crop((x,y,x+width,y+height))
                images.append((relative[9:-4], image))
    if not definitions or not models:
        raise ValueError("No Minecraft blockstates/models found")
    atlas_width = max(2048, max(i.width+2 for _,i in images))
    atlas_width = 1 << (atlas_width - 1).bit_length()
    x,y,row_height = 0,0,0
    placements, uv = [], {}
    for name, image in sorted(images, key=lambda p: (-p[1].height, p[0])):
        if x+image.width+2 > atlas_width:
            x,y,row_height = 0,y+row_height,0
        uv[name] = [x+1,y+1,image.width,image.height]
        placements.append((image,x+1,y+1))
        row_height = max(row_height,image.height+2)
        x += image.width+2
    atlas_height = 1 << (y+row_height-1).bit_length()
    atlas = Image.new("RGBA", (atlas_width, atlas_height))
    for image,x,y in placements:
        atlas.paste(image,(x,y))
    atlas.save(output / "atlas.png")
    alpha={name:('opaque' if image.getchannel('A').getextrema()==(255,255) else 'cutout' if set(image.getchannel('A').getdata())<={0,255} else 'translucent') for name,image in images}
    for filename,data in (("block-models.json",models),("block-definitions.json",definitions),("atlas-uv.json",uv),("texture-alpha.json",alpha)):
        (output / filename).write_text(json.dumps(data,separators=(",", ":")),encoding="utf-8")
    report = {"source": str(Path(source).resolve()), "models":len(models),"blockstates":len(definitions),"textures":len(images),
              "atlas_size":[atlas_width,atlas_height],"animation":"first frame", "version":version}
    (output / "resource-info.json").write_text(json.dumps(report,indent=2))
    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("--output", required=True)
    parser.add_argument("--version", default="custom-unverified")
    args = parser.parse_args()
    print(json.dumps(build(args.source,args.output,args.version),indent=2))
