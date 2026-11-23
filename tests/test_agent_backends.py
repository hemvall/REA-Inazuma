import json
import sys
import tempfile
import threading
import unittest

import httpx
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from agent_runtime import LocalAgent, CodexAgent, AgentCancelled, InvalidAgentResponse
from arena_service import Arena
from chester import generate_reaction


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

    def model_transport(self, content='{"ok":true}', finish_reason='stop'):
        def response(request):
            return httpx.Response(200, json={
                'id': 'test-completion', 'object': 'chat.completion', 'created': 1,
                'model': 'qwen/qwen3.5-9b',
                'choices': [{'index': 0, 'finish_reason': finish_reason,
                             'message': {'role': 'assistant', 'content': content}}],
            })
        transport = Mock(side_effect=response)
        class ModelClient(httpx.Client):
            def __init__(self, **kwargs):
                super().__init__(transport=httpx.MockTransport(transport), **kwargs)

        return patch('httpx.Client', ModelClient), transport

    def test_local_image_and_structured_response(self):
        client, transport = self.model_transport()
        with tempfile.TemporaryDirectory() as directory, client:
            agent = LocalAgent(directory)
            image = Path(directory) / 'screen.png'
            image.write_bytes(b'fixture-image')
            self.assertEqual(agent.generate('Observe', {'type': 'object'}, image=image), {'ok': True})
            request = transport.call_args.args[0]
            self.assertEqual(request.url.path, '/v1/chat/completions')
            payload = json.loads(request.content)
            self.assertTrue(payload['messages'][0]['content'][1]['image_url']['url'].startswith('data:image/png;base64,'))
            self.assertEqual(payload['response_format']['type'], 'json_schema')
            self.assertEqual(payload['reasoning_effort'], 'none')
            self.assertEqual(payload['max_tokens'], 1500)
            self.assertTrue(list(Path(directory).glob('*/response.json')))

    def test_cancelled_request_cannot_return_late_action(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = LocalAgent(directory)
            cancel = threading.Event()

            def reply(request):
                cancel.set()
                return '{}'

            agent.provider.invoke = reply
            with self.assertRaises(AgentCancelled):
                agent.generate('Observe', {}, cancel=cancel)
            self.assertFalse(list(Path(directory).glob('*/response.json')))

    def test_chester_requires_a_model_tool_call(self):
        client, transport = self.model_transport()
        read = Mock()
        with tempfile.TemporaryDirectory() as directory, client:
            with self.assertRaises(InvalidAgentResponse):
                LocalAgent(directory).generate('Commente', {}, match_context=read)
            read.assert_not_called()
            self.assertEqual(transport.call_count, 1)

    def test_neuille_uses_the_langchain_match_context_tool(self):
        client, transport = self.model_transport('{"reaction":"Oh na, défense en mode avion !"}')
        final_response = transport.side_effect
        tool_call = {'id': 'call_context', 'type': 'function',
                     'function': {'name': 'get_match_context', 'arguments': '{}'}}
        transport.side_effect = [
            httpx.Response(200, json={'choices': [{'index': 0, 'finish_reason': 'tool_calls',
                'message': {'role': 'assistant', 'content': None, 'tool_calls': [tool_call]}}]}),
            final_response(None),
        ]
        read = Mock(return_value={'score': {'home': 2, 'away': 1}})
        with tempfile.TemporaryDirectory() as directory, client:
            result = generate_reaction(LocalAgent(directory), 'goal', None, match_context=read, mode='neuille')
            self.assertEqual(result['reaction'], 'Oh na, défense en mode avion !')
            read.assert_called_once_with()
            payload = json.loads(transport.call_args.args[0].content)
            self.assertEqual(payload['messages'][-1]['role'], 'tool')
            self.assertEqual(json.loads(payload['messages'][-1]['content']), read.return_value)

    def test_remote_server_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', {'INAZUMIA_LLM_URL':'https://example.com/v1'}):
            with self.assertRaises(ValueError):
                LocalAgent(directory)

    def test_incomplete_generation_is_rejected(self):
        client, _ = self.model_transport(finish_reason='length')
        with tempfile.TemporaryDirectory() as directory, client:
            with self.assertRaises(InvalidAgentResponse):
                LocalAgent(directory).generate('Observe', {})

    def test_codex_reply_uses_shared_schema_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = CodexAgent(directory)
            agent.provider.invoke = Mock(return_value='{"action_id":"invented"}')
            with self.assertRaises(InvalidAgentResponse):
                agent.decide_match_action({'legal_actions': [{'id': 'pass'}]}, None)
            self.assertFalse(list(Path(directory).glob('*/response.json')))


if __name__ == '__main__':
    unittest.main()
