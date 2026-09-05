"""Container entrypoint only. NEVER run this script on the host with untrusted code."""
import contextlib
import io
import json
import resource
import sys


class CappedOutput(io.TextIOBase):
    def __init__(self):
        self.written = 0

    def write(self, value):
        self.written += len(value)
        if self.written > 8192:
            raise ValueError('Candidate printed more than 8192 characters')
        return len(value)


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))
    resource.setrlimit(resource.RLIMIT_FSIZE, (65536, 65536))
    resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError('Input too large')
        request = json.loads(raw)
        scope = {'__name__': '__candidate__'}
        sink = CappedOutput()
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            exec(compile(request['code'], '<candidate>', 'exec'), scope)
            value = scope['solve'](**request['case'])
        response = {'status': 'ok', 'value': value}
        encoded = json.dumps(response, allow_nan=False)
        if len(encoded.encode()) > 32768:
            response = {'status': 'invalid_output', 'message': 'Return value exceeds 32 KiB'}
    except BaseException as error:
        response = {'status': 'exception', 'message': f'{type(error).__name__}: {str(error)[:500]}'}
    sys.stdout.write(json.dumps(response, allow_nan=False))


if __name__ == '__main__':
    main()
