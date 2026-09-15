"""Run: python -m editor.mcp_server --descriptor <Blender bridge descriptor>."""
import argparse
import asyncio
import json
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from .service import TOOLS, tool_schema

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--descriptor", required=True)
    args = parser.parse_args()
    schemas = [*TOOLS, tool_schema("render_preview", "Rebuild dirty chunks; optionally render PNG in an isolated preview scene",{'path':{'type':'string'},'size':{'type':'integer','minimum':128,'maximum':4096}})]

    async def list_tools(ctx, params):
        return types.ListToolsResult(tools=[types.Tool(**t) for t in schemas])

    async def perform(name, arguments):
        import jsonschema
        schema = next((t for t in schemas if t["name"] == name), None)
        if schema is None:
            raise ValueError("Unknown tool")
        jsonschema.validate(arguments, schema["inputSchema"])
        def request():
            config = json.loads(Path(args.descriptor).read_text())
            url = urlparse(config["url"])
            if url.scheme != "http" or url.hostname != "127.0.0.1" or url.path != "/command":
                raise ValueError("Descriptor must target local Blender bridge")
            req = Request(config["url"], data=json.dumps({"command": name, "arguments": arguments}).encode(),
                          headers={"Authorization": "Bearer " + config["token"], "Content-Type": "application/json"})
            with urlopen(req, timeout=130) as response:
                result = json.load(response)
            if "error" in result:
                raise ValueError(result["error"])
            return result["result"]
        result = await asyncio.to_thread(request)
        return types.CallToolResult(content=[types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))])

    async def call_tool(ctx, params):
        try:
            return await perform(params.name, params.arguments or {})
        except Exception as exc:
            return types.CallToolResult(isError=True, content=[types.TextContent(type="text", text=str(exc))])

    from . import VERSION
    server = Server("mine2blend-editor", version=VERSION, on_list_tools=list_tools, on_call_tool=call_tool)

    async def run():
        async with stdio_server() as (read, write):
            await server.run(read, write, server.create_initialization_options())
    asyncio.run(run())

if __name__ == "__main__":
    main()
