#!/usr/bin/env python3
"""
Mini server (solo stdlib) per il client browser:
  GET  /          -> index.html
  POST /session   -> conia un ephemeral token (la API key resta qui, mai nel browser)
  POST /robot     -> endpoint finto "hardware" chiamato dal tool del browser

Uso:  export XAI_API_KEY=xai-... ; python server.py ; apri http://localhost:8000
(getUserMedia richiede https oppure localhost)
"""
import json
import os
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

API_BASE = os.getenv("XAI_API_BASE", "https://api.x.ai")
HERE = Path(__file__).parent


class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            body = (HERE / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        payload = json.loads(self.rfile.read(length) or b"{}")
        if self.path == "/session":
            req = urllib.request.Request(
                f"{API_BASE}/v1/realtime/client_secrets",
                data=json.dumps({"expires_after": {"seconds": 60}}).encode(),  # basta che duri fino al connect
                headers={"Authorization": f"Bearer {os.environ['XAI_API_KEY']}",
                         "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as r:
                    self._json(200, json.loads(r.read()))  # {"value": "...", "expires_at": ...}
            except Exception as e:
                self._json(502, {"error": str(e)})
        elif self.path == "/robot":
            print(f"[ROBOT] {payload}")  # TODO: inoltrare al robot/simulatore
            self._json(200, {"ok": True, **payload})
        else:
            self._json(404, {"error": "not found"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"http://localhost:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
