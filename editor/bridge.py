"""Loopback bridge: worker receives JSON; Blender timer performs all scene access."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from queue import Queue, Empty
import json
import secrets
import threading
import tempfile
import time
import os

SERVER = None
QUEUE = Queue(maxsize=32)
TOKEN = None
DESCRIPTOR = None

def descriptor_path():
    return Path(tempfile.gettempdir()) / f"mine2blend-{os.getpid()}.json"

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_POST(self):
        if self.path != "/command" or self.headers.get("Authorization") != "Bearer " + TOKEN:
            self.send_error(403)
            return
        try:
            length = int(self.headers.get("Content-Length", 0))
            if not 0 < length <= 8_000_000:
                raise ValueError("Request body must be 1..8MB")
            data = json.loads(self.rfile.read(length))
            item = {"request": data, "done": threading.Event(), "expires": time.monotonic()+120, "started": False}
            QUEUE.put_nowait(item)
            if not item["done"].wait(125):
                # Do not imply rollback if a running command times out.
                result = {"error": "Timeout; outcome unknown if started. Query grid revision before retrying."}
            else:
                result = item["result"]
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            self.send_error(400, str(exc))

def pump():
    if SERVER is None:
        return None
    try:
        item = QUEUE.get_nowait()
    except Empty:
        return 0.1
    try:
        if time.monotonic() > item["expires"]:
            raise ValueError("Request expired before execution")
        item["started"] = True
        from .blender_ui import execute
        request = item["request"]
        item["result"] = {"result": execute(request["command"], request.get("arguments", {}))}
    except Exception as exc:
        item["result"] = {"error": str(exc)}
    finally:
        item["done"].set()
    return 0.1

def start():
    global SERVER, TOKEN, DESCRIPTOR
    if SERVER is not None:
        return {"descriptor": str(DESCRIPTOR)}
    import bpy
    TOKEN = secrets.token_urlsafe(32)
    SERVER = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    SERVER.daemon_threads = True
    DESCRIPTOR = descriptor_path()
    DESCRIPTOR.write_text(json.dumps({"url": f"http://127.0.0.1:{SERVER.server_port}/command", "token": TOKEN}), encoding="utf-8")
    threading.Thread(target=SERVER.serve_forever, daemon=True).start()
    bpy.app.timers.register(pump, persistent=True)
    return {"descriptor": str(DESCRIPTOR)}

def stop():
    global SERVER
    if SERVER is not None:
        SERVER.shutdown()
        SERVER.server_close()
        SERVER = None
        import bpy
        if bpy.app.timers.is_registered(pump):
            bpy.app.timers.unregister(pump)
        DESCRIPTOR.unlink(missing_ok=True)
        while not QUEUE.empty():
            item = QUEUE.get_nowait()
            item["result"] = {"error": "Bridge stopped before execution"}
            item["done"].set()
    return {"stopped": True}
