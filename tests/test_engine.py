import copy
import unittest

from backend.tasks import TASKS, demo_evaluator, oracle, valid_case
from backend.engine import discover, generate_cases, measure, verify


class EngineTests(unittest.TestCase):
    def test_seeded_generation_and_constraints(self):
        for task in TASKS:
            cases = generate_cases(task, 42, 100)
            self.assertEqual(cases, generate_cases(task, 42, 100))
            self.assertEqual(len(cases), 100)
            self.assertTrue(all(valid_case(task, c) for c in cases))

    def test_oracles(self):
        self.assertEqual(oracle('sort', {'numbers': [2, 1, 2]}), [1, 2, 2])
        self.assertEqual(oracle('first_index', {'numbers': [1, 1, 2], 'target': 1}), 0)
        self.assertEqual(oracle('first_index', {'numbers': [], 'target': 1}), -1)
        self.assertEqual(oracle('max_subarray', {'numbers': [-4, -2, -7]}), -2)

    def test_correct_programs_pass(self):
        for task in TASKS:
            report = discover(task, demo_evaluator(task, 'correct'), 17, 150, 80)
            self.assertEqual(report['status'], 'passed')
            self.assertIsNone(report['failure'])
            self.assertEqual(report['tested'], 150)

    def test_shrinking_preserves_failure_and_strictly_decreases(self):
        for task in TASKS:
            run = discover(task, demo_evaluator(task, 'buggy'), 42, 100, 180)
            self.assertEqual(run['status'], 'wrong_answer')
            self.assertTrue(run['shrink']['stable'])
            steps = run['shrink']['steps']
            self.assertGreater(len(steps), 1)
            for before, after in zip(steps, steps[1:]):
                self.assertLess(measure(after['input']), measure(before['input']))
            for step in steps:
                self.assertTrue(valid_case(task, step['input']))
                self.assertNotEqual(step['expected'], step['actual'])
            self.assertLessEqual(run['shrink']['calls'], 180)

    def test_replay(self):
        a = discover('sort', demo_evaluator('sort', 'buggy'), 23, 100, 60)
        b = discover('sort', demo_evaluator('sort', 'buggy'), 23, 100, 60)
        self.assertEqual(a['tested_inputs'], b['tested_inputs'])
        self.assertEqual(a['shrink'], b['shrink'])

    def test_coordinated_simplification_keeps_duplicate_relationship(self):
        run = discover('sort', demo_evaluator('sort', 'buggy'), 42, 100, 100)
        self.assertEqual(run['shrink']['reduced']['input'], {'numbers': [0, 0]})

    def test_infrastructure_error_is_not_a_wrong_answer(self):
        run = discover('sort', lambda _: {'status': 'infrastructure_error', 'message': 'unavailable'}, 1, 10, 20)
        self.assertEqual(run['status'], 'infrastructure_error')
        self.assertIsNone(run['shrink'])

    def test_budget_is_honest(self):
        run = discover('sort', demo_evaluator('sort', 'buggy'), 42, 100, 1)
        self.assertEqual(run['shrink']['calls'], 1)
        self.assertEqual(run['shrink']['stop_reason'], 'budget_exhausted')

    def test_exception_is_not_shrunk(self):
        run = discover('sort', lambda _: {'status': 'exception', 'message': 'oops'}, 1, 10, 20)
        self.assertEqual(run['status'], 'exception')
        self.assertIsNone(run['shrink'])

    def test_exact_output_type(self):
        run = discover('first_index', lambda _: {'status': 'ok', 'value': True}, 1, 10, 20)
        self.assertEqual(run['status'], 'invalid_output')

    def test_verification_is_held_out_and_retains_source_report(self):
        run = discover('sort', demo_evaluator('sort', 'buggy'), 42, 100, 100)
        snapshot = copy.deepcopy(run)
        result = verify('sort', demo_evaluator('sort', 'correct'), run, 100)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['tested'], 100)
        excluded = run['tested_inputs'] + run['shrink']['evaluated_inputs']
        self.assertTrue(all(c not in excluded for c in result['tested_inputs']))
        self.assertEqual(result['overlap_count'], 0)
        self.assertNotEqual(run['seed'], result['seed'])
        self.assertEqual(run, snapshot)

    def test_non_determinism_prevents_shrinking(self):
        calls = 0
        def flaky(case):
            nonlocal calls
            calls += 1
            return {'status': 'ok', 'value': [] if calls == 1 else sorted(case['numbers'])}
        run = discover('sort', flaky, 42, 100, 80)
        self.assertFalse(run['shrink']['stable'])
        self.assertEqual(run['shrink']['stop_reason'], 'unstable_failure')


if __name__ == '__main__':
    unittest.main()
