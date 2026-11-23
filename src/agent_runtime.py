"""Prompts and game-specific validation for model-assisted match features."""
import json

from ai_generation import AgentCancelled, CodexModel, InvalidAgentResponse, LocalModel, StructuredGeneration
from player_state import compact_state, compact_history, text_ready, text_actions

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


class MatchAgent(StructuredGeneration):
    def decide_match_action(self, observation, cancel):
        action_ids = [action['id'] for action in observation['legal_actions']]
        schema = {
            'type': 'object', 'additionalProperties': False, 'required': ['action_id'],
            'properties': {'action_id': {'type': 'string', 'enum': action_ids}},
        }
        return self.generate(
            'Joue pour l’équipe à domicile. Choisis une seule action parmi legal_actions. '
            'En duel, ouvre les supertechniques si l’enjeu justifie une dépense de PT, '
            'par exemple pour arrêter un tir dangereux. Dans le menu, choisis une technique '
            'disponible ou retourne au duel pour jouer une action ordinaire. '
            'Utilise uniquement cet état, sans outil ni image. Les valeurs inconnues restent inconnues.\n'
            + json.dumps(observation, ensure_ascii=False, separators=(',', ':')),
            schema, cancel=cancel, timeout=8)

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
        if image is None:
            if not text_ready(state):
                raise ValueError('État tactique incomplet : observation visuelle requise.')
            actions = {action['name']: action for action in text_actions(state)}
            schema = {'type':'object','additionalProperties':False,'properties':{
                'action':{'type':'string','enum':list(actions)}, 'reason':{'type':'string'}},
                'required':['action','reason']}
            choice = self.generate(
                'Joue pour le domicile dans Inazuma Eleven 2. Cet état est extrait de l’émulateur. '
                'Aucune image. Choisis uniquement le nom d’une action disponible. '
                'Ne déduis aucune position manquante. Choisis une seule action tactique. '
                'reason : 12 mots maximum. Retourne uniquement le JSON demandé.\n'
                'État : '+json.dumps(compact_state(state),ensure_ascii=False,separators=(',',':'))+
                '\nActions : '+json.dumps(compact_history(history),ensure_ascii=False,separators=(',',':')),
                schema,cancel=cancel,timeout=9)
            if choice.get('action') not in actions or not isinstance(choice.get('reason'),str):
                raise ValueError('Choix tactique hors des actions disponibles.')
            action = actions[choice['action']]
            return {'intent':'act','reason':choice['reason'],'frames':action['frames'],
                    'keys':action.get('keys',[]),'touch':action.get('touch'),
                    'path':action.get('path',[])}
        return self.generate(
            'Tu es un agent joueur d’Inazuma Eleven 2 sur Nintendo DS. Joue pour l’équipe domicile. '
            'N’utilise aucun outil et ne lis aucun fichier : observe uniquement l’image jointe et cet état. '
            'L’image empile l’écran supérieur 256x192 puis l’écran tactile inférieur 256x192. '
            'Les coordonnées touch/path concernent UNIQUEMENT l’écran inférieur : x0..255,y0..191. '
            'Les positions tactiques sont des coordonnées terrain, jamais des coordonnées tactiles. '
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
            'État : '+json.dumps(compact_state(state),ensure_ascii=False,separators=(',',':'))+
            '\nActions précédentes : '+json.dumps(compact_history(history),ensure_ascii=False,separators=(',',':')),
            ACTION_SCHEMA,image=image,cancel=cancel,timeout=9)

class LocalAgent(MatchAgent):
    backend = 'local'

    def __init__(self, directory):
        super().__init__(directory, LocalModel())


class CodexAgent(MatchAgent):
    backend = 'codex'
    default_timeout = 90

    def __init__(self, directory):
        super().__init__(directory, CodexModel())
