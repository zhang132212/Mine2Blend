import unittest,tempfile
from pathlib import Path
import nbtlib as n
from editor.grid import BlockGrid,BlockRecord,Region
from editor import formats

class EntityFormats(unittest.TestCase):
    def test_entity_transform_atomic_undo(self):
        from editor.service import EditorService
        s=EditorService();g=BlockGrid();s.grids[g.id]=g
        g._set((1,0,0),BlockRecord.parse('minecraft:stone'))
        g.regions=[Region('Main',(0,0,0),(5,5,5),['{id:"minecraft:armor_stand",Pos:[1.5d,0d,0.5d],Rotation:[0f,0f]}'])]
        g.components={'pillar':{'bounds':[(1,0,0),(1,0,0)],'type':'pillar'}}
        before=g.to_dict()
        s.execute('transform_region',{'grid_id':g.id,'expected_revision':0,'minimum':[1,0,0],'maximum':[1,1,0],'turns':1,'move':True})
        entity=n.parse_nbt(g.regions[0].entities[0])
        self.assertEqual(list(entity['Pos']),[.5,0,1.5]);self.assertEqual(entity['Rotation'][0],90)
        self.assertIn((0,0,1),g.blocks)
        g.undo();after=g.to_dict();after['revision']=before['revision'];self.assertEqual(after,before)
    def test_sponge_entities_and_metadata(self):
        g=BlockGrid();g._set((-3,4,5),BlockRecord.parse('minecraft:stone'))
        g.regions=[Region('Main',(-3,4,5),(1,1,1),['{id:"minecraft:armor_stand",Pos:[0.5d,1d,0.5d],Rotation:[30f,0f],Invisible:1b,CustomName:"Test"}'])]
        g.source_metadata['schem']='{Author:"Builder",Custom:23L}'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'entity.schem';formats.export_schem(g,p);result=formats.import_schem(p)
        self.assertEqual(result.blocks,g.blocks)
        entity=n.parse_nbt(result.regions[0].entities[0])
        self.assertEqual(entity,n.parse_nbt(g.regions[0].entities[0]))
        self.assertIsInstance(entity['Invisible'],n.Byte)
        self.assertEqual(n.parse_nbt(result.source_metadata['schem'])['Custom'],23)
    def test_sponge_v3_entity_wrapper(self):
        root=n.Compound(Version=n.Int(3),DataVersion=n.Int(4903),Width=n.Short(1),Height=n.Short(1),Length=n.Short(1),Offset=n.IntArray([4,5,6]),Blocks=n.Compound(Palette=n.Compound({'minecraft:stone':n.Int(0)}),Data=n.ByteArray([0])),Entities=n.List[n.Compound]([n.Compound(Id=n.String('minecraft:pig'),Pos=n.List[n.Double]([.5,0,.5]),Data=n.Compound(Age=n.Int(-10)))]))
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'v3.schem';n.File({'Schematic':root},gzipped=True).save(p);result=formats.import_schem(p)
        entity=n.parse_nbt(result.regions[0].entities[0]);self.assertEqual(entity['Age'],-10);self.assertEqual(entity['id'],'minecraft:pig')
