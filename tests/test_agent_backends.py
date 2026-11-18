import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent_runtime import LocalAgent, CodexAgent, AgentCancelled
from arena_service import Arena


class BackendTests(unittest.TestCase):
    def test_choice_survives_restart_and_active_job_prevents_switch(self):
        with tempfile.TemporaryDirectory() as directory, patch('arena_service.ROOT', Path(directory)), patch.dict('os.environ', {}, clear=True):
            arena = Arena()
            self.assertIsInstance(arena.agent, LocalAgent)
            arena.select_agent('codex')
            self.assertIsInstance(Arena().agent, CodexAgent)
            arena.thread = Mock()
            arena.thread.is_alive.return_value = True
            with self.assertRaises(ValueError):
                arena.select_agent('local')
            self.assertIsInstance(arena.agent, CodexAgent)
            arena.thread = None
            arena.select_agent('local')
            self.assertNotIsInstance(Arena().agent, CodexAgent)
            with self.assertRaises(ValueError):
                arena.select_agent('unknown')

    def test_local_image_and_structured_response(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = LocalAgent(directory)
            image = Path(directory)/'screen.png'
            image.write_bytes(b'fixture-image')
            agent._request = Mock(return_value={'choices':[{'finish_reason':'stop','message':{'content':'{"ok":true}'}}]})
            self.assertEqual(agent.generate('Observe', {'type':'object'}, image=image), {'ok':True})
            payload = agent._request.call_args.args[2]
            self.assertTrue(payload['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
            self.assertEqual(payload['response_format']['type'], 'json_schema')
            self.assertEqual(payload['reasoning_effort'], 'none')
            self.assertTrue(list(Path(directory).glob('*/response.json')))

    def test_cancelled_request_cannot_return_late_action(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = LocalAgent(directory)
            cancel = threading.Event()
            def reply(*args):
                cancel.set()
                return {'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}
            agent._request = reply
            with self.assertRaises(AgentCancelled):
                agent.generate('Observe', {}, cancel=cancel)
            self.assertFalse(list(Path(directory).glob('*/response.json')))

    def test_remote_server_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', {'INAZUMIA_LLM_URL':'https://example.com/v1'}):
            with self.assertRaises(ValueError):
                LocalAgent(directory)

    def test_incomplete_generation_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = LocalAgent(directory)
            agent._request = Mock(return_value={'choices':[{'finish_reason':'length','message':{'content':'{}'}}]})
            with self.assertRaises(RuntimeError):
                agent.generate('Observe', {})


if __name__ == '__main__':
    unittest.main()
