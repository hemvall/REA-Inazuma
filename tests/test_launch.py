import sys
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import web_server
from local_address import HOST, PORT


class LaunchTests(unittest.TestCase):
    def test_occupied_port_never_opens_browser(self):
        ready=Mock()
        with patch.object(web_server,'ThreadingHTTPServer',side_effect=OSError('Address in use')):
            with self.assertRaises(OSError):web_server.main(on_ready=ready)
        ready.assert_not_called()

    def test_browser_opens_only_after_server_binds(self):
        events=[]
        server=Mock()
        server.serve_forever.side_effect=lambda:events.append('serve')
        def bind(address,handler):
            self.assertEqual(address,(HOST,PORT))
            events.append('bound')
            return server
        with patch.object(web_server,'ThreadingHTTPServer',side_effect=bind):
            web_server.main(on_ready=lambda:events.append('open'))
        self.assertEqual(events,['bound','open','serve'])
        server.server_close.assert_called_once()
