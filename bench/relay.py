"""One fixed model endpoint for an offline Docker container. No host key enters it."""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

MODEL = "gpt-4.1-mini-2025-04-14"
MAX_CALLS = 32
LIMIT = 8 * 1024 * 1024


class LocalEndpoint(BaseHTTPRequestHandler):
    def do_POST(self):
        size = int(self.headers.get("Content-Length", 0))
        if self.path != "/v1/chat/completions" or not 0 < size <= LIMIT:
            return self.send_error(400)
        payload = self.rfile.read(size)
        print(base64.b64encode(payload).decode(), flush=True)
        status, content_type, encoded = json.loads(sys.stdin.buffer.readline())
        response = base64.b64decode(encoded)
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)


def forward(process):
    """Host side of the pipe. Accept only ordinary function tools for this model."""
    calls = 0
    for line in process.stdout:
        payload = base64.b64decode(line)
        request = json.loads(payload)
        calls += 1
        if (calls > MAX_CALLS or request.get("model") != MODEL or
                any(tool.get("type") != "function" for tool in request.get("tools", []))):
            status, kind, body = 403, "application/json", b'{"error":{"message":"M0 relay limit"}}'
        else:
            api = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions", data=payload,
                headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"],
                         "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(api, timeout=100) as response:
                    status = response.status
                    kind = response.headers.get_content_type()
                    body = response.read()
            except urllib.error.HTTPError as exc:
                status, kind = exc.code, "application/json"
                body = json.dumps({"error": {"message": "Upstream HTTP %d" % status}}).encode()
            except OSError:
                status, kind, body = 502, "application/json", b'{"error":{"message":"Upstream connection failed"}}'
        reply = [status, kind, base64.b64encode(body).decode()]
        process.stdin.write(json.dumps(reply).encode() + b"\n")
        process.stdin.flush()


if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", 9741), LocalEndpoint)
    print("ready", flush=True)
    server.serve_forever()
