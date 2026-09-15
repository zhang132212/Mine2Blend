import unittest
import nbtlib as n
from editor.grid import BlockGrid,BlockRecord,Region
from editor.registry import Registry
from editor.clipboard import capture,paste

class ClipboardTests(unittest.TestCase):
    def test_snapshot_entities_and_typed_nbt_undo(self):
        source=BlockGrid();source._set((10,2,10),BlockRecord.parse('minecraft:chest','{id:"minecraft:chest",x:10,y:2,z:10,CustomName:"test"}'))
        source.regions=[Region('Original',(10,2,10),(2,2,2),['{id:"minecraft:pig",Pos:[0.5d,0d,0.5d],Health:20f}'],{'PendingBlockTicks':'[{x:0,y:0,z:0,t:5}]'})]
        source.components={'Room':{'bounds':[(10,2,10),(11,3,11)],'type':'room'}}
        data=capture(source,(10,2,10),(11,3,11));source.blocks.clear()
        target=BlockGrid();changes,meta=paste(target,data,(-5,4,8),Registry());target.apply(changes,0,meta)
        self.assertEqual(int(n.parse_nbt(target.blocks[-5,4,8].nbt)['x']),-5)
        r=target.regions[0];entity=n.parse_nbt(r.entities[0])
        self.assertEqual(float(entity['Pos'][0])+r.origin[0],-4.5)
        self.assertIsInstance(entity['Health'],n.Float)
        self.assertEqual(target.components['Room']['bounds'][0],(-5,4,8))
        target.undo();self.assertFalse(target.blocks);self.assertFalse(target.regions)
