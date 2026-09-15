"""Overlay local zip/folder resource packs without modifying the base resources."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import tempfile
import zipfile
from .ctm import CTM, Rule

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
        definitions={};models={};textures={};rules=[];diagnostics=[]
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
                textures[prefix+relative.removeprefix('textures/')[:-4]]=str(target)
        library.models.update(models);library.definitions.update(definitions)
        library.texture_overrides.update(textures)
        # A later pack replaces rules sharing the same resource path.
        combined={r.source:r for r in library.ctm.rules}
        combined.update({r.source:r for r in rules});library.ctm=CTM(combined.values())
        library.model.cache_clear();library.quads.cache_clear();library.missing.clear()
        library.boundary.cache_clear();library.full_opaque.cache_clear()
        library.occluded_cached.cache_clear()
        return {'path':str(source),'pack':pack,'models':len(models),'blockstates':len(definitions),'textures':len(textures),'ctm_rules':len(rules),'diagnostics':diagnostics}
    finally:
        if archive:archive.close()
