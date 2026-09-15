"""Overlay local zip/folder resource packs without modifying the base resources."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import tempfile
import zipfile
from .ctm import CTM, Rule

ALPHA_CACHE={}

def alpha_class(path,data):
    if path in ALPHA_CACHE:return ALPHA_CACHE[path]
    result='translucent'
    # RGB/grayscale PNG without a transparency chunk is fully opaque.
    if data[:8]==b'\x89PNG\r\n\x1a\n' and len(data)>26 and data[25] in (0,2) and b'tRNS' not in data:result='opaque'
    else:
        try:
            import bpy,numpy as np
            image=bpy.data.images.load(path,check_existing=True)
            if image.size[0]*image.size[1]>16_777_216:raise ValueError('Resource image exceeds 16 million pixels')
            pixels=np.empty(len(image.pixels),dtype=np.float32);image.pixels.foreach_get(pixels)
            alpha=pixels[3::4]
            if len(alpha):result='opaque' if np.all(alpha>=.99999) else 'cutout' if np.all((alpha<=.00001)|(alpha>=.99999)) else 'translucent'
        except ImportError:pass  # Non-Blender inspection stays conservative.
    ALPHA_CACHE[path]=result
    if len(ALPHA_CACHE)>4096:ALPHA_CACHE.pop(next(iter(ALPHA_CACHE)))
    return result

def load(library,path):
    source=Path(path).resolve()
    archive=zipfile.ZipFile(source) if source.is_file() else None
    try:
        names=archive.namelist() if archive else [p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file()]
        def read(name):
            if '..' in PurePosixPath(name).parts or name.startswith('/'):
                raise ValueError('Unsafe resource path')
            if archive:
                info=archive.getinfo(name)
                if info.file_size>64_000_000:raise ValueError('Resource entry too large')
                return archive.read(name)
            resolved=(source/name).resolve()
            if not resolved.is_relative_to(source):raise ValueError('Resource symlink leaves pack')
            return resolved.read_bytes()
        meta=json.loads(read('pack.mcmeta'))
        pack=meta.get('pack',{})
        if not any(k in pack for k in ('pack_format','min_format','supported_formats')):raise ValueError('Missing resource pack format')
        cache=Path(tempfile.gettempdir())/'Mine2Blend'/'resource-images'
        cache.mkdir(parents=True,exist_ok=True)
        definitions={};models={};textures={};alphas={};rules=[];diagnostics=[]
        total=0
        for name in names:
            parts=PurePosixPath(name).parts
            if len(parts)<4 or parts[0]!='assets':continue
            ns=parts[1];relative='/'.join(parts[2:]);prefix='' if ns=='minecraft' else ns+':'
            if relative.startswith('models/') and relative.endswith('.json'):
                models[prefix+relative[7:-5]]=json.loads(read(name))
            elif relative.startswith('blockstates/') and relative.endswith('.json'):
                definitions[prefix+relative[12:-5]]=json.loads(read(name))
            elif name.endswith('.properties') and relative.startswith(('optifine/ctm/','mcpatcher/ctm/')):
                try:rules.append(Rule.parse(ns+':'+relative,read(name).decode('utf-8-sig')))
                except ValueError as exc:diagnostics.append(str(exc))
            elif name.endswith('.png') and relative.startswith(('textures/','optifine/ctm/','mcpatcher/ctm/')):
                data=read(name);total+=len(data)
                if total>512_000_000:raise ValueError('Resource images exceed 512MB')
                digest=hashlib.sha256(data).hexdigest();target=cache/(digest+'.png')
                if not target.exists():target.write_bytes(data)
                key=prefix+relative.removeprefix('textures/')[:-4]
                textures[key]=str(target);alphas[key]=alpha_class(str(target),data)
        library.models.update(models);library.definitions.update(definitions)
        library.texture_overrides.update(textures)
        library.texture_alpha.update(alphas)
        # A later pack replaces rules sharing the same resource path.
        combined={r.source:r for r in library.ctm.rules}
        combined.update({r.source:r for r in rules});library.ctm=CTM(combined.values())
        library.model.cache_clear();library.quads.cache_clear();library.missing.clear()
        library.boundary.cache_clear();library.full_opaque.cache_clear()
        library.occluded_cached.cache_clear()
        library.alternatives.cache_clear();library.all_choices.cache_clear()
        if hasattr(library,'prototype_cache'):library.prototype_cache.clear()
        return {'path':str(source),'pack':pack,'models':len(models),'blockstates':len(definitions),'textures':len(textures),'ctm_rules':len(rules),'diagnostics':diagnostics}
    finally:
        if archive:archive.close()
