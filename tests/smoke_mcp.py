"""Real MCP handshake and shared HTTP/emulator round trip."""
import asyncio
from pathlib import Path
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    params = StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).resolve().parents[1] / 'src/mcp_server.py')])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            names = {tool.name for tool in (await client.list_tools()).tools}
            assert {'capabilities', 'session_open', 'observe', 'step', 'touch_path', 'session_close'} <= names
            result = await client.call_tool('capabilities', {})
            assert not result.isError, result
            if '--read-only' in sys.argv:
                assert {'prepare_match','start_match','reset_match','delegate_player','stop_player','get_match_status'} <= names
                status = await client.call_tool('get_match_status', {})
                assert not status.isError,status
                teams = await client.call_tool('list_teams', {})
                assert not teams.isError,teams
                print('PASS MCP full tool discovery, capabilities, status and native team catalogue')
                return
            import json
            opened = await client.call_tool('session_open', {})
            assert not opened.isError, opened
            session_id = json.loads(opened.content[0].text)['session_id']
            from urllib.request import Request, urlopen
            with urlopen(Request('http://127.0.0.1:18765/api/set_control',
                    data=json.dumps({'session_id': session_id, 'owner': 'agent'}).encode(),
                    headers={'Content-Type': 'application/json'})) as response:
                assert json.load(response)['owner'] == 'agent'
            try:
                state = await client.call_tool('observe', {'session_id': session_id})
                assert not state.isError, state
                revision = json.loads(state.content[0].text)['revision']
                stepped = await client.call_tool('step', {'session_id': session_id,
                    'revision': revision, 'frames': 120, 'keys': []})
                assert not stepped.isError, stepped
                assert any(item.type == 'image' for item in stepped.content), stepped
            finally:
                closed = await client.call_tool('session_close', {'session_id': session_id})
                assert not closed.isError, closed
            print('PASS MCP initialization, discovery, shared session, step, image and close')


if __name__ == '__main__':
    asyncio.run(main())
