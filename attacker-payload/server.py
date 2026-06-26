#!/usr/bin/env python3
"""
C2 stub server for Lab 1 assessment-2 (workshop infrastructure).

Listens only on 127.0.0.1:8080. Returns a JSON object {"snippet": "<js source>"}
when /payload is requested. The "snippet" is the contents of payload.js — the
defanged stand-in for a real-world remote stealer.

Only meant to run inside the workshop image, which is the safety boundary for
this lab. The image-only distribution model keeps the payload + this stub off
participants' host filesystems.
"""
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
PAYLOAD_PATH = os.path.join(HERE, "payload.js")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/payload":
            # Re-read on every request so payload.js edits show up
            # without restarting the server. Also makes the workshop's
            # "edit payload, see different behavior" demo work without
            # a process bounce.
            with open(PAYLOAD_PATH, "r", encoding="utf-8") as f:
                payload = f.read()
            body = json.dumps({"snippet": payload}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("[c2-stub] " + (fmt % args) + "\n")


def main():
    host, port = "127.0.0.1", 8080
    httpd = HTTPServer((host, port), Handler)
    sys.stderr.write("[c2-stub] listening on http://%s:%d (workshop only)\n" % (host, port))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
