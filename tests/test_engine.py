import copy
import unittest
import time
from unittest.mock import patch

from backend.tasks import TASKS, demo_evaluator, oracle, valid_case
from backend.engine import discover, generate_cases, measure, verify, shrink, _simplifications, check


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
        for run in (a, b):
            self.assertGreaterEqual(run['shrink'].pop('elapsed_ms'), 0)
            for attempt in run['shrink']['attempts']:
                self.assertGreaterEqual(attempt.pop('elapsed_ms'), 0)
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

    def test_strategies_preserve_invariants_across_evaluation_seeds(self):
        for task in TASKS:
            for seed in range(12):
                for strategy in ('single', 'block'):
                    run = discover(task, demo_evaluator(task, 'buggy'), seed, 100, 60,
                                   strategy=strategy, profile='evaluation')
                    if run['shrink'] is None:
                        continue
                    reduced = run['shrink']
                    self.assertLessEqual(reduced['calls'], 60)
                    self.assertEqual(run['candidate_calls'], run['tested'] + reduced['calls'])
                    self.assertEqual(reduced['calls'], sum(a['call'] is not None for a in reduced['attempts']))
                    self.assertEqual(run['tested'], len(run['tested_inputs']))
                    self.assertTrue(valid_case(task, reduced['reduced']['input']))
                    self.assertEqual(check(task, demo_evaluator(task, 'buggy'), reduced['reduced']['input'])['status'], 'wrong_answer')
                    for before, after in zip(reduced['steps'], reduced['steps'][1:]):
                        self.assertLess(measure(after['input']), measure(before['input']))
                    result = verify(task, demo_evaluator(task, 'correct'), run, 20)
                    self.assertEqual(result['overlap_count'], 0)
                    self.assertEqual(result['status'], 'passed')

    def test_both_strategies_share_value_simplifications(self):
        case = {'numbers': [8, -4, 2, 1], 'target': 2}
        single = list(_simplifications(case, 'single'))
        block = list(_simplifications(case, 'block'))
        values = lambda items: [(c, why) for c, why in items if not why.startswith('Remove')]
        self.assertEqual(values(single), values(block))
        self.assertTrue(all('Remove 1 element' in why for _, why in single if why.startswith('Remove')))
        self.assertTrue(any('Remove 2 element' in why for _, why in block))

    def test_rejected_and_skipped_attempts_are_explained(self):
        run = discover('max_subarray', demo_evaluator('max_subarray', 'buggy'), 42, 100, 100)
        attempts = run['shrink']['attempts']
        self.assertTrue(any(a['decision'] == 'invalid_input' and a['call'] is None for a in attempts))
        self.assertTrue(any(a['decision'] == 'rejected' and a['status'] == 'passed' for a in attempts))
        self.assertEqual(sum(a['decision'] == 'accepted' for a in attempts), len(run['shrink']['steps']) - 1)

    def test_budget_cannot_accept_unconfirmed_proposal(self):
        evaluator = demo_evaluator('sort', 'buggy')
        failure = check('sort', evaluator, {'numbers': [1, 1, 2, 2]})
        result = shrink('sort', evaluator, failure, 3, time.monotonic() + 10)
        self.assertEqual(result['stop_reason'], 'budget_exhausted')
        self.assertEqual(len(result['steps']), 1)
        self.assertEqual(result['attempts'][-1]['decision'], 'unconfirmed')

    def test_deadline_and_zero_budget_do_not_evaluate(self):
        failure = check('sort', demo_evaluator('sort', 'buggy'), {'numbers': [1, 1]})
        for budget, deadline, reason in [(0, time.monotonic()+10, 'budget_exhausted'),
                                         (10, time.monotonic()-1, 'time_limit')]:
            with patch('backend.engine.check') as evaluate:
                result = shrink('sort', None, failure, budget, deadline)
                evaluate.assert_not_called()
                self.assertEqual(result['stop_reason'], reason)
                self.assertFalse(result['stable'])

    def test_evaluation_profile_is_reproducible_without_teaching_prefix(self):
        for task in TASKS:
            cases = generate_cases(task, 42, 40, profile='evaluation')
            self.assertEqual(cases, generate_cases(task, 42, 40, profile='evaluation'))
            self.assertNotEqual(cases[0], generate_cases(task, 42, 1)[0])
            self.assertTrue(all(valid_case(task, case) for case in cases))
        with self.assertRaises(ValueError):
            generate_cases('sort', 0, 10, profile='unknown')
        with self.assertRaises(ValueError):
            discover('sort', None, 0, 10, 10, strategy='unknown')


if __name__ == '__main__':
    unittest.main()
