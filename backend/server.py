"""Dependency-free loopback API for a personal local research workbench."""
import argparse
import copy
import json
import mimetypes
import threading
import time
import uuid
from collections import OrderedDict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from .engine import PROFILES, STRATEGIES, check, discover, verify
from .execution import docker_evaluator, readiness
from .reports import prompts, source_record, timestamp
from .tasks import TASKS, catalog, demo_evaluator

DIST = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
MAX_BODY = 65536


class RequestError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status


def integer(data, field, default, lo, hi):
    value = data.get(field, default)
    if type(value) is not int or not lo <= value <= hi:
        raise RequestError(f'{field} must be an integer from {lo} to {hi}.')
    return value


def candidate(data, task):
    mode = data.get('mode', 'demo')
    variant = data.get('variant', 'buggy')
    if mode == 'demo':
        if variant not in ('buggy', 'correct'):
            raise RequestError('Unknown teaching example.')
        code = TASKS[task][variant]
        return demo_evaluator(task, variant), source_record(task, mode, variant, code)
    if mode != 'custom':
        raise RequestError('mode must be demo or custom.')
    code = data.get('code')
    if not isinstance(code, str) or not code.strip() or len(code.encode()) > 24000:
        raise RequestError('Provide Python code no larger than 24 KiB.')
    state = readiness()
    if not state['available']:
        raise RequestError(state['reason'], 503)
    return docker_evaluator(code), source_record(task, mode, None, code)


class LabServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address):
        super().__init__(address, Handler)
        self.run_lock = threading.Lock()
        self.reports = OrderedDict()

    def remember(self, report):
        now = time.monotonic()
        while self.reports and (len(self.reports) >= 24 or next(iter(self.reports.values()))[0] < now - 3600):
            self.reports.popitem(last=False)
        self.reports[report['run_id']] = (now, copy.deepcopy(report))

    def get_report(self, run_id):
        if not isinstance(run_id, str):
            raise RequestError('Missing run_id.')
        item = self.reports.get(run_id)
        if not item or item[0] < time.monotonic() - 3600:
            raise RequestError('The original run expired or the server restarted. Run the experiment again.', 404)
        return copy.deepcopy(item[1])


class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(15)

    def log_message(self, fmt, *args):
        # No candidate code or arbitrary request text in console logs.
        pass

    def allowed(self):
        authorities = {f'{host}:{port}' for host in ('127.0.0.1', 'localhost')
                       for port in (self.server.server_port, 5173)}
        if self.headers.get('Host') not in authorities:
            raise RequestError('Non-local Host rejected.', 403)
        origin = self.headers.get('Origin')
        if origin and origin not in {f'http://{authority}' for authority in authorities}:
            raise RequestError('Cross-site request rejected.', 403)

    def send_bytes(self, body, status=200, content_type='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, value, status=200):
        self.send_bytes(json.dumps(value, ensure_ascii=False, allow_nan=False).encode(), status)

    def do_GET(self):
        try:
            self.allowed()
            path = urlsplit(self.path).path
            if path == '/api/health':
                self.send_json({'status': 'ok', 'version': '1.0.0', 'runner': readiness()})
            elif path == '/api/tasks':
                self.send_json({'tasks': catalog()})
            elif path.startswith('/api/'):
                raise RequestError('Endpoint not found.', 404)
            else:
                file = (DIST / (unquote(path).lstrip('/') or 'index.html')).resolve()
                if not file.is_relative_to(DIST.resolve()) or not file.is_file():
                    raise RequestError('Build the frontend first: npm --prefix frontend run build', 404)
                self.send_bytes(file.read_bytes(), content_type=mimetypes.guess_type(file)[0] or 'application/octet-stream')
        except RequestError as error:
            self.send_json({'error': error.message}, error.status)

    def read_json(self):
        if self.headers.get_content_type() != 'application/json':
            raise RequestError('The request must use application/json.', 415)
        if self.headers.get('Transfer-Encoding'):
            raise RequestError('Chunked requests are not supported.')
        try:
            size = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            raise RequestError('Invalid request length.')
        if not 0 < size <= MAX_BODY:
            raise RequestError('The request is empty or larger than 64 KiB.', 413)
        try:
            data = json.loads(self.rfile.read(size))
        except (ValueError, UnicodeDecodeError, RecursionError):
            raise RequestError('The request is not valid JSON.')
        if not isinstance(data, dict):
            raise RequestError('The request must be a JSON object.')
        return data

    def do_POST(self):
        locked = False
        try:
            self.allowed()
            if self.path not in ('/api/run', '/api/verify'):
                raise RequestError('Endpoint not found.', 404)
            data = self.read_json()
            locked = self.server.run_lock.acquire(blocking=False)
            if not locked:
                raise RequestError('An experiment is already running. Try again shortly.', 409)
            count = integer(data, 'count', 100, 1, 500)
            if self.path == '/api/run':
                task = data.get('task')
                if not isinstance(task, str) or task not in TASKS:
                    raise RequestError('Unknown problem.')
                seed = integer(data, 'seed', 42, 0, 2**32 - 1)
                budget = integer(data, 'shrink_budget', 100, 0, 500)
                strategy = data.get('strategy', 'block')
                profile = data.get('profile', 'demo')
                if strategy not in STRATEGIES or profile not in PROFILES:
                    raise RequestError('Unknown strategy or generator profile.')
                evaluate, source = candidate(data, task)
                report = discover(task, evaluate, seed, count, budget, strategy=strategy, profile=profile)
                report.update({'schema_version': '1.1', 'run_id': uuid.uuid4().hex,
                               'created_at': timestamp(), 'source': source})
                report['prompts'] = prompts(report)
                self.server.remember(report)
                self.send_json(report)
            else:
                discovery = self.server.get_report(data.get('run_id'))
                evaluate, source = candidate(data, discovery['task'])
                # A visible regression check is separate from the unseen test set.
                # Never count this already-exposed example as held-out evidence.
                previous = (discovery['shrink']['reduced'] if discovery['shrink'] else discovery['failure'])
                regression = check(discovery['task'], evaluate, previous['input']) if previous else None
                result = verify(discovery['task'], evaluate, discovery, count)
                result['regression'] = regression
                result.update({'run_id': discovery['run_id'], 'source': source, 'created_at': timestamp()})
                self.send_json(result)
        except RequestError as error:
            self.send_json({'error': error.message}, error.status)
        except (TimeoutError, ConnectionError):
            self.send_json({'error': 'Connection timed out. Try again.'}, 408)
        except Exception:
            self.send_json({'error': 'Internal server error. The request did not complete. Check the tests or restart the service.'}, 500)
        finally:
            if locked:
                self.server.run_lock.release()


def main():
    parser = argparse.ArgumentParser(description='Counterexample Lab local server')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    server = LabServer(('127.0.0.1', args.port))
    print(f'Counterexample Lab → http://127.0.0.1:{args.port}', flush=True)
    print('Built-in demos ready. Custom code requires Docker. Ctrl+C to stop.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
