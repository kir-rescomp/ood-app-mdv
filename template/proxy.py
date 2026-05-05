#!/usr/bin/env python3
"""
OOD rnode path-rewriting proxy for MDV.
Rewrites absolute /flask/ asset paths to relative paths in HTML responses
so they load correctly through OOD's rnode reverse proxy.
WebSocket connections (socket.io) are forwarded transparently.
"""
import http.server
import urllib.request
import urllib.error
import socket
import threading
import os

FLASK_HOST = '127.0.0.1'
FLASK_PORT = int(os.environ['FLASK_PORT'])
BIND_PORT  = int(os.environ['BIND_PORT'])

REWRITE_PAIRS = [
    (b'href="/flask/',  b'href="flask/'),
    (b"href='/flask/",  b"href='flask/"),
    (b'src="/flask/',   b'src="flask/'),
    (b"src='/flask/",   b"src='flask/"),
    (b'url("/flask/',   b'url("flask/'),
    (b"url('/flask/",   b"url('flask/"),
]

HOP_BY_HOP = {'connection','keep-alive','transfer-encoding','te',
               'trailer','upgrade','proxy-authorization','proxy-authenticate'}

def websocket_bridge(client_sock, server_sock):
    """Bidirectional raw socket bridge for WebSocket connections."""
    def pipe(src, dst):
        try:
            while True:
                chunk = src.recv(65536)
                if not chunk:
                    break
                dst.sendall(chunk)
        except Exception:
            pass
        finally:
            for s in (src, dst):
                try: s.shutdown(socket.SHUT_RDWR)
                except: pass
    threading.Thread(target=pipe, args=(client_sock, server_sock), daemon=True).start()
    threading.Thread(target=pipe, args=(server_sock, client_sock), daemon=True).start()


class ProxyHandler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass  # suppress per-request logging

    def _is_websocket(self):
        return (self.headers.get('Upgrade', '').lower() == 'websocket'
                or 'upgrade' in self.headers.get('Connection', '').lower())

    def _handle_websocket(self):
        try:
            server_sock = socket.create_connection((FLASK_HOST, FLASK_PORT), timeout=10)
            # Reconstruct and forward the HTTP upgrade request
            lines = [f'{self.command} {self.path} {self.request_version}\r\n']
            for k, v in self.headers.items():
                lines.append(f'{k}: {v}\r\n')
            lines.append('\r\n')
            server_sock.sendall(''.join(lines).encode())
            websocket_bridge(self.connection, server_sock)
        except Exception as e:
            self.send_error(502, f'WebSocket bridge error: {e}')

    def _proxy(self):
        if self._is_websocket():
            self._handle_websocket()
            return

        url = f'http://{FLASK_HOST}:{FLASK_PORT}{self.path}'
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else None
        hdrs = {k: v for k, v in self.headers.items()
                if k.lower() not in HOP_BY_HOP | {'host'}}

        req = urllib.request.Request(url, data=body, headers=hdrs, method=self.command)
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
                ct = resp.headers.get('Content-Type', '')
                if 'text/html' in ct:
                    for old, new in REWRITE_PAIRS:
                        data = data.replace(old, new)
                self.send_response(resp.status)
                for k, v in resp.headers.items():
                    if k.lower() not in HOP_BY_HOP | {'content-length'}:
                        self.send_header(k, v)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_error(502, str(e))

    do_GET = do_POST = do_PUT = do_DELETE = do_PATCH = do_OPTIONS = _proxy


if __name__ == '__main__':
    server = http.server.ThreadingHTTPServer(('0.0.0.0', BIND_PORT), ProxyHandler)
    print(f'[proxy] Listening on 0.0.0.0:{BIND_PORT} → {FLASK_HOST}:{FLASK_PORT}')
    server.serve_forever()
