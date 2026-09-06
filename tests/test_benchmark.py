import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.compare import DEFAULT_FIXTURES, load_candidates, run_trial, summary, save
from backend.tasks import demo_evaluator


class BenchmarkTests(unittest.TestCase):
    def test_fixture_contracts_and_controls(self):
        candidates = load_candidates(DEFAULT_FIXTURES)
        self.assertEqual(len(candidates), 12)
        self.assertEqual(sum(c['kind'] == 'control' for c in candidates), 3)
        self.assertEqual({c['task'] for c in candidates}, {'sort', 'first_index', 'max_subarray'})
        self.assertTrue(all(c['source'] and c['reason'] for c in candidates))

    def test_corrupt_witness_rejected_before_execution(self):
        data = json.loads(DEFAULT_FIXTURES.read_text())
        data['candidates'][0]['witness']['expected'] = []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.json'
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'oracle'):
                load_candidates(path)

    def test_pair_uses_same_discovery_and_counts_confirmation(self):
        item = load_candidates(DEFAULT_FIXTURES)[0]
        evaluator = demo_evaluator('sort', 'buggy')
        with patch('benchmarks.compare.discover', wraps=__import__('backend.engine', fromlist=['discover']).discover) as search:
            trial = run_trial(item, 42, 20, 30, 10, evaluator)
        search.assert_called_once()
        self.assertEqual(len(trial['paired']), 2)
        for pair in trial['paired']:
            self.assertEqual(pair['reduction']['steps'][0]['input'], trial['discovery']['failure']['input'])
            self.assertLessEqual(pair['reduction']['calls'], 30)
            self.assertEqual(pair['audit_calls'], 1)
            self.assertTrue(pair['valid'])
        reversed_trial = run_trial(item, 7, 20, 30, 10, evaluator)
        self.assertEqual(trial['strategy_order'], list(reversed(reversed_trial['strategy_order'])))

    def test_missing_failures_remain_in_summary(self):
        item = load_candidates(DEFAULT_FIXTURES)[0]
        found = run_trial(item, 42, 20, 20, 10, demo_evaluator('sort', 'buggy'))
        missed = run_trial(item, 7, 20, 20, 10, demo_evaluator('sort', 'correct'))
        self.assertEqual(missed['paired'], [])
        report = {'planned_trials': 4, 'trials': [found, missed]}
        result = summary(report)
        self.assertEqual(result['discovery_rate'], .5)
        self.assertEqual(result['completed_trials'], 2)
        self.assertEqual(result['planned_trials'], 4)
        self.assertEqual(result['by_program'][0]['runs'], 2)

    def test_partial_report_can_be_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'
            save({'complete': False, 'planned_trials': 24, 'trials': []}, path)
            report = json.loads(path.read_text())
            self.assertFalse(report['complete'])
            self.assertIsNone(report['summary']['discovery_rate'])
            self.assertFalse(path.with_suffix('.json.tmp').exists())


if __name__ == '__main__':
    unittest.main()
