"""Exercise the host-side call cap without a provider key or network access."""
import base64
import io
import json
import unittest
from email.message import Message
from types import SimpleNamespace
from unittest.mock import patch

import relay


class LocalResponse(io.BytesIO):
    status = 200
    headers = Message()
    headers["Content-Type"] = "text/event-stream"


class RelayLimitTests(unittest.TestCase):
    def test_first_n_forwarded_and_next_refused(self):
        for cap in (1, 32, 64, 128):
            with self.subTest(cap=cap):
                payloads = [json.dumps({"model": relay.MODEL, "user": str(i)}).encode()
                            for i in range(cap + 1)]
                incoming = b"".join(base64.b64encode(p) + b"\n" for p in payloads)
                process = SimpleNamespace(stdout=io.BytesIO(incoming), stdin=io.BytesIO())
                journal = io.StringIO()
                body = b"data: [DONE]\n\n"
                with patch.dict("os.environ", OPENAI_API_KEY="unit-test"), patch.object(
                    relay.urllib.request, "urlopen", side_effect=lambda *a, **k: LocalResponse(body)
                ) as upstream:
                    relay.forward(process, journal, max_calls=cap)

                self.assertEqual([c.args[0].data for c in upstream.call_args_list], payloads[:cap])
                replies = [json.loads(line) for line in process.stdin.getvalue().splitlines()]
                self.assertEqual([r[0] for r in replies], [200] * cap + [403])
                self.assertTrue(all(base64.b64decode(r[2]) == body for r in replies[:-1]))
                self.assertIn("limit", json.loads(base64.b64decode(replies[-1][2]))["error"]["message"])
                events = [json.loads(line) for line in journal.getvalue().splitlines()]
                self.assertEqual([e["event"] for e in events], ["sent", "response"] * cap + ["limit_hit"])
                self.assertEqual([e["call"] for e in events[:-1:2]], list(range(1, cap + 1)))

    def test_interrupted_chunked_response_does_not_kill_relay(self):
        class BrokenStream(LocalResponse):
            def read(self):
                raise relay.http.client.IncompleteRead(b"partial SSE")

        request = base64.b64encode(json.dumps({"model": relay.MODEL}).encode()) + b"\n"
        process = SimpleNamespace(stdout=io.BytesIO(request * 2), stdin=io.BytesIO())
        journal = io.StringIO()
        with patch.dict("os.environ", OPENAI_API_KEY="unit-test"), patch.object(
            relay.urllib.request, "urlopen", side_effect=[BrokenStream(), LocalResponse(b"data: [DONE]\n")]
        ):
            relay.forward(process, journal, max_calls=2)
        self.assertEqual([json.loads(line)[0] for line in process.stdin.getvalue().splitlines()], [502, 200])
        responses = [e for e in map(json.loads, journal.getvalue().splitlines()) if e["event"] == "response"]
        self.assertEqual([r["call"] for r in responses], [1, 2])
        self.assertIsNone(responses[0]["usage"])
