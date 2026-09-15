"""Structured, revision-aware commands shared by UI, blender-mcp and stdio MCP."""
from collections import Counter
from itertools import product
from .grid import BlockGrid, BlockRecord, Region, DIRECTIONS, position
from .registry import Registry
from . import formats
from .connections import reconcile, placement
from .transforms import transform_region

class EditorService:
    def __init__(self):
        self.grids = {}
        self.registry = Registry()

    def commit(self, grid, changes, expected, auto_connect=True,metadata=None):
        checked = [(position(p),b) for p,b in changes]
        if len(checked)>1_000_000: raise ValueError("Transaction too large")
        if auto_connect: checked=reconcile(grid,checked)
        return grid.apply(checked,expected,metadata)

    def fill(self,grid,lo,hi,block,expected,replace=None,auto_connect=True):
        lo,hi=position(lo),position(hi)
        volume=1
        for a,b in zip(lo,hi):
            if a>b: raise ValueError("Minimum exceeds maximum")
            volume*=b-a+1
        if volume>1_000_000: raise ValueError("Region too large")
        changes=((p,block) for p in product(*(range(a,b+1) for a,b in zip(lo,hi))) if replace is None or grid.blocks.get(p,BlockRecord("minecraft:air")).state==replace)
        return self.commit(grid,changes,expected,auto_connect)

    def execute(self, command, args):
        args = dict(args)
        if command == "list_blocks":
            return self.registry.search(**args)
        if command == "list_grids":
            return [g.summary() for g in self.grids.values()]
        if command == "create_grid":
            grid = BlockGrid(args.get("name", "Building"))
            self.grids[grid.id] = grid
            return grid.summary()
        if command in ("import_litematic", "import_schem"):
            grid = getattr(formats, command)(args["path"])
            self.grids[grid.id] = grid
            return grid.summary()
        grid = self.grids[args.pop("grid_id")]
        if command == "get_summary":
            return {**grid.summary(),"components":grid.components,"view":grid.view,"resource_packs":grid.resource_packs}
        if command=="get_components":return {"revision":grid.revision,"components":grid.components}
        if command == "get_block":
            p = position(args["position"])
            return {"position": p, **grid.blocks.get(p, BlockRecord("minecraft:air")).json(), "revision": grid.revision}
        if command == "query_region":
            lo, hi = position(args["minimum"]), position(args["maximum"])
            offset, limit = max(0, args.get("offset", 0)), max(1, min(args.get("limit", 200), 2000))
            rows = sorted((p, b) for p, b in grid.blocks.items() if all(a <= v <= z for a, v, z in zip(lo, p, hi)))
            return {"revision": grid.revision, "total": len(rows), "next_offset": offset + limit if offset + limit < len(rows) else None,
                    "materials": dict(Counter(b.state for p, b in rows)),
                    "layers": dict(Counter(p[1] for p, b in rows)),
                    "blocks": [{"position": p, **b.json()} for p, b in rows[offset:offset + limit]]}
        if command in ("export_litematic", "export_schem"):
            return getattr(formats, command)(grid, args["path"])
        if command == "validate_orientations":
            issues = []
            for p, b in grid.blocks.items():
                try:
                    self.registry.resolve(b.state)
                except ValueError as exc:
                    issues.append({"position": p, "message": str(exc)})
            return {"revision": grid.revision, "issues": issues[:1000], "total": len(issues),
                    "scope": "26.2 property validity; placement physics not simulated"}
        if command == "validate_support":
            issues = []
            for (x, y, z), b in grid.blocks.items():
                if b.block_id in ("minecraft:sand", "minecraft:red_sand", "minecraft:gravel") or b.block_id.endswith("_concrete_powder"):
                    if (x, y - 1, z) not in grid.blocks:
                        issues.append({"position": (x, y, z), "message": "Gravity block has air below"})
            return {"issues": issues[:1000], "total": len(issues), "scope": "Gravity-block heuristic only; no tick simulation"}
        expected = args.pop("expected_revision", None)
        if expected is None or expected != grid.revision:
            raise ValueError(f"Provide current expected_revision ({grid.revision})")
        if command in ("undo", "redo"):
            return grid.undo(command == "redo")
        auto_connect=args.pop("auto_connect",True)
        if command=="set_view":
            metadata=grid.metadata();metadata['view'].update(args['view'])
            return grid.apply([],expected,metadata)
        if command=="define_component":
            lo,hi=position(args['minimum']),position(args['maximum'])
            if any(a>b for a,b in zip(lo,hi)):raise ValueError('Invalid component bounds')
            metadata=grid.metadata();metadata['components'][args['name']]={'bounds':[lo,hi],'type':args.get('type','structure'),'description':args.get('description','')}
            return grid.apply([],expected,metadata)
        if command=="set_regions":
            metadata=grid.metadata();regions=[]
            for item in args['regions']:
                origin,size=position(item['origin']),position(item['size'])
                formats._check_volume(size)
                r=Region(item['name'],origin,size)
                existing=next((v for v in grid.regions if v.name==r.name),None)
                if existing:
                    if tuple(existing.origin)!=origin and (existing.entities or existing.pending_ticks):raise ValueError('Region contains entity/tick coordinates; use reframe_grid to change its origin')
                    r.entities=existing.entities;r.pending_ticks=existing.pending_ticks
                regions.append(r)
            if len({r.name for r in regions})!=len(regions):raise ValueError('Duplicate region names')
            for p in grid.blocks:
                if sum(r.contains(p) for r in regions)!=1:raise ValueError('Each block must belong to exactly one region')
            if any(r.entities or r.pending_ticks for r in grid.regions if r.name not in {s.name for s in regions}):raise ValueError('Cannot discard region entities/ticks')
            metadata['regions']=[r.__dict__ for r in regions]
            return grid.apply([],expected,metadata)
        if command=="recalculate_connections":
            return self.commit(grid,list(grid.blocks.items()),expected,True)
        if command=="transform_region":
            from .transforms import transform_metadata
            changes=list(transform_region(grid,**args))
            metadata=transform_metadata(grid,**args)
            return self.commit(grid,changes,expected,auto_connect,metadata)
        if command == "place_block":
            block = self.registry.resolve(args["state"], args.get("nbt"))
            p=position(args["position"])
            context=args.get("placement")
            if context is not None:
                oriented=placement(self.registry,args["state"],p,**context)
                block=BlockRecord(oriented.block_id,oriented.properties,block.nbt)
            changes=[(p,block)]
            existing=grid.blocks.get(p)
            if context is not None and existing and existing.block_id==block.block_id and block.block_id.endswith('_slab') and dict(existing.properties).get('type')!='double':
                props=dict(block.properties);props['type']='double';props['waterlogged']='false'
                block=BlockRecord(block.block_id,tuple(sorted(props.items())),block.nbt);changes=[(p,block)]
            if block.block_id=="minecraft:air" and existing and existing.block_id.endswith("_door"):
                dy=1 if dict(existing.properties).get("half")=="lower" else -1
                partner=(p[0],p[1]+dy,p[2])
                if grid.blocks.get(partner) and grid.blocks[partner].block_id==existing.block_id: changes.append((partner,None))
            if context is not None and block.block_id.endswith("_door"):
                props=dict(block.properties);props["half"]="lower"
                from .connections import left,right,add,solid
                facing=props['facing'];l=DIRECTIONS[left(facing)];r=DIRECTIONS[right(facing)]
                left_block=grid.blocks.get(add(p,l));right_block=grid.blocks.get(add(p,r))
                left_score=sum(solid(grid.blocks.get(add(add(p,l),(0,dy,0)))) for dy in (0,1))
                right_score=sum(solid(grid.blocks.get(add(add(p,r),(0,dy,0)))) for dy in (0,1))
                if left_block and left_block.block_id==block.block_id:props['hinge']='right'
                elif right_block and right_block.block_id==block.block_id:props['hinge']='left'
                elif left_score!=right_score:props['hinge']='right' if right_score>left_score else 'left'
                else:
                    dot=(context.get('hit_x',.5)-.5)*r[0]+(context.get('hit_z',.5)-.5)*r[2]
                    props['hinge']='right' if dot>0 else 'left'
                changes=[(p,BlockRecord(block.block_id,tuple(sorted(props.items())),block.nbt))]
                partner=(p[0],p[1]+1,p[2])
                if partner in grid.blocks: raise ValueError("Door upper position is occupied")
                props["half"]="upper"
                changes.append((partner,BlockRecord(block.block_id,tuple(sorted(props.items())))))
            return self.commit(grid,changes,expected,auto_connect)
        if command in ("fill_region", "replace_blocks"):
            block = self.registry.resolve(args["state"])
            replace = self.registry.resolve(args["replace"]).state if command == "replace_blocks" else None
            return self.fill(grid,args["minimum"], args["maximum"], block, expected, replace,auto_connect)
        if command == "apply_blocks":
            return self.commit(grid,[(r["position"], self.registry.resolve(r["state"], r.get("nbt"))) for r in args["blocks"]], expected,auto_connect)
        if command == "create_wall":
            a, b = position(args["minimum"]), position(args["maximum"])
            if a[0] != b[0] and a[2] != b[2]:
                raise ValueError("Wall must be aligned to X or Z")
            return self.fill(grid,a,b,self.registry.resolve(args["state"]),expected,auto_connect=auto_connect)
        if command == "create_roof":
            lo, hi = position(args["minimum"]), position(args["maximum"])
            if any(a > b for a, b in zip(lo, hi)) or (hi[0]-lo[0]+1)*(hi[2]-lo[2]+1) > 1_000_000:
                raise ValueError("Invalid or oversized roof bounds")
            # Stepped gable profile. State orientation remains explicitly controlled by caller.
            block = self.registry.resolve(args["state"])
            changes = []
            for x in range(lo[0], hi[0]+1):
                y = lo[1] + min(x-lo[0], hi[0]-x)
                if y > hi[1]:
                    raise ValueError("Roof ridge exceeds maximum Y")
                changes.extend(((x, y, z), block) for z in range(lo[2], hi[2]+1))
            return self.commit(grid,changes,expected,auto_connect)
        if command == "copy_region":
            lo, hi, offset = position(args["minimum"]), position(args["maximum"]), position(args["offset"])
            rows = [(p, b) for p, b in grid.blocks.items() if all(a <= v <= z for a, v, z in zip(lo, p, hi))]
            return self.commit(grid,[(tuple(p[i]+offset[i] for i in range(3)), b) for p, b in rows], expected,auto_connect)
        raise ValueError(f"Unknown command: {command}")

POSITION = {"type": "array", "items": {"type": "integer"}, "minItems": 3, "maxItems": 3}
STRING = {"type": "string"}
INTEGER = {"type": "integer", "minimum": 0}
def tool_schema(name, description, props=None, required=None, grid=True, write=False):
    props = dict(props or {})
    props['scene_id']={'type':'string','description':'Optional persistent scene ID from list_scenes; avoids active-window ambiguity'}
    props['request_id']={'type':'string','description':'Optional idempotency key; reuse for an identical retry'}
    required = list(required or [])
    if grid:
        props["grid_id"] = STRING
        required.append("grid_id")
    if write:
        props["expected_revision"] = INTEGER
        props["auto_connect"] = {"type":"boolean","default":True}
        required.append("expected_revision")
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": props, "required": required, "additionalProperties": False}}

TOOLS = [
    tool_schema('list_scenes','List persistent scene IDs for independent agent sessions',grid=False),
    tool_schema('start_io_job','Start background schematic IO; export uses immutable revision snapshot',{'command':{'enum':['import_litematic','import_schem','export_litematic','export_schem']},'path':STRING,'grid_id':STRING},['command','path'],grid=False),
    tool_schema('get_job_status','Get background IO state and result',{'job_id':STRING},['job_id'],grid=False),
    tool_schema('cancel_job','Cancel queued work or prevent in-flight export publication',{'job_id':STRING},['job_id'],grid=False),
    tool_schema('save_recovery','Write atomic compressed recovery snapshot',grid=False),
    tool_schema('recover_snapshot','Recover snapshot into new grids without overwriting current grids',{'path':STRING},['path'],grid=False),
    tool_schema('get_components','Read named architectural components and their exact bounds'),
    tool_schema('define_component','Name a wall/roof/floor/window/room for future structured edits',{'name':STRING,'minimum':POSITION,'maximum':POSITION,'type':STRING,'description':STRING},['name','minimum','maximum'],write=True),
    tool_schema('set_regions','Set explicit export regions; preserve matching region entities',{'regions':{'type':'array','minItems':1,'items':{'type':'object','properties':{'name':STRING,'origin':POSITION,'size':POSITION},'required':['name','origin','size'],'additionalProperties':False}}},['regions'],write=True),
    tool_schema('set_view','Change section/layers/isolation without deleting blocks',{'view':{'type':'object','properties':{'slice_min':{'type':['integer','null']},'slice_max':{'type':['integer','null']},'hidden_layers':{'type':'array','items':{'type':'integer'}},'isolate':{'type':['array','null'],'items':POSITION,'minItems':2,'maxItems':2},'xray':{'type':'boolean'},'biome':STRING},'additionalProperties':False}},['view'],write=True),
    tool_schema('load_resource_pack','Load local ZIP or folder resource pack with CTM and model overrides',{'path':STRING},['path'],write=True),
    tool_schema("recalculate_connections","Recalculate static neighbor connections in one undoable transaction",write=True),
    tool_schema("transform_region","Rotate/mirror/move/copy/array blocks and directional states",{"minimum":POSITION,"maximum":POSITION,"pivot":POSITION,"offset":POSITION,"turns":{"type":"integer"},"mirror":{"enum":["x","z"]},"move":{"type":"boolean"},"copies":{"type":"integer","minimum":1,"maximum":1000}},["minimum","maximum"],write=True),
    tool_schema("list_grids", "List building grids with bounds, materials and revisions", grid=False),
    tool_schema("create_grid", "Create a 26.2 grid using Minecraft XYZ, Y up", {"name": STRING}, grid=False),
    tool_schema("list_blocks", "Search verified 26.2 block IDs and allowed states", {"query": STRING, "offset": INTEGER, "limit": INTEGER}, grid=False),
    tool_schema("get_summary", "Building structure, bounds, region metadata, materials and revision"),
    tool_schema("get_block", "Read exact block state and typed SNBT", {"position": POSITION}, ["position"]),
    tool_schema("query_region", "Read bounded, paginated blocks with material and height-layer summaries", {"minimum": POSITION, "maximum": POSITION, "offset": INTEGER, "limit": INTEGER}, ["minimum", "maximum"]),
    tool_schema("place_block", "Place/delete one block atomically; use minecraft:air to delete", {"position": POSITION, "state": STRING, "nbt": STRING,"placement":{"type":"object","properties":{"clicked_face":{"enum":list(DIRECTIONS)},"look":{"enum":["north","east","south","west"]},**{'hit_'+axis:{'type':'number','minimum':0,'maximum':1} for axis in 'xyz'}},"additionalProperties":False}}, ["position", "state"], write=True),
    tool_schema("apply_blocks", "Atomic batch; all states validated before mutation", {"blocks": {"type": "array", "maxItems": 1000000, "items": {"type": "object", "properties": {"position": POSITION, "state": STRING, "nbt": STRING}, "required": ["position", "state"], "additionalProperties": False}}}, ["blocks"], write=True),
    *[tool_schema(n, d, {"minimum": POSITION, "maximum": POSITION, "state": STRING}, ["minimum", "maximum", "state"], write=True) for n, d in [
        ("fill_region", "Fill inclusive cuboid"), ("create_wall", "Create axis-aligned wall"), ("create_roof", "Create stepped gable roof along Z")]],
    tool_schema("replace_blocks", "Replace exact state in inclusive region", {"minimum": POSITION, "maximum": POSITION, "state": STRING, "replace": STRING}, ["minimum", "maximum", "state", "replace"], write=True),
    tool_schema("copy_region", "Copy non-air blocks by an integer offset", {"minimum": POSITION, "maximum": POSITION, "offset": POSITION}, ["minimum", "maximum", "offset"], write=True),
    *[tool_schema(n, f"{n} last block transaction", write=True) for n in ("undo", "redo")],
    *[tool_schema(n, n.replace("_", " ")) for n in ("validate_orientations", "validate_support")],
    *[tool_schema(n, n.replace("_", " "), {"path": STRING}, ["path"], grid=not n.startswith("import")) for n in ("import_litematic", "export_litematic", "import_schem", "export_schem")],
]
