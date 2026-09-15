import tempfile,time,unittest
from pathlib import Path
from editor.grid import BlockGrid,BlockRecord
from editor import jobs,recovery

class JobsTests(unittest.TestCase):
    def test_export_snapshot_and_recovery(self):
        g=BlockGrid();g.apply([((0,0,0),BlockRecord.parse('minecraft:stone'))])
        with tempfile.TemporaryDirectory() as directory:
            job=jobs.start('export_litematic',str(Path(directory)/'a.litematic'),0,g)
            g.apply([((1,0,0),BlockRecord.parse('minecraft:glass'))])
            item=jobs.JOBS[job['job_id']]
            deadline=time.monotonic()+15
            while item.status in ('queued','running') and time.monotonic()<deadline:time.sleep(0.02)
            self.assertEqual(item.status,'completed',item.error)
            from editor.formats import import_litematic
            self.assertEqual(len(import_litematic(item.path).blocks),1)
            p=recovery.save([g],directory,'scene')
            restored=recovery.load(p)[0]
            self.assertEqual(restored.blocks,g.blocks)
            for _ in range(6):recovery.save([g],directory,'scene')
            self.assertEqual(len(list(Path(directory).glob('*.m2b.json.gz'))),5)
