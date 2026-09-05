import os
import subprocess
import sys
import unittest
from unittest.mock import patch

from backend.execution import _communicate_bounded, docker_command, docker_evaluator, readiness


class ExecutionTests(unittest.TestCase):
    def test_container_restrictions(self):
        command = docker_command('test-name')
        for flag in ['--read-only', '--network', '--cap-drop', '--security-opt', '--memory', '--pids-limit', '--user', '--pull']:
            self.assertIn(flag, command)
        self.assertNotIn('-v', command)
        self.assertNotIn('--mount', command)
        self.assertEqual(command[command.index('--network') + 1], 'none')

    def test_no_docker_is_explicit(self):
        with patch('backend.execution.shutil.which', return_value=None):
            self.assertFalse(readiness()['available'])

    def test_bounded_reader_rejects_large_output(self):
        # This is fixed trusted test code, never a user-supplied program.
        proc = subprocess.Popen([sys.executable, '-c', 'import sys; sys.stdin.read(); print("x" * 100000)'],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            with self.assertRaises(OverflowError):
                _communicate_bounded(proc, b'{}', 2)
        finally:
            proc.kill()
            proc.wait()
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                stream.close()

    def test_timeout_cleans_container(self):
        with patch('backend.execution.subprocess.Popen') as popen, \
             patch('backend.execution._communicate_bounded', side_effect=subprocess.TimeoutExpired('docker', 6)), \
             patch('backend.execution.subprocess.run') as remove:
            popen.return_value.poll.return_value = None
            result = docker_evaluator('def solve(numbers): return numbers')({'numbers': []})
            self.assertEqual(result['status'], 'timeout')
            popen.return_value.kill.assert_called_once()
            self.assertEqual(remove.call_args.args[0][:3], ['docker', 'rm', '--force'])


@unittest.skipUnless(os.environ.get('LAB_DOCKER_TESTS') == '1' and readiness()['available'],
                     'Docker integration requires a built image and LAB_DOCKER_TESTS=1')
class DockerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.created = []
        def tracked_command(name):
            self.created.append(name)
            return docker_command(name)
        self.command_patch = patch('backend.execution.docker_command', side_effect=tracked_command)
        self.command_patch.start()
        self.addCleanup(self.command_patch.stop)

    def tearDown(self):
        # Only inspect containers created by this test, never unrelated containers.
        for name in self.created:
            result = subprocess.run(['docker', 'container', 'inspect', name], capture_output=True, timeout=5)
            self.assertNotEqual(result.returncode, 0, f'Container was not removed: {name}')

    def test_normal_exception_and_loop(self):
        self.assertEqual(docker_evaluator('def solve(numbers): return sorted(numbers)')({'numbers': [2, 1]}),
                         {'status': 'ok', 'value': [1, 2]})
        self.assertEqual(docker_evaluator('def solve(numbers): raise ValueError("test")')({'numbers': []})['status'], 'exception')
        self.assertIn(docker_evaluator('def solve(numbers):\n while True: pass')({'numbers': []})['status'], ('timeout', 'exception'))

    def test_wall_timeout(self):
        result = docker_evaluator('import time\ndef solve(numbers):\n time.sleep(60)\n return []')({'numbers': []})
        self.assertEqual(result['status'], 'timeout')

    def test_output_flood(self):
        result = docker_evaluator('import os\ndef solve(numbers):\n os.write(1, b"x" * 100000)\n return []')({'numbers': []})
        self.assertEqual(result['status'], 'invalid_output')

    def test_memory_limit(self):
        result = docker_evaluator('def solve(numbers):\n data = bytearray(256 * 1024 * 1024)\n return len(data)')({'numbers': []})
        self.assertEqual(result['status'], 'exception')

    def test_live_isolation_properties(self):
        code = '''import os
import resource
import socket
def solve(numbers):
    try:
        with open('/app/should-not-exist', 'w') as stream:
            stream.write('probe')
        readonly = False
    except OSError:
        readonly = True
    with open('/proc/self/status') as stream:
        status = dict(line.split(':', 1) for line in stream if ':' in line)
    probe = socket.socket()
    probe.settimeout(0.5)
    network_error = probe.connect_ex(('192.0.2.1', 9))
    probe.close()
    return {'uid': os.getuid(), 'readonly': readonly,
            'network_error': network_error,
            'capabilities': int(status['CapEff'].strip(), 16),
            'no_new_privileges': int(status['NoNewPrivs'].strip()),
            'cpu_limit': list(resource.getrlimit(resource.RLIMIT_CPU))}
'''
        result = docker_evaluator(code)({'numbers': []})
        self.assertEqual(result['status'], 'ok')
        value = result['value']
        self.assertEqual(value['uid'], 65534)
        self.assertTrue(value['readonly'])
        # Docker may expose inactive virtual interfaces. Test the actual property:
        # no route to the documentation-only TEST-NET address (Linux errno values).
        self.assertIn(value['network_error'], (101, 113))
        self.assertEqual(value['capabilities'], 0)
        self.assertEqual(value['no_new_privileges'], 1)
        self.assertEqual(value['cpu_limit'], [2, 2])

    def test_real_counterexample_and_repair_workflow(self):
        from backend.engine import discover, verify
        from backend.tasks import TASKS
        report = discover('sort', docker_evaluator(TASKS['sort']['buggy']), 42, 10, 80)
        self.assertEqual(report['status'], 'wrong_answer')
        self.assertEqual(report['shrink']['reduced']['input'], {'numbers': [0, 0]})
        self.assertEqual(report['shrink']['stop_reason'], 'local_fixed_point')
        result = verify('sort', docker_evaluator(TASKS['sort']['correct']), report, 12)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['passed'], 12)
        self.assertEqual(result['overlap_count'], 0)


if __name__ == '__main__':
    unittest.main()
