"""Reproducible differential testing and budgeted counterexample reduction.

The engine owns the oracle. Evaluators receive only the input, never expected output.
"""
import copy
import json
import random
import time

from .tasks import oracle, valid_case, valid_output

GENERATOR_VERSION = '1.0'


def key(case):
    return json.dumps(case, sort_keys=True, separators=(',', ':'))


def generate_cases(task, seed, count, excluded=()):
    # A private generator makes a run replayable without changing global RNG state.
    # Boundary cases expose known classes of bugs; random cases broaden coverage.
    rng = random.Random(seed)
    edges = {
        'sort': [[8, 3, -2, 8, 5, 3, 0, -2, 9, 5, 1, 8], [], [0], [0, 0], [-1, 1]],
        'first_index': [[-4, -1, 2, 2, 2, 2, 2, 6, 9], [], [0], [0, 0], [-1, 0, 1]],
        'max_subarray': [[-8, -3, -6, -2, -5, -4, -9, -1], [0], [-1], [1], [-2, 3, -1, 4, -8]],
    }[task]
    seen = set(excluded)
    result = []
    for attempt in range(count * 40 + len(edges)):
        if len(result) >= count:
            break
        numbers = edges[attempt][:] if attempt < len(edges) else [
            rng.randint(-12, 12) for _ in range(rng.randint(1 if task == 'max_subarray' else 0, 16))]
        if task == 'first_index':
            numbers.sort()
        case = {'numbers': numbers}
        if task == 'first_index':
            case['target'] = 2 if attempt == 0 else (
                rng.choice(numbers) if numbers and rng.random() < .65 else rng.randint(-12, 12))
        identity = key(case)
        if identity not in seen:
            result.append(case)
            seen.add(identity)
    return result


def measure(case):
    # Python compares tuples lexicographically: shorten the array first, then
    # simplify its values. Strict descent over nonnegative integers prevents cycles.
    # This guarantees progress, not the globally smallest failing input.
    return (len(case['numbers']), sum(abs(n) for n in case['numbers']) + abs(case.get('target', 0)))


def check(task, evaluator, case):
    # Compute the oracle outside the candidate process. Pass a copy so an in-place
    # candidate cannot mutate the evidence used to explain or reproduce its result.
    expected = oracle(task, case)
    result = evaluator(copy.deepcopy(case))
    record = {'input': copy.deepcopy(case), 'expected': expected, 'actual': result.get('value')}
    if result['status'] != 'ok':
        return {**record, 'status': result['status'], 'message': result.get('message', '')}
    if not valid_output(task, result.get('value')):
        return {**record, 'status': 'invalid_output', 'message': 'The return value violates the contract type or size limit.'}
    return {**record, 'status': 'passed' if result['value'] == expected else 'wrong_answer'}


def _simplifications(case):
    numbers = case['numbers']
    size = max(1, len(numbers) // 2)
    yielded = set()
    while size >= 1:
        for start in range(0, len(numbers), size):
            candidate = {**case, 'numbers': numbers[:start] + numbers[start + size:]}
            if key(candidate) not in yielded:
                yielded.add(key(candidate))
                yield candidate, f'Remove {min(size, len(numbers) - start)} element(s) at index {start}'
        if size == 1:
            break
        size = max(1, size // 2)
    # Coordinated simplification preserves relationships such as duplicate values
    # or equality with a search target that single-element changes would destroy.
    for transform, reason in [(lambda n: 0, 'Replace all values with zero'),
                              (lambda n: (1 if n > 0 else -1 if n < 0 else 0), 'Reduce all values to their signs'),
                              (lambda n: int(n / 2), 'Halve all values')]:
        candidate = {**case, 'numbers': [transform(n) for n in numbers]}
        if 'target' in case:
            candidate['target'] = transform(case['target'])
        yield candidate, reason
    for index, value in enumerate(numbers):
        for replacement in dict.fromkeys([0, (1 if value > 0 else -1), int(value / 2)]):
            new_numbers = numbers[:]
            new_numbers[index] = replacement
            yield {**case, 'numbers': new_numbers}, f'Index {index}: {value} → {replacement}'
    if 'target' in case:
        for target in dict.fromkeys([0, 1 if case['target'] > 0 else -1, int(case['target'] / 2)]):
            yield {**case, 'target': target}, f"Target: {case['target']} → {target}"


def shrink(task, evaluator, failure, budget, deadline):
    current = failure
    steps = [{**failure, 'reason': 'Original input', 'call': 0}]
    evaluated = []
    stable = False
    stop_reason = 'local_fixed_point'

    def evaluate(case):
        if len(evaluated) >= budget:
            raise StopIteration('budget_exhausted')
        if time.monotonic() >= deadline:
            raise StopIteration('time_limit')
        evaluated.append(copy.deepcopy(case))
        return check(task, evaluator, case)

    try:
        # Recheck twice before using the original error as an experimental witness.
        for _ in range(2):
            repeat = evaluate(current['input'])
            if repeat != failure:
                raise StopIteration('unstable_failure')
        stable = True
        while True:
            improved = False
            for candidate, reason in _simplifications(current['input']):
                if not valid_case(task, candidate) or measure(candidate) >= measure(current['input']):
                    continue
                result = evaluate(candidate)
                if result['status'] == 'infrastructure_error':
                    raise StopIteration('infrastructure_error')
                if result['status'] != 'wrong_answer':
                    continue
                # A one-off random error must not be accepted as a stable reduction.
                repeat = evaluate(candidate)
                if repeat != result:
                    raise StopIteration('unstable_failure')
                current = result
                steps.append({**result, 'reason': reason, 'call': len(evaluated)})
                improved = True
                # Restart from the smaller witness: transformations rejected for
                # the previous input may become useful after another deletion.
                break
            if not improved:
                break
    except StopIteration as stopped:
        stop_reason = str(stopped)
    return {'stable': stable and stop_reason != 'unstable_failure', 'steps': steps,
            'calls': len(evaluated), 'evaluated_inputs': evaluated, 'budget': budget,
            'stop_reason': stop_reason, 'reduced': current,
            'claim': 'Locally reduced, not guaranteed globally minimal. More reduction may be possible if the budget or time limit was reached.'}


def discover(task, evaluator, seed, count, shrink_budget, seconds=50):
    started = time.monotonic()
    deadline = started + seconds
    cases = generate_cases(task, seed, count)
    tested_inputs = []
    failure = None
    status = 'passed'
    for case in cases:
        if time.monotonic() >= deadline:
            status = 'incomplete'
            break
        record = check(task, evaluator, case)
        tested_inputs.append(case)
        if record['status'] != 'passed':
            failure = record
            status = record['status']
            break
    reduction = shrink(task, evaluator, failure, shrink_budget, deadline) if status == 'wrong_answer' else None
    if failure is None and len(tested_inputs) < count:
        status = 'incomplete'
    return {'task': task, 'seed': seed, 'requested': count, 'tested': len(tested_inputs),
            'generator_version': GENERATOR_VERSION, 'generator': {'max_length': 16, 'value_range': [-12, 12], 'deduplicated': True},
            'status': status, 'tested_inputs': tested_inputs, 'failure': failure,
            'shrink': reduction, 'elapsed_ms': round((time.monotonic() - started) * 1000, 2)}


def verify(task, evaluator, discovery, count, seconds=50):
    started = time.monotonic()
    # XOR with a nonzero constant gives a distinct, reproducible validation seed.
    # A new seed alone does not prevent overlap, so explicitly exclude every input
    # already evaluated, including rejected shrink attempts that could leak feedback.
    seed = (discovery['seed'] ^ 0x5EED1234) & 0xFFFFFFFF
    excluded = list(discovery['tested_inputs'])
    if discovery['shrink']:
        excluded += discovery['shrink']['evaluated_inputs']
    excluded_keys = {key(c) for c in excluded}
    cases = generate_cases(task, seed, count, excluded_keys)
    records = []
    for case in cases:
        if time.monotonic() - started >= seconds:
            break
        records.append(check(task, evaluator, case))
        if records[-1]['status'] in ('infrastructure_error', 'timeout'):
            break
    failures = [r for r in records if r['status'] != 'passed']
    return {'seed': seed, 'requested': count, 'tested': len(records),
            'passed': sum(r['status'] == 'passed' for r in records),
            'status': (failures[0]['status'] if failures else 'passed' if len(records) == count else 'incomplete'),
            'failures': failures, 'tested_inputs': [r['input'] for r in records],
            'excluded_count': len(excluded_keys),
            'overlap_count': sum(key(r['input']) in excluded_keys for r in records),
            'elapsed_ms': round((time.monotonic() - started) * 1000, 2),
            'claim': 'Passing held-out tests is not a proof. Re-verifying this run reuses the same test set; do not tune against it.'}
