"""Run paired reduction experiments; never import or exec candidate source on host."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from backend.engine import GENERATOR_VERSION, STRATEGIES, check, discover, key, measure, shrink
from backend.execution import IMAGE, docker_evaluator, readiness
from backend.tasks import TASKS, oracle, valid_case, valid_output

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = ROOT / 'benchmarks' / 'candidates.json'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_candidates(path):
    document = json.loads(path.read_text())
    if document.get('schema_version') != '1.0':
        raise ValueError('Unsupported fixture schema')
    candidates = document['candidates']
    ids = set()
    for item in candidates:
        if not isinstance(item['id'], str) or item['id'] in ids:
            raise ValueError('Candidate IDs must be unique strings')
        ids.add(item['id'])
        if item['task'] not in TASKS or item['kind'] not in ('buggy', 'control'):
            raise ValueError('Unknown task or candidate kind')
        if not isinstance(item['code'], str) or not 0 < len(item['code'].encode()) <= 24000:
            raise ValueError('Candidate source must be 1..24000 bytes')
        witness = item['witness']
        if not valid_case(item['task'], witness['input']):
            raise ValueError('Invalid witness input')
        if not valid_output(item['task'], witness['expected']) or witness['expected'] != oracle(item['task'], witness['input']):
            raise ValueError('Witness expected value disagrees with the oracle')
        if (witness['actual'] == witness['expected']) != (item['kind'] == 'control'):
            raise ValueError('Witness does not match the declared candidate kind')
    return candidates


def run_trial(item, seed, count, budget, seconds, evaluator):
    # Discovery is shared, not repeated separately for each strategy. The fixture's
    # manual witness is not passed to discovery or either reduction strategy.
    discovery = discover(item['task'], evaluator, seed, count, 0, seconds,
                         profile='evaluation')
    paired = []
    order = list(STRATEGIES)
    if seed % 2:
        order.reverse()
    if item['kind'] == 'buggy' and discovery['status'] == 'wrong_answer':
        for strategy in order:
            result = shrink(item['task'], evaluator, discovery['failure'], budget,
                            time.monotonic() + seconds, strategy)
            # This independent audit is outside the strategy budget and explicitly
            # counted separately. A changed/error result invalidates the pair.
            audit = check(item['task'], evaluator, result['reduced']['input'])
            valid = result['stable'] and audit == result['reduced']
            valid = valid and all(measure(b['input']) < measure(a['input'])
                                  for a, b in zip(result['steps'], result['steps'][1:]))
            paired.append({'strategy': strategy, 'reduction': result, 'audit': audit,
                           'audit_calls': 1, 'valid': valid})
    return {'candidate_id': item['id'], 'kind': item['kind'], 'task': item['task'],
            'seed': seed, 'source_sha256': digest(item['code'].encode()),
            'discovery': discovery, 'strategy_order': order, 'paired': paired}


def summary(report):
    trials = report['trials']
    buggy = [r for r in trials if r['kind'] == 'buggy']
    found = [r for r in buggy if r['discovery']['status'] == 'wrong_answer']
    controls = [r for r in trials if r['kind'] == 'control']
    valid_pairs = [r for r in found if len(r['paired']) == 2 and all(p['valid'] for p in r['paired'])]
    failures = [r for r in trials if r['discovery']['status'] in ('infrastructure_error', 'timeout', 'exception', 'invalid_output')]
    by_program = []
    for id in sorted({r['candidate_id'] for r in trials}):
        runs = [r for r in trials if r['candidate_id'] == id]
        by_program.append({'candidate_id': id, 'kind': runs[0]['kind'], 'runs': len(runs),
                           'wrong_answer_runs': sum(r['discovery']['status'] == 'wrong_answer' for r in runs),
                           'completed_pass_runs': sum(r['discovery']['status'] == 'passed' for r in runs)})
    return {'completed_trials': len(trials), 'planned_trials': report['planned_trials'],
            'buggy_trials': len(buggy), 'wrong_answer_trials': len(found),
            'discovery_rate': len(found)/len(buggy) if buggy else None,
            'control_trials': len(controls),
            'controls_passed': sum(r['discovery']['status'] == 'passed' for r in controls),
            'valid_pairs': len(valid_pairs), 'execution_failure_trials': len(failures),
            'by_program': by_program}


def save(report, path):
    report['summary'] = summary(report)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def positive(value):
    number = int(value)
    if not 1 <= number <= 500:
        raise argparse.ArgumentTypeError('Must be between 1 and 500')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=DEFAULT_FIXTURES)
    parser.add_argument('--seeds', type=int, nargs='+', default=[7, 42])
    parser.add_argument('--count', type=positive, default=20)
    parser.add_argument('--budget', type=positive, default=40)
    parser.add_argument('--seconds', type=positive, default=90)
    parser.add_argument('--only', nargs='+', help='Explicit subset of candidate IDs')
    parser.add_argument('--output', type=Path, default=ROOT / 'artifacts/comparison.json')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output exists; choose a new path to retain the earlier experiment')
    if len(set(args.seeds)) != len(args.seeds) or any(not 0 <= seed < 2**32 for seed in args.seeds):
        parser.error('Seeds must be distinct integers in 0..2**32-1')
    candidates = load_candidates(args.fixtures)
    if args.only:
        if set(args.only) - {c['id'] for c in candidates}:
            parser.error('Unknown candidate ID')
        candidates = [c for c in candidates if c['id'] in args.only]
    state = readiness()
    if not state['available']:
        parser.error(state['reason'])
    image = subprocess.run(['docker', 'image', 'inspect', IMAGE, '--format', '{{.Id}}'],
                           capture_output=True, text=True, timeout=5, check=True).stdout.strip()
    report = {'schema_version': '1.0', 'created_at': datetime.now(timezone.utc).isoformat(),
              'complete': False, 'generator_version': GENERATOR_VERSION,
              'environment': {'python': platform.python_version(), 'system': platform.system(),
                              'machine': platform.machine(), 'runner_image_id': image},
              'implementation_sha256': {p: digest((ROOT/p).read_bytes()) for p in
                                       ['backend/engine.py', 'backend/tasks.py', 'backend/execution.py',
                                        'runner/worker.py', 'benchmarks/compare.py']},
              'config': {'seeds': args.seeds, 'count': args.count, 'shrink_budget': args.budget,
                         'seconds_per_phase': args.seconds, 'generator_profile': 'evaluation',
                         'strategies': list(STRATEGIES)},
              'fixture_sha256': digest(args.fixtures.read_bytes()), 'candidates': candidates,
              'planned_trials': len(candidates)*len(args.seeds), 'witness_checks': [], 'trials': []}
    save(report, args.output)
    try:
        for item in candidates:
            evaluator = docker_evaluator(item['code'])
            witness = check(item['task'], evaluator, item['witness']['input'])
            report['witness_checks'].append({'candidate_id': item['id'], 'result': witness, 'calls': 1})
            expected_status = 'wrong_answer' if item['kind'] == 'buggy' else 'passed'
            if witness['actual'] != item['witness']['actual'] or witness['status'] != expected_status:
                raise RuntimeError('Declared witness could not be reproduced: ' + item['id'])
            for seed in args.seeds:
                trial = run_trial(item, seed, args.count, args.budget, args.seconds, evaluator)
                report['trials'].append(trial)
                save(report, args.output)
                print(f"{item['id']} seed={seed}: {trial['discovery']['status']}, {len(trial['paired'])} reductions", flush=True)
        report['complete'] = True
        save(report, args.output)
    except (Exception, KeyboardInterrupt) as error:
        report['error'] = type(error).__name__ + ': ' + str(error)
        save(report, args.output)
        raise
    issues = report['summary']['execution_failure_trials'] or any(
        (r['kind'] == 'control' and r['discovery']['status'] != 'passed') or
        any(not p['valid'] for p in r['paired']) for r in report['trials'])
    print(json.dumps(report['summary'], indent=2))
    return 1 if issues else 0


if __name__ == '__main__':
    sys.exit(main())
