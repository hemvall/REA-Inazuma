"""Shared match organiser, emulator and optional visual player."""
import base64
import json
import os
import threading
import time
import uuid
from game_session import GameSession, ROOT
from agent_runtime import LocalAgent, CodexAgent, AgentCancelled, BUTTONS
from arena_bridge import catalogue
from fast_policy import fast_decision
from player_state import text_ready


class Arena:
    def __init__(self):
        self.session = GameSession()
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.thread = None
        self.job = {'state':'idle','message':'Choisissez votre rencontre.'}
        self.latest = None
        self.fixture = None
        self.history = []
        settings = ROOT/'build/agents/settings.json'
        try:
            backend = json.loads(settings.read_text(encoding='utf-8')).get('backend', 'local')
        except (OSError, ValueError, AttributeError):
            backend = 'local'
        backend = os.environ.get('INAZUMIA_AGENT_BACKEND', backend)
        self.agent = (CodexAgent if backend == 'codex' else LocalAgent)(ROOT/'build/agents')

    def capabilities(self):
        built = (ROOT/'build/arena/profile.json').is_file()
        return {'application':'InazumIA','protocol':1,'emulation':True,'dynamic_match':built,'player_agent':self.agent.available(),
                'external_agent_control':True,'teams':[1,2,3,10], 'club':True, 'agent_backend':self.agent.backend, 'agent_model':self.agent.model,
                'player_mode':'hybrid','player_inputs':['rules','text','vision_fallback'],
                'reason':None if built else 'Construisez l’arène avec python src/prepare_arena.py.'}

    def select_agent(self, backend):
        if backend not in ('local', 'codex'):
            raise ValueError('Moteur attendu : local ou codex.')
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError('Arrêtez l’opération en cours avant de changer de moteur.')
            candidate = (LocalAgent if backend == 'local' else CodexAgent)(ROOT/'build/agents')
            settings = ROOT/'build/agents/settings.json'
            temporary = settings.with_suffix('.tmp')
            temporary.write_text(json.dumps({'backend':backend}),encoding='utf-8')
            temporary.replace(settings)
            self.agent = candidate
        return {'agent_backend':self.agent.backend, 'agent_model':self.agent.model}

    def list_teams(self):
        return [{k:v for k,v in row.items() if k not in ('header_hex','native_match_id')} for row in catalogue()]

    def update(self, **values):
        with self.lock:
            self.job.update(values)

    def launch(self, target, message):
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise ValueError('Une opération est déjà en cours. Arrêtez-la avant de continuer.')
            self.cancel = threading.Event()
            self.job = {'id':uuid.uuid4().hex,'state':'running','message':message,'started_at':time.time()}
            def run():
                try:
                    target()
                    if self.cancel.is_set():
                        self.update(state='cancelled',message='Opération arrêtée. Le jeu est en pause.')
                    elif self.job['state']=='running':
                        self.update(state='complete')
                except Exception as error:
                    self.update(state='cancelled' if self.cancel.is_set() else 'error',message=str(error))
                finally:
                    sid = self.session.session_id
                    if sid and self.session.owner=='agent':
                        self.session.set_control(sid,'human')
            self.thread = threading.Thread(target=run,daemon=True)
            self.thread.start()
            return dict(self.job)

    def checked(self, operation, **arguments):
        result = self.session.request(op=operation,**arguments)
        if 'error' in result:
            if self.latest and 'revision' in result:self.latest={**self.latest,'revision':result['revision']}
            raise ValueError(result['error'])
        self.latest = result
        if 'match' in result:
            native_fixture=result['match'].get('fixture')
            self.fixture=({**native_fixture,'status':'ready' if result['match']['phase']=='idle' else result['match']['phase']}
                          if native_fixture else None)
        return result

    def prepare(self, home, away, lines):
        if type(home) is not int or type(away) is not int or home not in (1,2,3,10) or away not in (1,2,3,10) or home==away:
            raise ValueError('Choisissez deux équipes distinctes du catalogue.')
        if not isinstance(lines,list) or len(lines)!=6 or any(not isinstance(line,str) or not 1<=len(line)<=100 for line in lines):
            raise ValueError('Six répliques de 1 à 100 caractères sont requises.')
        if self.cancel.is_set(): raise AgentCancelled()
        self.update(message='Ouverture de l’arène et préparation des équipes…')
        opened = self.session.open('arena',cancel=self.cancel)
        sid = opened['session_id']
        observation = self.checked('observe',session_id=sid)
        if observation['match']['phase']=='result':
            observation=self.checked('reset_match',session_id=sid,revision=observation['revision'],actor=self.session.owner)
        if observation['match']['native_counter'] != 4:
            raise ValueError('Réinitialisez la rencontre avant d’en préparer une autre.')
        observation = self.checked('prepare_match',session_id=sid,revision=observation['revision'],
                                   home=home,away=away,lines=lines,actor=self.session.owner)
        self.fixture = {'home':home,'away':away,'lines':lines,'status':'ready'}
        self.update(message='Rencontre prête. Lancez le dialogue puis jouez, ou confiez le match à l’agent.')
        return observation

    def chat(self, message):
        if not isinstance(message,str) or not 1<=len(message.strip())<=2000:
            raise ValueError('Message attendu : 1 à 2000 caractères')
        def organise():
            plan = self.agent.organise(message,self.list_teams(),self.cancel)
            if plan.get('home') is None or plan.get('away') is None:
                self.update(message=plan.get('message','Précisez les deux équipes.'))
                return
            teams = {row['id'] for row in self.list_teams()}
            if type(plan['home']) is not int or type(plan['away']) is not int or plan['home'] not in teams or plan['away'] not in teams or plan['home']==plan['away']:
                raise ValueError('L’organisateur a proposé une affiche invalide.')
            self.prepare(plan['home'],plan['away'],plan['lines'])
        return {'job':self.launch(organise,'L’organisateur prépare votre affiche et les dialogues…')}

    def status(self):
        if self.session.session_id and self.session.owner == 'human' and not (self.thread and self.thread.is_alive()):
            self.checked('observe', session_id=self.session.session_id, include_image=False)
        with self.lock:
            return {'job':dict(self.job),'session_id':self.session.session_id, 'profile':self.session.profile,
                    'owner':self.session.owner,'fixture':self.fixture,'observation':self.latest,
                    'agent_actions':len(self.history)}

    def delegate(self, session_id, max_decisions=400):
        if type(max_decisions) is not int or not 1<=max_decisions<=500:
            raise ValueError('Budget attendu : 1 à 500 décisions')
        if session_id != self.session.session_id: raise ValueError('Session inconnue')
        if self.session.profile not in ('arena','club') or not self.fixture:
            raise ValueError('Préparez d’abord une rencontre dans l’arène.')
        def player():
            self.checked('playback', session_id=session_id, running=False)
            self.session.set_control(session_id,'agent')
            self.history=[]
            self.update(rule_actions=0,text_calls=0,vision_calls=0,decision_ms=0)
            for index in range(max_decisions):
                if self.cancel.is_set():return
                observation = self.checked('observe',session_id=session_id,include_image=False)
                match = observation.get('match',{})
                if match.get('phase')=='result':
                    self.update(message='Match terminé. Le résultat final est affiché dans le jeu.' if match.get('result_source')=='native_final_screen' else
                                'Match terminé : victoire.' if match.get('result')=='victory' else
                                'Rencontre terminée, retour natif confirmé (code '+str(match.get('native_result'))+').')
                    return
                if match.get('native_counter')==4:
                    observation = self.checked('start_match',session_id=session_id,
                        revision=observation['revision'],actor='agent',include_image=False)
                if observation.get('match',{}).get('phase')=='dialogue':
                    observation=self.checked('step',session_id=session_id,revision=observation['revision'],
                        actor='agent',frames=3,keys=['A'],include_image=False)
                    self.checked('step',session_id=session_id,revision=observation['revision'],
                        actor='agent',frames=120,keys=[],include_image=False)
                    self.update(message='L’agent avance le dialogue natif des capitaines…',
                                decision_mode='rules',rule_actions=self.job['rule_actions']+1)
                    continue
                decision,observation = self.choose_action(observation,session_id,index,max_decisions)
                validate_decision(decision)
                if self.cancel.is_set():return
                self.history.append(decision)
                if decision['intent'] != 'act':
                    self.update(message=('Résultat visuel signalé : ' if decision['intent']=='finished' else 'Reprise demandée : ')+decision['reason'])
                    return
                arguments = {'session_id':session_id,'revision':observation['revision'],'actor':'agent','include_image':False}
                if decision['path']:
                    self.checked('touch_path',**arguments,points=decision['path'])
                else:
                    touch = decision['touch']
                    repetitions = 4 if (self.job.get('decision_mode')=='vision' and not touch
                                        and not decision['keys'] and decision['frames']==120) else 1
                    for _ in range(repetitions):
                        if self.cancel.is_set():return
                        result = self.checked('step',**arguments,frames=decision['frames'],keys=decision['keys'],
                                              touch=[touch['x'],touch['y']] if touch else None)
                        arguments['revision']=result['revision']
                        if result.get('match',{}).get('phase')=='result':break
                # Let the native menu transition settle locally. Calling a model
                # on the intervening fade wastes a decision and can repeat a click.
                # 120 frames is the bounded interval verified on saved native states.
                if (self.job.get('decision_mode') in ('rules','text')
                        and (decision['touch'] is not None or decision['keys'] or decision['path'])
                        and self.latest.get('match',{}).get('phase')!='result'):
                    self.checked('step',session_id=session_id,revision=self.latest['revision'],actor='agent',
                                 frames=120,keys=[],include_image=False)
                self.update(message=decision['reason'])
            self.update(message='Budget de décisions atteint. Le jeu est en pause ; reprenez ou relancez l’agent.')
        return {'job':self.launch(player,'Démarrage de l’agent hybride : règles, texte, vision en secours…')}

    def choose_action(self, observation, session_id, index, maximum):
        """Prefer local rules, then legal text choices; request pixels only as fallback."""
        started = time.monotonic()
        state = observation.get('match',{})
        decision = fast_decision(state,self.history)
        mode = 'rules' if decision is not None else ('text' if text_ready(state) else 'vision')
        self.update(decision_mode=mode,decision_started_at=time.time())
        if decision is None:
            image = None
            if mode == 'vision':
                visual = self.checked('observe',session_id=session_id,include_image=True)
                # No frames may advance between the compact and visual observations.
                if any(visual.get(key) != observation.get(key) for key in ('revision','frame')):
                    raise ValueError('Observation modifiée pendant la décision ; reprenez l’agent.')
                observation = visual
                state = observation.get('match',{})
                image = ROOT/'build/agents'/f'{session_id}-current.png'
                image.write_bytes(base64.b64decode(observation['image']))
            choosing = f'L’agent choisit son action ({index+1}/{maximum}, '+('texte' if mode=='text' else 'vision en secours')+')'
            self.update(message=choosing+'…')
            feedback_done = threading.Event()
            def feedback():
                while not feedback_done.wait(1):
                    self.update(message=choosing+f' · {int(time.monotonic()-started)} s (jeu en pause)…')
            feedback_thread = threading.Thread(target=feedback,daemon=True)
            feedback_thread.start()
            try:
                decision = self.agent.play(image,state,self.history,self.cancel)
            finally:
                feedback_done.set()
                feedback_thread.join()
        validate_decision(decision)
        elapsed = round((time.monotonic()-started)*1000,2)
        counter = {'rules':'rule_actions','text':'text_calls','vision':'vision_calls'}[mode]
        self.update(decision_ms=elapsed,**{counter:self.job.get(counter,0)+1})
        folder = ROOT/'build/agents'
        folder.mkdir(parents=True,exist_ok=True)
        with (folder/f'{session_id}-decisions.jsonl').open('a',encoding='utf-8') as log:
            log.write(json.dumps({'mode':mode,'milliseconds':elapsed,'frame':observation.get('frame'),
                                  'screen':state.get('screen',{}).get('name'),'action':decision},ensure_ascii=False)+'\n')
        return decision,observation

    def stop(self):
        self.cancel.set()
        if self.session.session_id and self.session.owner=='agent':
            self.session.set_control(self.session.session_id,'human')
        return {'stopping':True}

    def call(self, operation, arguments):
        if operation=='open_club':
            if arguments: raise ValueError('Aucun argument attendu')
            if self.session.session_id: raise ValueError('Fermez la session actuelle avant d’entrer dans le local.')
            def enter():
                opened = self.session.open('club', cancel=self.cancel)
                self.checked('observe', session_id=opened['session_id'])
                self.update(message='Parlez au coach dans le local : A ou écran tactile. Non propose l’affiche suivante. Après le match, A revient au local.')
            return {'job':self.launch(enter, 'Ouverture du local du club…')}
        if operation=='select_agent':return self.select_agent(**arguments)
        if operation=='capabilities':return self.capabilities()
        if operation=='list_teams':return {'teams':self.list_teams()}
        if operation=='status':return self.status()
        if operation=='chat':return self.chat(**arguments)
        if operation=='stop_agent':return self.stop()
        if operation=='delegate_player':return self.delegate(**arguments)
        if operation=='prepare_match':
            home,away,lines=arguments['home'],arguments['away'],arguments['lines']
            return {'job':self.launch(lambda:self.prepare(home,away,lines),'Préparation dynamique…')}
        if operation=='session_open':return self.session.open(**arguments)
        if operation=='session_close':
            if self.thread and self.thread.is_alive():raise ValueError('Arrêtez d’abord l’opération en cours.')
            if arguments.get('session_id')!=self.session.session_id:raise ValueError('Session inconnue')
            self.session.close();self.latest=None;self.fixture=None
            return {'closed':True}
        if operation=='set_control':
            if arguments.get('owner')=='human' and self.thread and self.thread.is_alive():self.cancel.set()
            return self.session.set_control(**arguments)
        if operation in ('observe','step','touch_path','checkpoint_save','checkpoint_load','start_match','reset_match','playback'):
            result=self.checked(operation,**arguments)
            if operation=='reset_match':self.fixture=None
            return result
        raise ValueError('Opération inconnue')


def validate_decision(value):
    if not isinstance(value,dict) or set(value)!={'intent','reason','frames','keys','touch','path'}:
        raise ValueError('Invalid agent action schema')
    if value['intent'] not in ('act','finished','blocked') or not isinstance(value['reason'],str):raise ValueError('Invalid agent intent')
    if type(value['frames']) is not int or not 1<=value['frames']<=120:raise ValueError('Invalid agent frame budget')
    keys=value['keys']
    if not isinstance(keys,list) or len(keys)>12 or any(k not in BUTTONS for k in keys):raise ValueError('Invalid agent buttons')
    touch=value['touch']
    if touch is not None:
        if not isinstance(touch,dict) or set(touch)!={'x','y'}:raise ValueError('Invalid agent touch')
        validate_point(touch)
    path=value['path']
    if not isinstance(path,list) or len(path)>30:raise ValueError('Invalid agent path')
    for point in path:
        if not isinstance(point,dict) or set(point)!={'x','y','frames'}:raise ValueError('Invalid path point')
        validate_point(point)
        if type(point['frames']) is not int or not 1<=point['frames']<=120:raise ValueError('Invalid path duration')
    if sum(p['frames'] for p in path)>120:raise ValueError('Agent path exceeds 120 frames')


def validate_point(point):
    if type(point['x']) is not int or type(point['y']) is not int or not 0<=point['x']<=255 or not 0<=point['y']<=191:
        raise ValueError('Invalid DS coordinates')
