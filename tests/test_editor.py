import json
from pathlib import Path
import tempfile
import unittest
from editor.grid import BlockGrid, BlockRecord, Region, mc_to_blender, blender_to_mc
from editor.registry import Registry, matches
from editor.service import EditorService
from editor import formats
from editor.render import ModelLibrary

class GridTests(unittest.TestCase):
    def test_negative_chunk_boundary_and_undo(self):
        g = BlockGrid()
        stone = BlockRecord.parse("minecraft:stone")
        g.apply([((-1,0,0), stone)], 0)
        self.assertIn((-1,0,0), g.chunks)
        self.assertIn((0,0,0), g.dirty)
        g.undo(); self.assertFalse(g.blocks)
        g.undo(True); self.assertEqual(g.blocks[(-1,0,0)], stone)
        self.assertEqual(g.revision, 3)

    def test_atomic_failure(self):
        s = EditorService(); g = s.execute("create_grid", {})
        with self.assertRaises(ValueError):
            s.execute("apply_blocks", {"grid_id": g["grid_id"], "expected_revision": 0, "blocks": [
                {"position": [0,0,0], "state": "minecraft:stone"},
                {"position": [1,0,0], "state": "minecraft:oak_stairs[facing=up]"}]})
        self.assertFalse(s.grids[g["grid_id"]].blocks)

    def test_revision_and_volume(self):
        g = BlockGrid()
        with self.assertRaises(ValueError):
            g.apply([], 9)
        with self.assertRaises(ValueError):
            g.fill((0,0,0), (1000,1000,1000), None)

    def test_persistence_and_coordinates(self):
        g = BlockGrid(); g.apply([((4,8,-2), BlockRecord.parse("minecraft:chest", '{id:"minecraft:chest",Items:[],Count:1b}'))])
        g2 = BlockGrid.from_dict(json.loads(json.dumps(g.to_dict())))
        self.assertEqual(g.to_dict(), g2.to_dict())
        self.assertEqual(blender_to_mc(mc_to_blender((4,8,-2))), (4,8,-2))

    def test_registry_and_multipart(self):
        r = Registry()
        self.assertIn("facing=north", r.resolve("minecraft:oak_stairs").state)
        self.assertEqual(r.resolve("minecraft:cinnabar").block_id, "minecraft:cinnabar")
        self.assertTrue(matches({"OR": [{"north": "true"}, {"AND": [{"east": "true"}, {"waterlogged": "false"}]}]}, {"east":"true", "waterlogged":"false"}))
        self.assertFalse(matches({"north":"true"}, {"north":"false"}))

    def test_model_geometry_and_culling(self):
        lib = ModelLibrary()
        self.assertEqual(len(lib.quads("minecraft:stone")), 6)
        self.assertGreater(len(lib.quads(Registry().resolve("minecraft:oak_stairs").state)), 6)
        self.assertFalse(lib.opaque_cube(BlockRecord.parse("minecraft:glass")))

    def test_official_defaults_do_not_crash(self):
        lib, registry = ModelLibrary(), Registry()
        errors = []
        for name in registry.blocks:
            try:
                lib.quads(registry.resolve("minecraft:" + name).state)
            except Exception as exc:
                errors.append((name, str(exc)))
        self.assertFalse(errors, errors[:10])

class FormatTests(unittest.TestCase):
    def test_litematic_negative_size_multiregion_nbt(self):
        import nbtlib
        g = BlockGrid("Roundtrip")
        g.regions = [Region("Negative", (10,4,-3), (-3,2,2)), Region("Other", (-20,0,0), (2,2,2))]
        g.apply([((8,4,-3), Registry().resolve("minecraft:chest", '{id:"minecraft:chest",x:-2,y:0,z:0,Items:[{Slot:0b,id:"minecraft:stone",count:5}],custom:123L}')),
                 ((-20,0,0), Registry().resolve("minecraft:oak_stairs[facing=east]"))])
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "test.litematic")
            formats.export_litematic(g, p)
            actual = formats.import_litematic(p)
            self.assertEqual(actual.data_version, 4903)
            self.assertEqual({p:b.state for p,b in actual.blocks.items()}, {p:b.state for p,b in g.blocks.items()})
            self.assertIsInstance(nbtlib.parse_nbt(actual.blocks[(8,4,-3)].nbt)["custom"], nbtlib.Long)
            self.assertEqual([tuple(r.size) for r in actual.regions], [(-3,2,2),(2,2,2)])

    def test_schem_roundtrip(self):
        g = BlockGrid()
        g.apply([((-4,8,-3), Registry().resolve("minecraft:oak_stairs[facing=west]")), ((-2,8,-3), Registry().resolve("minecraft:stone"))])
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "test.schem")
            formats.export_schem(g, p)
            actual = formats.import_schem(p)
            self.assertEqual(actual.blocks, g.blocks)
            self.assertEqual(actual.data_version, 4903)

    def test_schem_block_entity(self):
        import nbtlib
        g = BlockGrid()
        g.apply([((3,5,7), Registry().resolve("minecraft:chest", '{id:"minecraft:chest",Items:[{Slot:0b,id:"minecraft:stone",count:3}]}'))])
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "chest.schem")
            formats.export_schem(g,p)
            actual = formats.import_schem(p)
            tag = nbtlib.parse_nbt(actual.blocks[(3,5,7)].nbt)
            self.assertIsInstance(tag['Items'][0]['Slot'], nbtlib.Byte)
            self.assertEqual(str(tag['id']), 'minecraft:chest')

if __name__ == "__main__":
    unittest.main()
