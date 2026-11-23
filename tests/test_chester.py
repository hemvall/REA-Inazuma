import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from chester import MatchCommentary, generate_reaction


class ChesterTests(unittest.TestCase):
    def setUp(self):
        self.journal = MatchCommentary()
        self.fixture = {'id': 'first', 'home': 3, 'away': 10}
        self.teams = {3: {'name': 'Occulte'}, 10: {'name': 'Zeus'}}

    def observe(self, phase, home=None, away=None, source=None, **facts):
        self.journal.observe({'fixture': self.fixture}, {
            'phase': phase, 'frame': 50, 'result_source': source,
            'score': None if home is None else {'home': home, 'away': away},
            **facts,
        }, self.teams)

    def test_confirmed_goals_and_result_are_recorded_once(self):
        self.observe('idle')
        self.observe('playing', 0, 0)
        self.observe('playing', 0, 1)
        self.observe('playing')
        self.observe('playing', 0, 0)
        self.observe('playing', 0, 1)
        self.observe('playing', 1, 1)
        self.observe('result', 1, 1, 'native_callback')
        self.observe('result', 1, 1, 'native_final_screen')
        events = self.journal.snapshot()['events']
        self.assertEqual([(event['kind'], event['side']) for event in events], [
            ('kickoff', None), ('goal', 'away'), ('goal', 'home'), ('result', None),
        ])
        self.assertEqual(events[1]['text'], 'Et ça rentre pour Zeus ! Le match bascule ! Occulte 0, Zeus 1.')

    def test_checkpoint_sets_a_new_epoch_and_baselines_restored_score(self):
        self.observe('playing', 0, 0)
        self.observe('playing', 1, 0)
        before = self.journal.snapshot()
        self.journal.reset(restored=True)
        self.observe('playing', 0, 0)
        self.assertEqual(self.journal.snapshot()['events'], [])
        self.observe('playing', 1, 0)
        after = self.journal.snapshot()
        self.assertGreater(after['epoch'], before['epoch'])
        self.assertGreater(after['cursor'], before['cursor'])
        self.assertEqual([event['kind'] for event in after['events']], ['goal'])

    def test_actions_come_from_native_screens_and_changes_of_holder(self):
        self.teams[3]['roster_names'] = {42: 'Talisman'}
        self.observe('playing', 0, 0, possession={'side': 'home', 'record': 1})
        self.observe('playing', 0, 0, possession={'side': 'home', 'record': 3, 'unit': 42})
        self.observe('playing', 0, 0, screen='attack_duel')
        self.observe('playing', 0, 0, screen='attack_duel_dodge')
        self.observe('playing', 0, 0, possession={'side': 'away', 'record': 2})
        self.observe('playing', 0, 0, screen='shot_block_menu')
        self.observe('playing', 0, 0, screen='keeper_duel')
        self.observe('halftime', 0, 0)
        self.observe('halftime', 0, 0)
        self.observe('playing', 0, 0)
        self.assertEqual([event['kind'] for event in self.journal.snapshot()['events']], [
            'kickoff', 'handoff', 'attack_duel', 'turnover', 'shot', 'halftime', 'resume',
        ])
        self.assertIn('Talisman', self.journal.snapshot()['events'][1]['text'])

    def test_model_writes_a_new_short_reaction_and_rejects_scorelines(self):
        class Agent:
            reaction = 'Le bloc va devoir se replacer très vite !'

            def generate(self, prompt, schema, *, timeout, match_context):
                return {'reaction': self.reaction}

        agent = Agent()
        self.assertEqual(generate_reaction(agent, 'turnover', None, match_context=dict)['reaction'], agent.reaction)
        with self.assertRaises(ValueError):
            generate_reaction(agent, 'turnover', agent.reaction, match_context=dict)
        agent.reaction = 'Score final : 24 à 0 !'
        with self.assertRaises(ValueError):
            generate_reaction(agent, 'turnover', None, match_context=dict)


    def test_neuille_asks_for_a_joke_about_the_confirmed_action(self):
        class Agent:
            def generate(self, prompt, schema, *, timeout, match_context):
                self.prompt = prompt
                self.context = match_context()
                return {'reaction': 'Oh na, défense en PC de CDI !'}

        agent = Agent()
        facts = 'Le porteur provoque son défenseur !'
        self.assertIn('CDI', generate_reaction(agent, 'attack_duel', None, match_context=lambda: {'action': facts}, mode='neuille')['reaction'])
        self.assertIn('Neuille', agent.prompt)
        self.assertEqual(agent.context['action'], facts)

    def test_summaries_use_observed_actions_and_detect_a_second_half_comeback(self):
        self.observe('playing', 0, 0)
        self.observe('playing', 0, 0, screen='shot_block_menu')
        self.observe('playing', 1, 0)
        self.observe('halftime', 1, 0)
        halftime = self.journal.snapshot()['events'][-1]
        self.assertEqual(halftime['summary']['shots_observed'], 1)
        self.assertIn('Zeus devra prendre l’initiative', halftime['text'])
        self.observe('playing', 1, 0)
        self.observe('playing', 1, 1)
        self.observe('playing', 1, 2)
        self.observe('result', 1, 2, 'native_final_screen')
        final = self.journal.snapshot()['events'][-1]
        self.assertEqual(final['summary']['halftime_score'], {'home': 1, 'away': 0})
        self.assertIn('Zeus a renversé le match', final['text'])
