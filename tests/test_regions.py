import unittest
import nbtlib as n
from editor.grid import BlockGrid,BlockRecord,Region
from editor.regions import fit

class RegionTests(unittest.TestCase):
    def test_transform_scheduled_ticks(self):
        from editor.transforms import transform_metadata
        g=BlockGrid();g.regions=[Region('Main',(0,0,0),(10,10,10),[],{'PendingBlockTicks':'[{x:1,y:2,z:3,t:4L}]'})]
        metadata=transform_metadata(g,(0,0,0),(9,9,9),turns=1,move=True)
        tick=n.parse_nbt(metadata['regions'][0]['pending_ticks']['PendingBlockTicks'])[0]
        self.assertEqual([int(tick[a]) for a in 'xyz'],[-3,2,1]);self.assertIsInstance(tick['t'],n.Long)
    def test_overlapping_air_regions_rejected(self):
        from editor.regions import validate_disjoint
        with self.assertRaises(ValueError):validate_disjoint([Region('A',(0,0,0),(4,4,4)),Region('B',(5,0,0),(-4,4,4))])
        validate_disjoint([Region('A',(0,0,0),(4,4,4)),Region('B',(4,0,0),(4,4,4))])
    def test_fit_preserves_positions_and_ticks(self):
        g=BlockGrid();g.regions=[Region('Old',(10,2,-3),(2,2,2),['{id:"minecraft:pig",Pos:[0.5d,0d,0.5d]}'],{'PendingBlockTicks':'[{x:0,y:1,z:0,t:4}]'})]
        g._set((-5,0,0),BlockRecord.parse('minecraft:stone'))
        r=fit(g);self.assertEqual(r.origin,(-5,0,-3))
        entity=n.parse_nbt(r.entities[0]);self.assertEqual(list(entity['Pos']),[15.5,2,.5])
        tick=n.parse_nbt(r.pending_ticks['PendingBlockTicks'])[0];self.assertEqual(int(tick['x'])+r.origin[0],10)
