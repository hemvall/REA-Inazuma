"""Organiser and visual player using a loopback-only local model server.

The emulator is not advanced while the model thinks. Model output is untrusted
and is validated again by the worker before any DS input is executed.
"""
import json
import base64
import http.client
import os
import shutil
import subprocess
from pathlib import Path
import threading
import time
import uuid
from urllib.parse import urlsplit

BUTTONS = ['A','B','X','Y','L','R','START','SELECT','UP','DOWN','LEFT','RIGHT']
ACTION_SCHEMA = {
    'type':'object','additionalProperties':False,
    'properties': {
        'intent': {'type':'string','enum':['act','finished','blocked']},
        'reason': {'type':'string'},
        'frames': {'type':'integer','minimum':1,'maximum':120},
        'keys': {'type':'array','items':{'type':'string','enum':BUTTONS},'maxItems':12},
        'touch': {'anyOf':[{'type':'null'},{'type':'object','additionalProperties':False,
                    'properties':{'x':{'type':'integer','minimum':0,'maximum':255},
                                  'y':{'type':'integer','minimum':0,'maximum':191}},'required':['x','y']}]},
        'path': {'type':'array','maxItems':30,'items':{'type':'object','additionalProperties':False,
                 'properties':{'x':{'type':'integer','minimum':0,'maximum':255},
                               'y':{'type':'integer','minimum':0,'maximum':191},
                               'frames':{'type':'integer','minimum':1,'maximum':120}},'required':['x','y','frames']}},
    },'required':['intent','reason','frames','keys','touch','path']}

ORGANISER_SCHEMA = {'type':'object','additionalProperties':False,'properties':{
    'home':{'type':['integer','null']}, 'away':{'type':['integer','null']},
    'message':{'type':'string'},'lines':{'type':'array','items':{'type':'string'},'maxItems':6}},
    'required':['home','away','message','lines']}


class AgentCancelled(Exception):
    pass


class LocalAgent:
    backend = 'local'
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.endpoint = urlsplit(os.environ.get('INAZUMIA_LLM_URL', 'http://127.0.0.1:1234/v1'))
        if self.endpoint.scheme != 'http' or self.endpoint.hostname not in ('127.0.0.1', 'localhost', '::1') or self.endpoint.username or self.endpoint.password or self.endpoint.query or self.endpoint.fragment:
            raise ValueError('INAZUMIA_LLM_URL doit être une adresse HTTP locale sans authentification.')
        self.model = os.environ.get('INAZUMIA_LLM_MODEL', 'qwen/qwen3.5-9b')

    def _request(self, method, path, payload=None, timeout=180):
        connection = http.client.HTTPConnection(self.endpoint.hostname, self.endpoint.port or 80, timeout=timeout)
        try:
            connection.request(method, self.endpoint.path.rstrip('/')+path,
                               body=json.dumps(payload).encode('utf-8') if payload is not None else None,
                               headers={'Content-Type':'application/json'})
            response = connection.getresponse()
            body = response.read().decode('utf-8')
            if response.status != 200:
                raise RuntimeError(f'IA locale : HTTP {response.status} : {body[:500]}')
            return json.loads(body)
        finally:
            connection.close()

    def available(self):
        try:
            models = self._request('GET', '/models', timeout=1)
            return any(row.get('id') == self.model for row in models.get('data', []))
        except (OSError, ValueError, RuntimeError, http.client.HTTPException):
            return False

    def generate(self, prompt, schema, *, image=None, cancel=None, timeout=180):
        if cancel and cancel.is_set():
            raise AgentCancelled('Agent arrêté ; contrôle rendu au joueur.')
        run = self.directory/uuid.uuid4().hex
        run.mkdir()
        schema_path = run/'schema.json'
        output_path = run/'response.json'
        schema_path.write_text(json.dumps(schema),encoding='utf-8')
        content = [{'type':'text','text':prompt}]
        if image:
            encoded = base64.b64encode(Path(image).read_bytes()).decode('ascii')
            content.append({'type':'image_url','image_url':{'url':'data:image/png;base64,'+encoded}})
        payload = {'model':self.model, 'messages':[{'role':'user','content':content}],
                   'temperature':0.2, 'max_tokens':1500, 'stream':False,
                   'reasoning_effort':'none',
                   'response_format':{'type':'json_schema','json_schema':{
                       'name':'agent_response','strict':True,'schema':schema}}}
        (run/'prompt.txt').write_text(prompt,encoding='utf-8')
        completed = threading.Event()
        outcome = {}
        def request():
            try:
                outcome['response'] = self._request('POST', '/chat/completions', payload, timeout)
            except Exception as error:
                outcome['error'] = error
            finally:
                completed.set()
        threading.Thread(target=request, daemon=True).start()
        deadline = time.monotonic()+timeout
        while not completed.wait(.1):
            if cancel and cancel.is_set():
                raise AgentCancelled('Agent arrêté ; contrôle rendu au joueur.')
            if time.monotonic() > deadline:
                raise TimeoutError('IA locale trop lente ; émulation laissée en pause.')
        if cancel and cancel.is_set():
            raise AgentCancelled('Agent arrêté ; contrôle rendu au joueur.')
        try:
            if 'error' in outcome:
                raise outcome['error']
            response = outcome['response']
            (run/'agent.log').write_text(json.dumps(response,ensure_ascii=False),encoding='utf-8')
            if response['choices'][0].get('finish_reason') != 'stop':
                raise ValueError('Réponse interrompue ou budget de tokens atteint')
            result = json.loads(response['choices'][0]['message']['content'])
            if not isinstance(result,dict):
                raise ValueError('Objet JSON attendu')
            output_path.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
            return result
        except Exception as error:
            (run/'error.txt').write_text(str(error),encoding='utf-8')
            raise RuntimeError('Échec de l’IA locale. Démarrez le serveur LM Studio avec le modèle '+self.model+
                               '. Détail : '+str(error)) from error

    def organise(self, message, teams, cancel=None):
        return self.generate(
            'Tu es l’organisateur de rencontres Inazuma Eleven 2 en français. '
            'N’utilise aucun outil, ne lis aucun fichier : toutes les données sont ici. '
            'Résous la demande utilisateur avec les identifiants du catalogue uniquement. '
            'Si ambiguë ou non prise en charge, retourne home et away null, lines vide et une question claire. '
            'Sinon, écris exactement six courtes répliques françaises originales entre les deux capitaines, '
            'en alternant domicile puis extérieur. Chaque réplique fait au maximum 75 caractères, '
            'sans nom de locuteur préfixé, sans retour à la ligne. Ne promets pas une victoire. '
            'Les deux équipes doivent être distinctes.\nCatalogue : '+json.dumps(teams,ensure_ascii=False)+
            '\nDemande : '+message, ORGANISER_SCHEMA,cancel=cancel)

    def play(self, image, state, history, cancel):
        return self.generate(
            'Tu es un agent joueur d’Inazuma Eleven 2 sur Nintendo DS. Joue pour l’équipe domicile. '
            'N’utilise aucun outil et ne lis aucun fichier : observe uniquement l’image jointe et cet état. '
            'L’image empile l’écran supérieur 256x192 puis l’écran tactile inférieur 256x192. '
            'Les coordonnées touch/path concernent UNIQUEMENT l’écran inférieur : x0..255,y0..191. '
            'Lis les boutons réellement visibles. Avance les dialogues avec A ou un clic bas droite. '
            'Dans la formation, B quitte les détails et Suite est vers (230,175). '
            'Avant le départ, Début est vers (70,175). Continuer au même endroit reprend une pause. '
            'Si le menu Revoir / Retour au match est visible, Retour au match est vers (128,126). '
            'Évite le bouton Menu quand le jeu est actif. Choisis les duels, '
            'trace des courses et des passes, tire vers le but adverse quand tu possèdes le ballon. '
            'Une path est un glisser continu ; ses durées cumulées doivent rester <=120 frames. '
            'Une action step peut tenir des touches ou le stylet pendant 1..120 frames. '
            'Pour cliquer, utilise 6 frames ; le contrôleur ajoute quatre frames de relâchement. '
            'Pour attendre une animation, frames120 avec keys vide,touch null,path vide. '
            'Ne termine que sur un écran explicite de résultat final ; un score intermédiaire ne suffit pas. '
            'Si bloqué, explique ce que montre l’écran. reason : 12 mots maximum. Retourne exclusivement le JSON demandé.\n'
            'État : '+json.dumps(state,ensure_ascii=False)+
            '\nActions précédentes : '+json.dumps(history[-8:],ensure_ascii=False),
            ACTION_SCHEMA,image=image,cancel=cancel)


class CodexAgent(LocalAgent):
    backend = 'codex'
    model = 'Codex (configuration du CLI)'
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.executable = shutil.which('codex')

    def generate(self, prompt, schema, *, image=None, cancel=None, timeout=90):
        if not self.executable:
            raise RuntimeError('Codex CLI absent. Installez Codex et connectez votre compte pour utiliser les agents.')
        run = self.directory/uuid.uuid4().hex
        run.mkdir()
        schema_path = run/'schema.json'
        output_path = run/'response.json'
        schema_path.write_text(json.dumps(schema),encoding='utf-8')
        arguments = [self.executable,'exec','--ephemeral','--ignore-user-config',
                     '--skip-git-repo-check','--sandbox','read-only',
                     '--cd',str(run.resolve()),'--output-schema',str(schema_path.resolve()),
                     '--output-last-message',str(output_path.resolve()),'--color','never']
        if image:
            arguments.extend(['--image',str(Path(image).resolve())])
        arguments.append('-')
        (run/'prompt.txt').write_text(prompt,encoding='utf-8')
        with (run/'agent.log').open('w',encoding='utf-8') as log:
            process = subprocess.Popen(arguments,stdin=subprocess.PIPE,stdout=log,stderr=log,
                text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            try:
                process.stdin.write(prompt)
                process.stdin.close()
                deadline = time.monotonic()+timeout
                while process.poll() is None:
                    if cancel and cancel.wait(.2):
                        raise AgentCancelled('Agent arrêté ; contrôle rendu au joueur.')
                    if not cancel:
                        time.sleep(.2)
                    if time.monotonic()>deadline:
                        raise TimeoutError('Agent trop lent ; émulation laissée en pause.')
                if process.returncode or not output_path.is_file():
                    raise RuntimeError('Échec de l’agent Codex. Consultez le journal local : '+str(run/'agent.log'))
                result = json.loads(output_path.read_text(encoding='utf-8'))
                return result
            finally:
                if process.poll() is None:
                    if hasattr(subprocess,'CREATE_NO_WINDOW'):
                        subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                            creationflags=subprocess.CREATE_NO_WINDOW,check=False)
                    else:
                        process.kill()
                    process.wait(timeout=10)

    def available(self):
        return bool(self.executable)
