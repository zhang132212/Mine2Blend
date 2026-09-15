"""Version-pinned vanilla state validation and resource-pack model selection."""
from pathlib import Path
import json
import zipfile
from functools import lru_cache
from .grid import BlockRecord

class Registry:
    def __init__(self):
        self.blocks = json.loads((Path(__file__).parent / "data/blocks.json").read_text())

    @lru_cache(maxsize=8192)
    def resolve(self, state, nbt=None):
        b = BlockRecord.parse(state, nbt)
        key = b.block_id.removeprefix("minecraft:")
        if not b.block_id.startswith("minecraft:") or key not in self.blocks:
            raise ValueError(f"Unknown 26.2 block: {b.block_id}")
        allowed, defaults = self.blocks[key]
        props = dict(defaults)
        for k, v in b.properties:
            if k not in allowed or v not in allowed[k]:
                raise ValueError(f"Invalid property {k}={v} for {b.block_id}")
            props[k] = v
        if nbt is not None:
            from .formats import dependencies
            nbtlib, _ = dependencies()
            if not isinstance(nbtlib.parse_nbt(nbt), nbtlib.Compound):
                raise ValueError("Block entity NBT must be an SNBT compound")
        return BlockRecord(b.block_id, tuple(sorted(props.items())), nbt)

    def search(self, query="", offset=0, limit=100):
        keys = sorted(k for k in self.blocks if query.lower() in k)
        return {"total": len(keys), "items": [{"id": "minecraft:" + k,
                 "properties": self.blocks[k][0], "defaults": self.blocks[k][1],
                 "property_schema":{name:property_schema(values,self.blocks[k][1][name]) for name,values in self.blocks[k][0].items()}}
                 for k in keys[offset:offset + min(limit, 500)]]}

def property_schema(values,default):
    if set(values)=={'true','false'}:return {'type':'boolean','default':default=='true'}
    if all(v.lstrip('-').isdigit() for v in values):return {'type':'integer','enum':[int(v) for v in values],'default':int(default)}
    return {'type':'string','enum':values,'default':default}

def matches(condition, properties):
    if not condition:
        return True
    return all((any(matches(c, properties) for c in value) if key == "OR" else
                all(matches(c, properties) for c in value) if key == "AND" else
                properties.get(key) in (str(value).lower() if isinstance(value,bool) else str(value)).split("|")) for key, value in condition.items())

class ResourcePack:
    def __init__(self, path):
        self.path = Path(path)
        self.archive = zipfile.ZipFile(path) if self.path.is_file() else None
        self.cache = {}
        self.metadata = self.read("pack.mcmeta")

    def read(self, name):
        if name not in self.cache:
            data = self.archive.read(name) if self.archive else (self.path / name).read_bytes()
            self.cache[name] = json.loads(data)
        return self.cache[name]

    def model(self, identifier, visited=()):
        identifier = identifier if ":" in identifier else "minecraft:" + identifier
        if identifier in visited or len(visited) > 64:
            raise ValueError("Cyclic model parent")
        namespace, name = identifier.split(":", 1)
        current = self.read(f"assets/{namespace}/models/{name}.json")
        parent = self.model(current["parent"], (*visited, identifier)) if "parent" in current and not current["parent"].startswith("builtin/") else {}
        return {**parent, **current, "textures": {**parent.get("textures", {}), **current.get("textures", {})}}

    def select(self, block):
        namespace, name = block.block_id.split(":", 1)
        definition = self.read(f"assets/{namespace}/blockstates/{name}.json")
        props = dict(block.properties)
        selected = []
        for key, value in definition.get("variants", {}).items():
            cond = dict(part.split("=", 1) for part in key.split(",") if part)
            if matches(cond, props):
                selected.append(value)
                break
        for part in definition.get("multipart", []):
            if matches(part.get("when", {}), props):
                selected.append(part["apply"])
        # Stable representative of weighted alternatives, independent of Python hash seed.
        return [v[0] if isinstance(v, list) else v for v in selected]
