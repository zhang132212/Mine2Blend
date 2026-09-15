import unittest,time,json
from editor.grid import BlockGrid,BlockRecord
from editor import persistence

class PersistenceTests(unittest.TestCase):
    def tearDown(self):persistence.stop()
    def test_immutable_background_snapshot(self):
        g=BlockGrid();g.apply([((0,0,0),BlockRecord.parse('minecraft:stone'))])
        persistence.schedule(1,[g]);g.apply([((1,0,0),BlockRecord.parse('minecraft:glass'))])
        deadline=time.monotonic()+5;value=None
        while value is None and time.monotonic()<deadline:
            value=persistence.collect(1);time.sleep(.01)
        self.assertEqual(len(json.loads(value)[0]['blocks']),1)
        persistence.schedule(1,[g]);self.assertIn(1,persistence.PENDING)
