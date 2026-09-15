"""Exercise actual SDK stdio initialization, schema listing, tool and error responses."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from editor.service import EditorService

class ProtocolTests(unittest.TestCase):
    def test_stdio(self):
        service=EditorService()
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args): pass
            def do_POST(self):
                assert self.headers['Authorization']=='Bearer test-token'
                data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                result=service.execute(data['command'],data['arguments'])
                body=json.dumps({'result':result}).encode()
                self.send_response(200); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        with tempfile.TemporaryDirectory() as folder:
            descriptor=Path(folder)/'bridge.json'
            descriptor.write_text(json.dumps({'url':f'http://127.0.0.1:{server.server_port}/command','token':'test-token'}))
            async def run():
                params=StdioServerParameters(command=sys.executable,args=['-m','editor.mcp_server','--descriptor',str(descriptor)])
                async with stdio_client(params) as (read,write):
                    async with ClientSession(read,write) as session:
                        await session.initialize()
                        tools=await session.list_tools()
                        self.assertGreaterEqual(len(tools.tools),20)
                        result=await session.call_tool('create_grid',{'name':'MCP test'})
                        self.assertFalse(result.is_error)
                        data=json.loads(result.content[0].text)
                        self.assertEqual(data['name'],'MCP test')
                        invalid=await session.call_tool('place_block',{'grid_id':data['grid_id'],'position':[0,0,0],'state':'minecraft:stone'})
                        self.assertTrue(invalid.is_error)
            try: asyncio.run(run())
            finally: server.shutdown(); server.server_close()

if __name__=='__main__': unittest.main()
