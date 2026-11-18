"""Exercise the live shared service. Requires a running web server and Codex auth."""
import base64
import argparse
import json
from pathlib import Path
import time
from urllib.request import Request,urlopen

def call(op,**arguments):
    request=Request('http://127.0.0.1:8765/api/'+op,data=json.dumps(arguments).encode(),
                    headers={'Content-Type':'application/json'})
    with urlopen(request,timeout=140) as response:result=json.load(response)
    if 'error' in result:raise RuntimeError(result['error'])
    return result

def wait_job(timeout=900):
    deadline=time.monotonic()+timeout;last=''
    while time.monotonic()<deadline:
        state=call('status')
        if state['job']['message']!=last:
            last=state['job']['message'];print(last,flush=True)
        if state['job']['state']!='running':
            if state['job']['state']=='error':raise RuntimeError(last)
            return state
        time.sleep(1)
    call('stop_agent');raise TimeoutError('Delivery integration timed out')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-decisions',type=int,default=80)
    parser.add_argument('--timeout',type=int,default=1800)
    parser.add_argument('--require-result',action='store_true')
    args=parser.parse_args()
    folder=Path('build/delivery');folder.mkdir(parents=True,exist_ok=True)
    state=call('status');sid=state['session_id']
    if not sid or not state['fixture']:
        call('chat',message='Occulte contre Zeus');state=wait_job(180);sid=state['session_id']
    call('delegate_player',session_id=sid,max_decisions=args.max_decisions)
    state=wait_job(args.timeout)
    observation=call('observe',session_id=sid)
    (folder/'agent-final.png').write_bytes(base64.b64decode(observation.pop('image')))
    (folder/'agent-final.json').write_text(json.dumps({'status':state['job'],'observation':observation,
        'actions':state['agent_actions']},ensure_ascii=False,indent=2),encoding='utf-8')
    assert state['agent_actions']>0,'Agent never acted'
    assert state['owner']=='human','Control was not returned'
    if args.require_result:
        assert observation['match']['phase']=='result','Agent did not reach the native final result within its budget'
    first_identity=call('session_open',profile='arena')
    reset=call('reset_match',session_id=sid,revision=observation['revision'])
    assert reset['match']['native_counter']==4
    call('prepare_match',home=10,away=3,lines=[
        'Zeus accueille Occulte pour cette nouvelle rencontre.',
        'Nos ombres connaissent aussi les terrains adverses.',
        'Le ballon nous departagera.', 'Alors faisons parler nos passes.',
        'Chaque joueur compte dans cette equipe.', 'En place, le match commence !'])
    second=wait_job(30)
    assert second['session_id']==sid and second['fixture']['home']==10
    identity=call('session_open',profile='arena')
    assert identity['rom_sha256']==first_identity['rom_sha256']
    state=call('start_match',session_id=sid,revision=second['observation']['revision'])
    for _ in range(5):
        state=call('step',session_id=sid,revision=state['revision'],frames=120,keys=[])
    (folder/'second-dialogue.png').write_bytes(base64.b64decode(state.pop('image')))
    (folder/'second-fixture.json').write_text(json.dumps({'identity':identity,'state':state},indent=2),encoding='utf-8')
    print('PASS agent actions, returned control, same-session reset, reversed fixture and dynamic dialogue',flush=True)
