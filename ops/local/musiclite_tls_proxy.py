#!/usr/bin/env python3
"""Small TLS reverse proxy used only for a local XAMPP integration test."""

from __future__ import annotations

import http.client
import os
import ssl
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


UPSTREAM_HOST = os.environ.get("MUSIC_AI_PROXY_UPSTREAM_HOST", "127.0.0.1")
UPSTREAM_PORT = int(os.environ.get("MUSIC_AI_PROXY_UPSTREAM_PORT", "80"))
MAX_BODY = int(os.environ.get("MUSIC_AI_PROXY_MAX_BODY", str(120 * 1024 * 1024)))
HOP_HEADERS = {"connection", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailers", "transfer-encoding", "upgrade"}


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "MusicLiteTLSProxy/1.0"

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > MAX_BODY:
            self.send_error(413)
            return
        body = self.rfile.read(length)
        headers = {key: value for key, value in self.headers.items() if key.lower() not in HOP_HEADERS}
        headers["Host"] = "localhost"
        headers["X-Forwarded-Proto"] = "https"
        connection = http.client.HTTPConnection(UPSTREAM_HOST, UPSTREAM_PORT, timeout=330)
        try:
            connection.request("POST", self.path, body=body, headers=headers)
            response = connection.getresponse()
            payload = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in HOP_HEADERS and key.lower() != "content-length":
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except (OSError, http.client.HTTPException):
            self.send_error(502)
        finally:
            connection.close()

    def log_message(self, message: str, *args) -> None:
        print(f"{self.client_address[0]} {message % args}", flush=True)


def main() -> None:
    cert = os.environ["MUSIC_AI_PROXY_CERT"]
    key = os.environ["MUSIC_AI_PROXY_KEY"]
    host = os.environ.get("MUSIC_AI_PROXY_HOST", "0.0.0.0")
    port = int(os.environ.get("MUSIC_AI_PROXY_PORT", "8443"))
    server = ThreadingHTTPServer((host, port), ProxyHandler)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert, key)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
