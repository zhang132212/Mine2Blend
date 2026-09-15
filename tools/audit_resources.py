from pathlib import Path
import sys
import json
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from editor.render import ModelLibrary
from editor.registry import Registry
library,registry=ModelLibrary(),Registry()
missing_textures=set()
for name in registry.blocks:
    for quad in library.quads(registry.resolve('minecraft:'+name).state):
        if quad[2] not in library.uv:missing_textures.add(quad[2])
report={'resource_version':library.resource_version,'default_states_checked':len(registry.blocks),
        'fallback_count':len(library.missing),'fallback_blocks':sorted(library.missing),
        'special_block_types':len(library.special),'special_state_variants':sum(len(m['variants']) for m in library.special.values()),
        'missing_textures':sorted(missing_textures),
        'note':'Parsing smoke only; visual equivalence, animated portal shader and dynamic entity-NBT appearance require separate tests.'}
output=ROOT/'test-output/resource-audit.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='fallback_blocks'}))
