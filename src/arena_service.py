"""Shared match organiser, emulator and optional visual player."""
import base64
import json
import os
import threading
import time
import uuid
from game_session import GameSession, ROOT
from agent_runtime import LocalAgent, CodexAgent, AgentCancelled, InvalidAgentResponse, BUTTONS
from arena_bridge import NATIVE_MATCH_BY_TEAM, catalogue
from fast_policy import fast_decision
from player_state import text_ready
from recruitment import propose
from recruitment_rom import FIRST_RECRUIT_ID
from recruitment_store import RecruitmentStore


class Arena:
    def __init__(self, *, stream_video=True, local_only=False, recruit_in_club=False):
        self.session = GameSession(stream_video=stream_video, recruit_in_club=recruit_in_club)
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.thread = None
        self.job = {'state':'idle','message':'Choisissez votre rencontre.'}
        self.latest = None
        self.fixture = None
        self.history = []
        self.recruitment = None
        self.local_only = local_only
        if local_only:
            self.agent = LocalAgent(ROOT/'build/agents')
            return
        settings = ROOT/'build/agents/settings.json'
        try:
            backend = json.loads(settings.read_text(encoding='utf-8')).get('backend', 'local')
        except (OSError, ValueError, AttributeError):
            backend = 'local'
        backend = os.environ.get('INAZUMIA_AGENT_BACKEND', backend)
        self.agent = (CodexAgent if backend == 'codex' else LocalAgent)(ROOT/'build/agents')

    def capabilities(self):
        built = (ROOT/'build/arena/profile.json').is_file()
        return {'application':'InazumIA','protocol':1,'emulation':True,'dynamic_match':built,'player_agent':built,
                'external_agent_control':True,'teams':list(NATIVE_MATCH_BY_TEAM), 'club':True, 'agent_backend':self.agent.backend, 'agent_model':self.agent.model,
                'player_mode':'deterministic','player_modes':['deterministic','ai'],'player_inputs':['rules','text'],
                'reason':None if built else 'Construisez l’arène avec python src/prepare_arena.py.'}

    def select_agent(self, backend):
        if self.local_only:
            raise ValueError('Le salon utilise LM Studio.')
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
        return [{k:v for k,v in row.items() if k not in ('header_hex','native_match_id','roster_names')} for row in catalogue()]

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
        if (type(home) is not int or type(away) is not int or home == away
                or home not in NATIVE_MATCH_BY_TEAM or away not in NATIVE_MATCH_BY_TEAM):
            raise ValueError('Choisissez deux équipes distinctes du catalogue.')
        if not isinstance(lines,list) or len(lines)!=6 or any(not isinstance(line,str) or not 1<=len(line)<=100 for line in lines):
            raise ValueError('Six répliques de 1 à 100 caractères sont requises.')
        if self.cancel.is_set(): raise AgentCancelled()
        self.update(message='Ouverture de l’arène et préparation des équipes…')
        recruited = self.recruited_players() or None
        if (self.session.session_id and self.session.profile == 'arena'
                and self.session.arena_recruitment != recruited):
            existing = self.checked('observe', session_id=self.session.session_id, include_image=False)
            if existing['match']['phase'] not in ('idle', 'result'):
                raise ValueError('Réinitialisez la rencontre avant d’en préparer une autre.')
        opened = self.session.open('arena', cancel=self.cancel, arena_recruitment=recruited)
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
                    'agent_actions':len(self.history),
                    'recruitment': self.recruitment,
                    'recruited_players': self.recruited_players()}

    def recruited_players(self):
        if self.session.recruit_in_club:
            return RecruitmentStore.read(self.session.recruitment_save)[0]
        return []

    def recruitment_context(self, session_id):
        if not self.session.recruit_in_club:
            raise ValueError('Ouvre InazumIA depuis le lanceur web.')
        if session_id != self.session.session_id:
            raise ValueError('Session périmée. Actualise la fiche.')
        if self.session.owner != 'human' or (self.thread and self.thread.is_alive()):
            raise ValueError('Attends la fin de l’opération en cours.')
        if session_id is None:
            return None
        observation = self.checked('observe', session_id=session_id, include_image=False)
        phase = observation['match']['phase']
        if ((self.session.profile == 'club' and phase == 'club')
                or (self.session.profile == 'arena' and phase in ('idle', 'result'))):
            return observation
        raise ValueError('Le recrutement est disponible hors match.')

    def recruitment_turn(self, session_id, message):
        if not isinstance(message, str) or not 1 <= len(message.strip()) <= 2000:
            raise ValueError('Saisis une demande de recrutement de 1 à 2000 caractères.')
        with self.lock:
            observation = self.recruitment_context(session_id)
            recruited = self.recruited_players()
            current = self.recruitment or {'history': []}
            message = message.strip()
            party = observation['match']['party_units'] if self.session.profile == 'club' and observation else []

            def discuss():
                answer, draft = propose(ROOT/'rom/original.nds', catalogue(), party, message)
                if draft:
                    try:
                        RecruitmentStore.check_available(recruited, draft)
                    except ValueError as error:
                        answer, draft = str(error), None
                with self.lock:
                    if self.cancel.is_set():
                        return
                    self.recruitment = {
                        'version': uuid.uuid4().hex,
                        'history': [*current['history'][-18:], {'role': 'joueur', 'message': message},
                                    {'role': 'coach', 'message': answer}],
                        'draft': draft,
                    }
                    self.update(message='Réponse de la recruteuse disponible.')

            return {'job': self.launch(discuss, 'Celia examine ta demande…')}

    def recruitment_cancel(self, session_id):
        with self.lock:
            self.recruitment_context(session_id)
            self.recruitment = None
            return {'cancelled': True}

    def recruitment_confirm(self, session_id, version, revision=None):
        with self.lock:
            current = self.recruitment
            if (not current or not current['draft'] or current['version'] != version
                    or self.session.session_id != session_id):
                raise ValueError('Cette version de la fiche est périmée.')
            if current.get('result') is not None:
                return current['result']
            observation = self.recruitment_context(session_id)
            draft = current['draft']
            recruited = self.recruited_players()
            RecruitmentStore.check_available(recruited, draft)
            result = {'unit': FIRST_RECRUIT_ID + len(recruited), 'draft': draft}
            if observation and self.session.profile == 'club' and not recruited:
                if type(revision) is not int or observation['revision'] != revision:
                    raise ValueError('État du Club périmé. Actualise la fiche.')
                observation = self.checked('confirm_recruitment', session_id=session_id, revision=revision,
                                           draft=draft, include_image=False)
                if observation['recruited'] != draft or FIRST_RECRUIT_ID not in observation['match']['party_units']:
                    raise ValueError('Inscription native non confirmée.')
                result['observation'] = observation
            else:
                RecruitmentStore.reserve(self.session.recruitment_save, draft)
            current['result'] = result
            return result

    def delegate(self, session_id, max_decisions=400, mode='deterministic'):
        if mode not in ('deterministic', 'ai'):
            raise ValueError('Mode attendu : deterministic ou ai.')
        if type(max_decisions) is not int or not 1<=max_decisions<=500:
            raise ValueError('Budget attendu : 1 à 500 décisions')
        if session_id != self.session.session_id: raise ValueError('Session inconnue')
        if self.session.profile not in ('arena','club','club_web') or not self.fixture:
            raise ValueError('Préparez d’abord une rencontre dans l’arène.')
        def player():
            with self.lock:
                if self.cancel.is_set():
                    return
                self.session.set_control(session_id, 'agent')
                self.checked('playback', session_id=session_id, actor='agent', running=False,
                             include_image=False)
                arguments = {'session_id': session_id, 'actor': 'agent', 'include_image': False}
                observation = self.checked('observe_match', **arguments)['match_observation']
            self.history = []
            self.update(pilot_mode=mode, rule_actions=0, text_calls=0, vision_calls=0,
                        decision_mode='rules', fallback_count=0, animation_seconds=0,
                        rejected_commands=0, max_action_gap_seconds=None,
                        max_input_gap_seconds=None)
            folder = ROOT / 'build/agents'
            folder.mkdir(parents=True, exist_ok=True)
            stalled_frames = 0
            rejected = 0
            last_action = None
            advance_since_action = 0
            repeated = 0
            cooldown = 0
            goal_animation_until = 0
            with (folder / f"{self.job['id']}-match.jsonl").open('a', encoding='utf-8') as log:
                def record(event, **fields):
                    log.write(json.dumps({'event': event, 'monotonic': time.monotonic(), **fields},
                                         ensure_ascii=False) + '\n')
                    log.flush()

                def finish(reason, **fields):
                    metrics = {key: self.job[key] for key in ('rule_actions', 'text_calls', 'vision_calls',
                               'fallback_count', 'animation_seconds', 'rejected_commands',
                               'max_action_gap_seconds', 'max_input_gap_seconds')}
                    record('summary', reason=reason, pilot_mode=mode, **metrics, **fields)

                while len(self.history) < max_decisions and not self.cancel.is_set():
                    record('observation', **observation)
                    phase = observation['phase']
                    frame = observation['frame']
                    if phase == 'result':
                        finish('result', observation=observation)
                        self.update(message='Match terminé. Résultat confirmé par l’émulateur.',
                                    result=observation)
                        return
                    actions = observation['legal_actions']
                    offered = actions[0]['id'] if actions else None
                    action_id = None if cooldown else offered
                    dialogue = phase == 'dialogue' or offered == 'dialogue.continue'
                    repeat_limit = 24 if dialogue else 3
                    waiting_for_transition = (observation['screen'] == 'goal_replay_video'
                                              or (observation['screen'] == 'scoreboard_transition'
                                                  and self.history[-1:] == ['replay.continue'])
                                              or frame < goal_animation_until)
                    frame_limit = 3600 if dialogue or waiting_for_transition else 900
                    if stalled_frames >= frame_limit or (repeated >= repeat_limit and not cooldown):
                        screen = observation['screen']
                        cause = ('no_legal_action' if offered is None else
                                 'repeated_action' if repeated >= repeat_limit else 'no_progress')
                        detail = ('Aucune action reconnue' if offered is None else
                                  f'{offered} ne fait pas progresser le match')
                        message = f'{detail} en phase {phase} ({screen}), frame {frame}. Reprenez la main.'
                        finish('blocked', phase=phase, screen=screen, frame=frame, cause=cause,
                               action_id=offered, stalled_frames=stalled_frames, repeated=repeated,
                               clock=observation['clock'], possession=observation['possession'])
                        self.update(state='blocked', message=message, cause=cause)
                        return

                    revision = observation['revision']
                    started = time.monotonic()
                    decision_mode = 'rules'
                    fallback = None
                    try:
                        choices = actions
                        if self.history[-1:] == ['duel.special.back']:
                            choices = [action for action in actions if action['id'] != 'duel.special.open']
                        if action_id and mode == 'ai' and len(choices) > 1:
                            self.update(text_calls=self.job['text_calls'] + 1,
                                        message='L’agent choisit son action…')
                            try:
                                choice = self.agent.decide_match_action(
                                    {**observation, 'legal_actions': choices}, self.cancel)
                                if (not isinstance(choice, dict) or set(choice) != {'action_id'}
                                        or choice['action_id'] not in [action['id'] for action in choices]):
                                    raise ValueError('Choix hors des actions disponibles.')
                            except TimeoutError:
                                fallback = 'timeout'
                            except (ValueError, InvalidAgentResponse):
                                fallback = 'invalid_response'
                            except (OSError, RuntimeError):
                                fallback = 'model_unavailable'
                            else:
                                action_id = choice['action_id']
                                decision_mode = 'text'
                        decision_ms = round((time.monotonic() - started) * 1000, 2)
                        with self.lock:
                            if self.cancel.is_set() or self.session.owner != 'agent':
                                raise AgentCancelled()
                            if action_id:
                                self.update(decision_mode=decision_mode, decision_ms=decision_ms,
                                            fallback_count=self.job['fallback_count'] + int(fallback is not None))
                                record('decision', pilot_mode=mode, mode=decision_mode, action_id=action_id,
                                       milliseconds=decision_ms, fallback=fallback, frame=frame, revision=revision)
                                result = self.checked('apply_match_action', **arguments, revision=revision,
                                                      frame=frame, action_id=action_id, realtime=mode == 'ai')
                            else:
                                result = self.checked('advance_match', **arguments, revision=revision,
                                                      frames=60, realtime=mode == 'ai')
                    except AgentCancelled:
                        finish('cancelled', phase=phase, frame=frame)
                        return
                    except ValueError as error:
                        if self.cancel.is_set():
                            finish('cancelled', phase=phase, frame=frame)
                            return
                        rejected += 1
                        self.update(rejected_commands=self.job['rejected_commands'] + 1)
                        record('rejected', action_id=action_id, frame=frame, reason=str(error))
                        if (rejected >= 3 and str(error) != 'Observation périmée.') or rejected >= 10:
                            finish('rejected', phase=phase, frame=frame)
                            self.update(state='blocked', message=f'Commande refusée en phase {phase}, frame {frame}.')
                            return
                        with self.lock:
                            if self.cancel.is_set() or self.session.owner != 'agent':
                                finish('cancelled', phase=phase, frame=frame)
                                return
                            observation = self.checked('observe_match', **arguments)['match_observation']
                        continue

                    current = result['match_observation']
                    rejected = 0
                    progressed = (phase, observation['clock'], actions) != (
                        current['phase'], current['clock'], current['legal_actions'])
                    previous_score, current_score = observation['score'], current['score']
                    if previous_score and current_score and sum(current_score.values()) > sum(previous_score.values()):
                        goal_animation_until = current['frame'] + 3600
                        progressed = True
                    stalled_frames = 0 if progressed else stalled_frames + current['frame'] - frame
                    if action_id:
                        accepted_at = time.monotonic()
                        gap = None if last_action is None else accepted_at - last_action
                        # The emulator is running, rather than waiting for a choice, during advances.
                        input_gap = None if gap is None else max(0, gap - advance_since_action)
                        last_action = accepted_at
                        advance_since_action = 0
                        self.history.append(action_id)
                        repeated = 0 if progressed else repeated + 1
                        if gap is not None:
                            self.update(max_action_gap_seconds=max(self.job['max_action_gap_seconds'] or 0, gap),
                                        max_input_gap_seconds=max(self.job['max_input_gap_seconds'] or 0, input_gap))
                        self.update(rule_actions=self.job['rule_actions'] + int(decision_mode == 'rules'),
                                    message=action_id)
                        record('accepted', action_id=action_id, frame=frame, gap_seconds=gap,
                               input_gap_seconds=input_gap)
                        cooldown = (240 if action_id == 'formation.open' else 120) if not progressed else 0
                    else:
                        advanced = current['frame'] - frame
                        cooldown = 0 if progressed else max(0, cooldown - advanced)
                        seconds = time.monotonic() - started
                        advance_since_action += seconds
                        if waiting_for_transition:
                            self.update(animation_seconds=self.job['animation_seconds'] + seconds)
                        record('advance', frame=frame, frames=advanced, seconds=seconds,
                               forced_animation=waiting_for_transition)
                        if progressed:
                            repeated = 0
                    observation = current

                if self.cancel.is_set():
                    finish('cancelled', frame=observation['frame'])
                elif observation['phase'] == 'result':
                    finish('result', observation=observation)
                    self.update(message='Match terminé. Résultat confirmé par l’émulateur.',
                                result=observation)
                else:
                    finish('budget', frame=observation['frame'])
                    self.update(message='Budget de décisions atteint. Le jeu est en pause.')
        return {'job':self.launch(player,'Démarrage du pilote local…')}

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
            except TimeoutError:
                decision = self.wait_action('Délai du modèle dépassé, le jeu avance')
            finally:
                feedback_done.set()
                feedback_thread.join()
        validate_decision(decision)
        if decision['intent'] == 'finished':
            decision = self.wait_action('Résultat non confirmé par le jeu')
        elapsed = round((time.monotonic()-started)*1000,2)
        counter = {'rules':'rule_actions','text':'text_calls','vision':'vision_calls'}[mode]
        self.update(decision_ms=elapsed,**{counter:self.job.get(counter,0)+1})
        folder = ROOT/'build/agents'
        folder.mkdir(parents=True,exist_ok=True)
        with (folder/f'{session_id}-decisions.jsonl').open('a',encoding='utf-8') as log:
            log.write(json.dumps({'mode':mode,'milliseconds':elapsed,'frame':observation.get('frame'),
                                  'screen':state.get('screen',{}).get('name'),'action':decision},ensure_ascii=False)+'\n')
        return decision,observation

    @staticmethod
    def wait_action(reason):
        return {'intent':'act','reason':reason,'frames':120,'keys':[],'touch':None,'path':[]}

    def stop(self, session_id=None):
        with self.lock:
            if session_id is not None and session_id != self.session.session_id:
                raise ValueError('Session inconnue')
            self.cancel.set()
            if self.session.session_id and self.session.owner=='agent':
                self.session.set_control(self.session.session_id,'human')
            return {'stopping':True}

    def call(self, operation, arguments):
        if operation == 'open_club_route':
            if arguments: raise ValueError('Aucun argument attendu')
            if self.session.session_id: raise ValueError('Fermez la session actuelle avant d’ouvrir la route.')
            def enter_route():
                opened = self.session.open('club_web', cancel=self.cancel)
                self.checked('playback', session_id=opened['session_id'], running=True, include_image=False)
                self.update(message='Va voir Hillman et appuie sur A. Réponds Oui pour ouvrir la route.')
            return {'job': self.launch(enter_route, 'Ouverture du local de Hillman…')}
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
        if operation=='recruitment_turn':return self.recruitment_turn(**arguments)
        if operation=='recruitment_cancel':return self.recruitment_cancel(**arguments)
        if operation=='recruitment_confirm':return self.recruitment_confirm(**arguments)
        if operation=='stop_agent':return self.stop(**arguments)
        if operation=='delegate_player':return self.delegate(**arguments)
        if operation=='prepare_match':
            home,away,lines=arguments['home'],arguments['away'],arguments['lines']
            return {'job':self.launch(lambda:self.prepare(home,away,lines),'Préparation dynamique…')}
        if operation=='session_open':
            recruited = self.recruited_players() if arguments.get('profile') == 'arena' else None
            return self.session.open(**arguments, arena_recruitment=recruited or None)
        if operation=='session_close':
            with self.lock:
                if self.thread and self.thread.is_alive():raise ValueError('Arrêtez d’abord l’opération en cours.')
                if arguments.get('session_id')!=self.session.session_id:raise ValueError('Session inconnue')
                self.session.close();self.latest=None;self.fixture=None
                return {'closed':True}
        if operation=='set_control':
            with self.lock:
                if (arguments.get('session_id') == self.session.session_id
                        and arguments.get('owner')=='human' and self.thread and self.thread.is_alive()):
                    self.cancel.set()
                return self.session.set_control(**arguments)
        if operation in ('observe_match', 'apply_match_action', 'advance_match'):
            return self.checked(operation, **arguments, include_image=False)['match_observation']
        if operation in ('observe','step','touch_path','choose_duel','checkpoint_save','checkpoint_load','start_match','reset_match','playback'):
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
