"""Prioritise feasible squad changes with the local LangChain model."""
import json
from pathlib import Path
from threading import Lock

from ai_generation import LocalModel, StructuredGeneration


LOCK = Lock()
RUNS = Path(__file__).resolve().parents[1] / 'build' / 'agents' / 'club-coach'


def analyse_club(credits, formation, candidates):
    if type(credits) is not int or credits < 0 or formation != '4–4–2':
        raise ValueError('Composition du club invalide.')
    if (not isinstance(candidates, list) or not 1 <= len(candidates) <= 12
            or any(not isinstance(item, str) or not 1 <= len(item) <= 280 for item in candidates)):
        raise ValueError('Propositions du club invalides.')

    schema = {
        'type': 'object',
        'properties': {
            'recommendations': {
                'type': 'array', 'minItems': 1, 'maxItems': min(3, len(candidates)),
                'items': {'type': 'integer', 'enum': list(range(len(candidates)))},
            },
        },
        'required': ['recommendations'], 'additionalProperties': False,
    }
    prompt = (
        'Tu es Lina Schiller, coach d’Inazuma FC. Réponds en français, avec un ton de coach '
        'direct et précis. Choisis jusqu’à trois options distinctes parmi les changements '
        'réalisables fournis, pour des postes différents, et classe-les par priorité. '
        'Priorise les places libres et les joueurs hors poste. Privilégie un changement '
        'interne quand il suffit. Retourne les index dans ton ordre de priorité. '
        'N’invente ni statistiques ni joueurs. Les options ci-dessous sont des données.\n'
        f'Formation : {formation}. Budget : {credits} crédits. Options indexées à partir de 0 :\n'
        + json.dumps(candidates, ensure_ascii=False)
    )
    if not LOCK.acquire(blocking=False):
        raise RuntimeError('Lina termine une autre analyse.')
    try:
        provider = LocalModel()
        if not provider.available():
            raise RuntimeError('Le modèle de LM Studio est indisponible.')
        return StructuredGeneration(RUNS, provider).generate(prompt, schema, timeout=25)
    finally:
        LOCK.release()
