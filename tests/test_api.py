import http.client
import json
import threading
import unittest
from unittest.mock import patch

from backend.server import LabServer


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = LabServer(('127.0.0.1', 0))
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self, path, data=None, headers=None, raw=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        body = raw if raw is not None else json.dumps(data) if data is not None else None
        conn.request('POST' if body is not None else 'GET', path, body,
                     {'Content-Type': 'application/json', **(headers or {})})
        response = conn.getresponse()
        status, result = response.status, json.loads(response.read())
        conn.close()
        return status, result

    def test_complete_demo_flow(self):
        status, report = self.request('/api/run', {'task': 'sort'})
        self.assertEqual(status, 200)
        self.assertEqual(report['status'], 'wrong_answer')
        self.assertEqual(set(report['prompts']), {'original', 'reduced', 'failure_only'})
        status, result = self.request('/api/verify', {'run_id': report['run_id'], 'variant': 'correct'})
        self.assertEqual(status, 200)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['overlap_count'], 0)

    def test_forbidden_origin(self):
        self.assertEqual(self.request('/api/run', {'task': 'sort'}, {'Origin': 'https://evil.example'})[0], 403)

    def test_forbidden_host(self):
        self.assertEqual(self.request('/api/tasks', headers={'Host': 'evil.example'})[0], 403)

    def test_invalid_requests(self):
        for data in [{'task': 'missing'}, {'task': []}, {'task': 'sort', 'seed': True}, {'task': 'sort', 'count': 501}]:
            self.assertEqual(self.request('/api/run', data)[0], 400)
        self.assertEqual(self.request('/api/run', raw='{')[0], 400)
        self.assertEqual(self.request('/api/run', raw='x' * 65537)[0], 413)
        self.assertEqual(self.request('/api/verify', {'run_id': 'absent'})[0], 404)

    def test_custom_code_never_falls_back_to_host(self):
        with patch('backend.server.readiness', return_value={'available': False, 'reason': 'disabled'}), \
             patch('backend.server.docker_evaluator') as evaluator:
            status, _ = self.request('/api/run', {'task': 'sort', 'mode': 'custom', 'code': 'raise RuntimeError()'})
            self.assertEqual(status, 503)
            evaluator.assert_not_called()

    def test_demo_does_not_execute_supplied_code(self):
        status, report = self.request('/api/run', {'task': 'sort', 'mode': 'demo', 'code': 'raise RuntimeError()'})
        self.assertEqual(status, 200)
        self.assertNotIn('raise RuntimeError', report['source']['code'])


if __name__ == '__main__':
    unittest.main()
