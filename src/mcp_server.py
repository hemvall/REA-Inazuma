"""MCP adapter to the shared running web service; requires mcp>=1.26,<2."""
import base64
import json
from urllib.request import Request, urlopen
from mcp.server.fastmcp import FastMCP, Image

mcp = FastMCP('InazumIA')


def call(operation, **arguments):
    request = Request('http://127.0.0.1:8765/api/' + operation,
                      data=json.dumps(arguments).encode(),
                      headers={'Content-Type': 'application/json'}, method='POST')
    with urlopen(request, timeout=130) as response:
        result = json.load(response)
    if 'error' in result:
        raise ValueError(result.get('reason', result['error']))
    return result


def observation(result):
    encoded = result.pop('image', None)
    content = [json.dumps(result)]
    if encoded:
        content.append(Image(data=base64.b64decode(encoded), format='png'))
    return content


@mcp.tool()
def capabilities() -> dict:
    """Return actual capabilities, including unavailable ROM features."""
    return call('capabilities')


@mcp.tool()
def session_open(profile: str = 'arena') -> dict:
    """Open the local scenario in the shared browser session, initially paused."""
    return call('session_open',profile=profile)


@mcp.tool()
def list_teams() -> dict:
    """List the supported ROM teams, native captains and rosters."""
    return call('list_teams')


@mcp.tool()
def organise_match(message: str) -> dict:
    """Ask the organiser agent to resolve teams and create six captain lines; returns a job ID."""
    return call('chat',message=message)


@mcp.tool()
def prepare_match(home: int, away: int, lines: list[str]) -> dict:
    """Dynamically prepare a supported fixture and six alternating captain lines; returns a job ID."""
    return call('prepare_match',home=home,away=away,lines=lines)


@mcp.tool()
def get_match_status() -> dict:
    """Read background job, control owner, fixture and native phase."""
    result=call('status')
    if result.get('observation'):result['observation'].pop('image',None)
    return result


@mcp.tool()
def start_match(session_id: str, revision: int) -> list:
    """Dismiss the arena waiting dialogue and begin the prepared captain exchange."""
    return observation(call('start_match',session_id=session_id,revision=revision,actor='agent'))


@mcp.tool()
def reset_match(session_id: str, revision: int) -> list:
    """Restore this worker's pristine arena checkpoint; does not reload or rebuild the ROM."""
    return observation(call('reset_match',session_id=session_id,revision=revision,actor='agent'))


@mcp.tool()
def delegate_player(session_id: str, max_decisions: int = 400) -> dict:
    """Start the deterministic emulator pilot for a bounded number of decisions."""
    return call('delegate_player',session_id=session_id,max_decisions=max_decisions)


@mcp.tool()
def stop_player() -> dict:
    """Cancel the agent's pending decision, leave emulation paused and return manual control."""
    return call('stop_agent')


@mcp.tool()
def observe(session_id: str) -> list:
    """Read revision and both DS screens without advancing frames."""
    return observation(call('observe', session_id=session_id))


@mcp.tool()
def observe_match(session_id: str) -> dict:
    """Read the compact match state and legal action IDs without a screenshot."""
    return call('observe_match', session_id=session_id)


@mcp.tool()
def apply_match_action(session_id: str, revision: int, frame: int, action_id: str) -> dict:
    """Execute a legal action from the latest match observation under agent control."""
    return call('apply_match_action', session_id=session_id, revision=revision,
                frame=frame, action_id=action_id, actor='agent')


@mcp.tool()
def advance_match(session_id: str, revision: int, frames: int) -> dict:
    """Advance 1–120 frames without input under agent control."""
    return call('advance_match', session_id=session_id, revision=revision, frames=frames, actor='agent')


@mcp.tool()
def step(session_id: str, revision: int, frames: int, keys: list[str], touch: list[int] | None = None) -> list:
    """Advance up to 120 frames; freeze on the native final screen. B then restores the arena checkpoint."""
    return observation(call('step', session_id=session_id, revision=revision,
                            frames=frames, keys=keys, touch=touch, actor='agent'))


@mcp.tool()
def touch_path(session_id: str, revision: int, points: list[dict]) -> list:
    """Execute a continuous path of x/y/frames segments, at most 120 frames total."""
    return observation(call('touch_path', session_id=session_id, revision=revision, points=points, actor='agent'))


@mcp.tool()
def checkpoint_save(session_id: str) -> dict:
    """Save an ephemeral checkpoint in this worker (maximum eight)."""
    return call('checkpoint_save', session_id=session_id, actor='agent')


@mcp.tool()
def checkpoint_load(session_id: str, checkpoint_id: str, revision: int) -> list:
    """Restore a checkpoint belonging to the current ROM/core session."""
    return observation(call('checkpoint_load', session_id=session_id,
                            checkpoint_id=checkpoint_id, revision=revision, actor='agent'))


@mcp.tool()
def session_close(session_id: str) -> dict:
    """Close the shared session and release the emulator."""
    return call('session_close', session_id=session_id)


if __name__ == '__main__':
    mcp.run(transport='stdio')
