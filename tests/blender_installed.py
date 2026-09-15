"""Use a disposable BLENDER_USER_RESOURCES profile with installed enabled extension."""
import bpy
import json
import threading
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from bl_ext.user_default.mcblock_mine2blend.editor import blender_ui as ui, bridge

result = ui.execute('create_grid',{'name':'Installed extension test'})
gid=result['grid_id']
ui.execute('fill_region',{'grid_id':gid,'expected_revision':0,'minimum':[0,0,0],'maximum':[2,1,2],'state':'minecraft:stone'})
target=Path(__file__).resolve().parents[1]/'test-output/installed-export.litematic'
ui.execute('export_litematic',{'grid_id':gid,'path':str(target)})
assert target.is_file()
descriptor=bridge.start()['descriptor']
config=json.loads(Path(descriptor).read_text())
errors=[]
def client():
    try:
        req=Request(config['url'],data=json.dumps({'command':'get_summary','arguments':{'grid_id':gid}}).encode(),headers={'Authorization':'Bearer '+config['token']})
        with urlopen(req,timeout=10) as response:
            reply=json.load(response)
        assert reply['result']['block_count']==18,reply
        try:
            urlopen(Request(config['url'],data=b'{}'),timeout=5)
            raise AssertionError('Missing token accepted')
        except HTTPError as exc:
            assert exc.code==403
    except Exception as exc:
        errors.append(str(exc))
thread=threading.Thread(target=client);thread.start()
deadline=time.monotonic()+15
while thread.is_alive() and time.monotonic()<deadline:
    bridge.pump()
    time.sleep(0.02)
thread.join(timeout=1)
bridge.stop()
assert not thread.is_alive() and not errors,errors
print('INSTALLED_EXTENSION_AND_BRIDGE_OK')
