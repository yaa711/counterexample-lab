"""Docker boundary. Host code only builds commands and parses bounded JSON."""
import json
import selectors
import shutil
import subprocess
import time
import uuid

IMAGE = 'counterexample-lab-runner:1'
MAX_OUTPUT = 65536


def readiness():
    if not shutil.which('docker'):
        return {'available': False, 'reason': 'Docker was not found. Built-in demos work; custom code requires Docker and the runner image.'}
    try:
        result = subprocess.run(['docker', 'image', 'inspect', IMAGE], capture_output=True, timeout=4)
    except (OSError, subprocess.TimeoutExpired):
        return {'available': False, 'reason': 'Docker did not respond. Start Docker Desktop.'}
    return {'available': result.returncode == 0,
            'reason': 'Isolated runner ready' if result.returncode == 0 else 'Start Docker and build the counterexample-lab-runner:1 image.'}


def docker_command(name):
    # Isolation is layered: network/filesystem restrictions limit access, while
    # CPU/memory/process caps limit consumption. No host directory is mounted.
    return ['docker', 'run', '--rm', '--pull', 'never', '--name', name,
            '--network', 'none', '--read-only', '--cap-drop', 'ALL',
            '--security-opt', 'no-new-privileges', '--pids-limit', '32',
            '--memory', '128m', '--memory-swap', '128m', '--cpus', '0.5',
            '--user', '65534:65534', '--log-driver', 'none', '-i', IMAGE]


def _communicate_bounded(proc, payload, timeout):
    """Drain both pipes without ever collecting unlimited candidate output."""
    deadline = time.monotonic() + timeout
    buffers = {'stdout': bytearray(), 'stderr': bytearray()}
    offset = 0
    # Read stdout and stderr together. Draining just one pipe can deadlock when
    # the other fills; collecting unlimited output could exhaust the host's RAM.
    with selectors.DefaultSelector() as selector:
        selector.register(proc.stdin, selectors.EVENT_WRITE, 'stdin')
        selector.register(proc.stdout, selectors.EVENT_READ, 'stdout')
        selector.register(proc.stderr, selectors.EVENT_READ, 'stderr')
        while selector.get_map():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(proc.args, timeout)
            for event, _ in selector.select(min(remaining, .1)):
                if event.data == 'stdin':
                    try:
                        sent = event.fileobj.write(payload[offset:offset + 4096])
                        event.fileobj.flush()
                        offset += sent
                    except BrokenPipeError:
                        offset = len(payload)
                    if offset >= len(payload):
                        selector.unregister(event.fileobj)
                        event.fileobj.close()
                else:
                    chunk = event.fileobj.read1(4096)
                    if not chunk:
                        selector.unregister(event.fileobj)
                        continue
                    buffers[event.data].extend(chunk)
                    if sum(len(b) for b in buffers.values()) > MAX_OUTPUT:
                        raise OverflowError('Output exceeded the 64 KiB limit.')
        proc.wait(timeout=max(.01, deadline - time.monotonic()))
    return bytes(buffers['stdout']), bytes(buffers['stderr'])


def docker_evaluator(code):
    def evaluate(case):
        name = 'counterexample-' + uuid.uuid4().hex
        proc = None
        try:
            proc = subprocess.Popen(docker_command(name), stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = _communicate_bounded(proc, json.dumps({'code': code, 'case': case}).encode(), 6)
            if proc.returncode in (125, 126, 127):
                return {'status': 'infrastructure_error', 'message': 'Docker could not start the runner: ' + stderr.decode(errors='replace')[:300]}
            if proc.returncode != 0:
                return {'status': 'exception', 'message': f'Candidate exited ({proc.returncode}); a resource limit may have been reached.'}
            try:
                result = json.loads(stdout)
            except (ValueError, RecursionError, UnicodeDecodeError):
                return {'status': 'invalid_output', 'message': 'The candidate did not produce valid JSON.'}
            if not isinstance(result, dict) or result.get('status') not in ('ok', 'exception', 'invalid_output'):
                return {'status': 'invalid_output', 'message': 'The candidate returned an invalid runner response.'}
            if result['status'] == 'ok':
                return {'status': 'ok', 'value': result.get('value')}
            return {'status': result['status'], 'message': str(result.get('message', ''))[:500]}
        except subprocess.TimeoutExpired:
            return {'status': 'timeout', 'message': 'Execution exceeded 6 seconds and was terminated.'}
        except OverflowError as error:
            return {'status': 'invalid_output', 'message': str(error)}
        except OSError:
            return {'status': 'infrastructure_error', 'message': 'Cannot access Docker. Check the local runner.'}
        finally:
            if proc:
                if proc.poll() is None:
                    proc.kill()
                proc.wait()
                for stream in (proc.stdin, proc.stdout, proc.stderr):
                    if not stream.closed:
                        stream.close()
            # The CLI process dying does not guarantee the container has stopped.
            try:
                subprocess.run(['docker', 'rm', '--force', name], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass  # Document manual cleanup if the Docker daemon itself is unreachable.
    return evaluate
