"""Sparse, transactional block storage. Coordinates are Minecraft XYZ (Y up)."""
from collections import Counter
from dataclasses import dataclass, field
from itertools import product
import copy
import json
import re
import uuid

AIR = "minecraft:air"
DIRECTIONS = {"east": (1, 0, 0), "west": (-1, 0, 0), "up": (0, 1, 0),
              "down": (0, -1, 0), "south": (0, 0, 1), "north": (0, 0, -1)}

def position(value):
    if len(value) != 3 or any(type(v) is not int for v in value):
        raise ValueError("Coordinates must be three integers")
    return tuple(value)

def mc_to_blender(p):
    return (p[0], -p[2], p[1])

def blender_to_mc(p):
    return (p[0], p[2], -p[1])

def parse_state(value):
    match = re.fullmatch(r"([a-z0-9_.-]+:[a-z0-9_./-]+)(?:\[([^\]]*)\])?", value)
    if not match:
        raise ValueError("Expected namespace:block[property=value]")
    props = {}
    for item in (match[2] or "").split(","):
        if not item:
            continue
        pair = item.split("=")
        if len(pair) != 2 or not all(re.fullmatch(r"[a-z0-9_-]+", s) for s in pair) or pair[0] in props:
            raise ValueError("Invalid or duplicate block property")
        props[pair[0]] = pair[1]
    return match[1], props

@dataclass(frozen=True)
class BlockRecord:
    block_id: str
    properties: tuple = ()
    nbt: str | None = None  # typed SNBT, never lossy untyped JSON

    @classmethod
    def parse(cls, state, nbt=None):
        block_id, props = parse_state(state)
        return cls(block_id, tuple(sorted(props.items())), nbt)

    @property
    def state(self):
        return self.block_id + ("[" + ",".join(f"{k}={v}" for k, v in self.properties) + "]" if self.properties else "")

    def json(self):
        return {"state": self.state, "nbt": self.nbt}

@dataclass
class Region:
    name: str
    origin: tuple
    size: tuple
    entities: list = field(default_factory=list)  # region-local typed SNBT
    pending_ticks: dict = field(default_factory=dict)

    def contains(self, p):
        return all(min(o, o + s - (1 if s > 0 else -1)) <= x <= max(o, o + s - (1 if s > 0 else -1))
                   for x, o, s in zip(p, self.origin, self.size))

class BlockGrid:
    def __init__(self, name="Building", data_version=4903, grid_id=None):
        self.id = grid_id or uuid.uuid4().hex
        self.name = name
        self.data_version = data_version
        self.blocks = {}
        self.chunks = {}
        self.regions = []
        self.components = {}
        self.source_metadata = {}
        self.resource_packs = []
        self.view = {"hidden_layers":[],"slice_min":None,"slice_max":None,"isolate":None,"xray":False,"biome":"minecraft:plains","renderer":"mesh"}
        self.dirty = set()
        self.revision = 0
        self._undo, self._redo = [], []
        self._chunk_arrays = {}
        self._bounds_cache = None

    def _set(self, p, block):
        chunk = tuple(v // 16 for v in p)
        self._chunk_arrays.pop(chunk,None)
        if self._bounds_cache is not None:
            lo,hi=self._bounds_cache
            if block is None or block.block_id==AIR:
                if any(p[i] in (lo[i],hi[i]) for i in range(3)):self._bounds_cache=None
            else:self._bounds_cache=(tuple(min(p[i],lo[i]) for i in range(3)),tuple(max(p[i],hi[i]) for i in range(3)))
        if block is None or block.block_id == AIR:
            self.blocks.pop(p, None)
            if chunk in self.chunks:
                self.chunks[chunk].discard(p)
                if not self.chunks[chunk]:
                    del self.chunks[chunk]
        else:
            self.blocks[p] = block
            self.chunks.setdefault(chunk, set()).add(p)
        self.dirty.add(chunk)
        self.dirty.update(product(*({(v-1)//16,v//16,(v+1)//16} for v in p)))

    def chunk_array(self,chunk):
        """Read-only uint16 palette array [Y,Z,X], X fastest; air is index zero."""
        import numpy as np
        chunk=position(chunk)
        if chunk in self._chunk_arrays:return self._chunk_arrays[chunk]
        values=np.zeros((16,16,16),dtype=np.uint16)
        palette=[BlockRecord(AIR)];lookup={palette[0]:0}
        for p in sorted(self.chunks.get(chunk,())):
            block=self.blocks[p]
            if block not in lookup:lookup[block]=len(palette);palette.append(block)
            values[p[1]%16,p[2]%16,p[0]%16]=lookup[block]
        values.flags.writeable=False
        result=(tuple(palette),values);self._chunk_arrays[chunk]=result
        if len(self._chunk_arrays)>256:self._chunk_arrays.pop(next(iter(self._chunk_arrays)))
        return result

    def metadata(self):
        return copy.deepcopy({"regions":[r.__dict__ for r in self.regions],"components":self.components,"source_metadata":self.source_metadata,"resource_packs":self.resource_packs,"view":self.view})

    def restore_metadata(self,data):
        self.regions=[Region(**r) for r in data["regions"]]
        self.components=copy.deepcopy(data["components"])
        self.source_metadata=copy.deepcopy(data.get('source_metadata',{}))
        self.resource_packs=list(data["resource_packs"])
        self.view=copy.deepcopy(data["view"])
        self.dirty.update(self.chunks)

    def apply(self, changes, expected_revision=None, metadata=None):
        if expected_revision is not None and expected_revision != self.revision:
            raise ValueError(f"Revision conflict: expected {expected_revision}, actual {self.revision}")
        checked = {}
        for p, b in changes:
            p = position(p)
            if b is not None and not isinstance(b, BlockRecord):
                raise ValueError("Expected BlockRecord")
            checked[p] = None if b and b.block_id == AIR else b
            if len(checked) > 1_000_000:
                raise ValueError("Transaction exceeds 1,000,000 positions")
        delta = [(p, self.blocks.get(p), b) for p, b in checked.items() if self.blocks.get(p) != b]
        before=self.metadata() if metadata is not None else None
        for p, old, new in delta:
            self._set(p, new)
        meta_changed=metadata is not None and before!=metadata
        if meta_changed:self.restore_metadata(metadata)
        if delta or meta_changed:
            self._undo.append((delta,before,copy.deepcopy(metadata)))
            self._undo = self._undo[-20:]
            self._redo.clear()
            self.revision += 1
        return {"changed": len(delta), "revision": self.revision, "dirty_chunks": len(self.dirty)}

    def undo(self, redo=False):
        source, target = (self._redo, self._undo) if redo else (self._undo, self._redo)
        if not source:
            return {"changed": 0, "revision": self.revision}
        delta,before,after = source.pop()
        for p, old, new in delta:
            self._set(p, new if redo else old)
        if before is not None:self.restore_metadata(after if redo else before)
        target.append((delta,before,after))
        self.revision += 1
        return {"changed": len(delta), "revision": self.revision}

    def fill(self, minimum, maximum, block, expected_revision=None, replace=None):
        lo, hi = position(minimum), position(maximum)
        volume = 1
        for a, b in zip(lo, hi):
            if a > b:
                raise ValueError("Minimum exceeds maximum")
            volume *= b - a + 1
        if volume > 1_000_000:
            raise ValueError("Region exceeds 1,000,000 blocks")
        return self.apply(((p, block) for p in product(*(range(a, b + 1) for a, b in zip(lo, hi)))
                           if replace is None or self.blocks.get(p, BlockRecord(AIR)).state == replace), expected_revision)

    @property
    def bounds(self):
        if not self.blocks:
            return None
        if self._bounds_cache is None:
            self._bounds_cache=(tuple(min(p[i] for p in self.blocks) for i in range(3)),tuple(max(p[i] for p in self.blocks) for i in range(3)))
        return list(self._bounds_cache)

    def summary(self):
        return {"grid_id": self.id, "name": self.name, "revision": self.revision,
                "data_version": self.data_version, "bounds": self.bounds,
                "block_count": len(self.blocks), "chunk_count": len(self.chunks),
                "materials": dict(Counter(b.state for b in self.blocks.values())),
                "regions": [r.__dict__ for r in self.regions]}

    def to_dict(self):
        return {"schema": 1, "id": self.id, "name": self.name, "data_version": self.data_version,
                "revision": self.revision, **self.metadata(),
                "blocks": [[*p, b.state, b.nbt] for p, b in sorted(self.blocks.items())]}

    @classmethod
    def from_dict(cls, data):
        if data.get("schema") != 1:
            raise ValueError("Unsupported BlockGrid schema")
        grid = cls(data["name"], data["data_version"], data["id"])
        for x, y, z, state, nbt in data["blocks"]:
            grid._set(position((x, y, z)), BlockRecord.parse(state, nbt))
        grid.regions = [Region(**r) for r in data.get("regions", [])]
        grid.components=data.get("components",{})
        grid.source_metadata=data.get('source_metadata',{})
        grid.resource_packs=data.get("resource_packs",[])
        grid.view.update(data.get("view",{}))
        grid.revision = data["revision"]
        return grid
