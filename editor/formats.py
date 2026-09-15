"""Lossless block/state/NBT litematic adapter. Optional packages are shipped as wheels."""
from pathlib import Path
import os
import tempfile
from .grid import BlockGrid, BlockRecord, Region, AIR

MAX_VOLUME = 8_000_000

def dependencies():
    try:
        import nbtlib
        import litemapy
    except ImportError as exc:
        raise RuntimeError("Install packaged extension wheels (litemapy, nbtlib, typing_extensions)") from exc
    return nbtlib, litemapy

def _check_volume(size):
    volume = abs(size[0] * size[1] * size[2])
    if not volume or volume > MAX_VOLUME:
        raise ValueError(f"Region volume must be 1..{MAX_VOLUME}")

def import_litematic(path):
    nbtlib, lm = dependencies()
    raw = nbtlib.load(path)
    # Validate volume before litemapy allocates dense arrays.
    for tag in raw["Regions"].values():
        _check_volume(tuple(int(tag["Size"][k]) for k in "xyz"))
    schem = lm.Schematic.from_nbt(raw)
    grid = BlockGrid(schem.name, int(schem.mc_version))
    grid.source_metadata['litematic']=raw.get('Metadata',nbtlib.Compound()).snbt()
    occupied_regions = []
    for name, reg in schem.regions.items():
        origin, size = (reg.x, reg.y, reg.z), (reg.width, reg.height, reg.length)
        region = Region(name, origin, size, [e.to_nbt().snbt() for e in reg.entities])
        tag = raw["Regions"][name]
        region.pending_ticks = {k: tag[k].snbt() for k in ("PendingBlockTicks", "PendingFluidTicks") if k in tag}
        # Overlapping regions can contain contradictory air and block records: reject instead of flattening silently.
        for other in occupied_regions:
            def extent(r, i):
                e = r.origin[i] + r.size[i] - (1 if r.size[i] > 0 else -1)
                return sorted((r.origin[i], e))
            if all(max(extent(region, i)[0], extent(other, i)[0]) <= min(extent(region, i)[1], extent(other, i)[1]) for i in range(3)):
                raise ValueError("Overlapping litematic regions need explicit merge policy")
        occupied_regions.append(region)
        tiles = {tuple(t.position): t.to_nbt().snbt() for t in reg.tile_entities}
        for p in reg.block_positions():
            block = reg[p]
            if block.id == AIR:
                continue
            world = tuple(int(p[i] + origin[i]) for i in range(3))
            grid._set(world, BlockRecord.parse(block.to_block_state_identifier(), tiles.get(tuple(p))))
        grid.regions.append(region)
    return grid

def export_litematic(grid, path):
    nbtlib, lm = dependencies()
    regions = list(grid.regions)
    if not regions:
        bounds = grid.bounds
        if not bounds:
            raise ValueError("Cannot export an empty grid without an explicit region")
        lo, hi = bounds
        regions = [Region("Main", lo, tuple(b - a + 1 for a, b in zip(lo, hi)))]
    uncovered = [p for p in grid.blocks if not any(r.contains(p) for r in regions)]
    if uncovered:
        raise ValueError("Blocks outside imported regions; explicitly redefine regions before export")
    result = {}
    for spec in regions:
        _check_volume(spec.size)
        reg = lm.Region(*spec.origin, *spec.size)
        for p, b in grid.blocks.items():
            if not spec.contains(p):
                continue
            local = tuple(p[i] - spec.origin[i] for i in range(3))
            reg[local] = lm.BlockState(b.block_id, **dict(b.properties))
            if b.nbt:
                tag = nbtlib.parse_nbt(b.nbt)
                for k, v in zip("xyz", local):
                    tag[k] = nbtlib.Int(v)
                reg.tile_entities.append(lm.TileEntity(tag))
        reg.entities.extend(lm.Entity(nbtlib.parse_nbt(e)) for e in spec.entities)
        result[spec.name] = reg
    schem = lm.Schematic(name=grid.name, author="Mine2Blend Editor", regions=result, mc_version=grid.data_version)
    root = schem.to_nbt()
    if 'litematic' in grid.source_metadata:
        original=nbtlib.parse_nbt(grid.source_metadata['litematic'])
        for key,value in original.items():
            if key not in ('Name','EnclosingSize','RegionCount','TotalBlocks','TotalVolume','TimeModified'):
                root['Metadata'][key]=value
    for spec in regions:
        for k, snbt in spec.pending_ticks.items():
            root["Regions"][spec.name][k] = nbtlib.parse_nbt(snbt)
    _atomic_nbt(nbtlib.File(root, gzipped=True), path)
    return {"path": str(Path(path).resolve()), "blocks": len(grid.blocks), "regions": len(regions), "data_version": grid.data_version}

def _atomic_nbt(root, path):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(suffix=path.suffix, dir=path.parent)
    os.close(fd)
    try:
        root.save(temporary)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def export_schem(grid, path):
    """Sponge v2 through mcschematic, with explicit DataVersion (no stale enum)."""
    nbtlib, _ = dependencies()
    import mcschematic
    if any(r.pending_ticks for r in grid.regions):
        raise ValueError("Sponge has no scheduled-tick field; use litematic to retain pending ticks")
    if not grid.bounds:
        raise ValueError("Empty grid")
    lo, hi = grid.bounds
    _check_volume(tuple(b - a + 1 for a, b in zip(lo, hi)))
    schem = mcschematic.MCSchematic()
    for p, b in grid.blocks.items():
        schem.setBlock(p, b.state + (b.nbt or ""))
    class TargetVersion:
        value = grid.data_version
    with tempfile.TemporaryDirectory() as folder:
        schem.save(folder, "building", TargetVersion())
        root = nbtlib.load(str(Path(folder) / "building.schem"))
        root['Offset']=nbtlib.IntArray(lo)
        if 'schem' in grid.source_metadata:
            metadata=nbtlib.parse_nbt(grid.source_metadata['schem'])
            root.setdefault('Metadata',nbtlib.Compound()).update(metadata)
        for key,value in zip('XYZ',lo):root.setdefault('Metadata',nbtlib.Compound())['WEOffset'+key]=nbtlib.Int(value)
        entities=[]
        for region in grid.regions:
            for snbt in region.entities:
                entity=nbtlib.parse_nbt(snbt)
                entity['Pos']=nbtlib.List[nbtlib.Double]([float(entity['Pos'][i])+region.origin[i]-lo[i] for i in range(3)])
                entity['Id']=entity.pop('id')
                entities.append(entity)
        root['Entities']=nbtlib.List[nbtlib.Compound](entities)
        _atomic_nbt(root, path)
    return {"path": str(Path(path).resolve()), "blocks": len(grid.blocks), "format": "Sponge v2"}

def import_schem(path):
    nbtlib, _ = dependencies()
    root = nbtlib.load(path)
    root = root.get("Schematic", root)
    version = int(root["Version"])
    if version not in (2, 3):
        raise ValueError("Only Sponge v2/v3 supported")
    size = tuple(int(root[k]) & 65535 for k in ("Width", "Height", "Length"))
    _check_volume(size)
    origin = tuple(int(v) for v in root.get("Offset", [0, 0, 0]))
    if version == 2 and "Metadata" in root and all("WEOffset" + k in root["Metadata"] for k in "XYZ"):
        origin = tuple(int(root["Metadata"]["WEOffset" + k]) for k in "XYZ")
    grid = BlockGrid(Path(path).stem, int(root["DataVersion"]))
    grid.source_metadata['schem']=root.get('Metadata',nbtlib.Compound()).snbt()
    container = root["Blocks"] if version == 3 else root
    palette = {int(v): BlockRecord.parse(k) for k, v in container["Palette"].items()}
    data = container["Data" if version == 3 else "BlockData"]
    indices, value, shift = [], 0, 0
    for byte in data:
        byte = int(byte) & 255
        value |= (byte & 127) << shift
        if byte & 128:
            shift += 7
            if shift > 28:
                raise ValueError("Invalid Sponge varint")
        else:
            indices.append(value)
            value, shift = 0, 0
    if shift or len(indices) != size[0] * size[1] * size[2]:
        raise ValueError("Sponge block array length mismatch")
    tiles = {}
    for tag in container.get("BlockEntities", []):
        p = tuple(int(v) for v in tag["Pos"])
        payload = nbtlib.Compound(tag.get("Data", tag))
        payload.pop("Pos", None)
        payload["id"] = tag["Id"]
        payload.pop("Id", None)
        for k, v in zip("xyz", p):
            payload[k] = nbtlib.Int(v)
        tiles[p] = payload.snbt()
    for i, idx in enumerate(indices):
        p = (i % size[0], i // (size[0] * size[2]), (i // size[0]) % size[2])
        b = palette[idx]
        if b.block_id != AIR:
            grid._set(tuple(p[j] + origin[j] for j in range(3)), BlockRecord(b.block_id, b.properties, tiles.get(p)))
    entities=[]
    for tag in root.get('Entities',[]):
        payload=nbtlib.Compound(tag.get('Data',tag))
        payload.pop('Id',None);payload['id']=tag['Id'];payload['Pos']=tag['Pos']
        entities.append(payload.snbt())
    grid.regions = [Region("Main", origin, size,entities)]
    return grid
