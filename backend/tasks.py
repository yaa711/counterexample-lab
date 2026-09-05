"""Small explicit contracts and deliberately simple independent reference algorithms."""
from copy import deepcopy


TASKS = {
    'sort': {
        'name': 'Array sorting', 'tag': 'ARRAYS', 'level': 'CS 128 / 225',
        'description': 'Return an ascending array, preserving every value and its frequency. Empty arrays are valid.',
        'signature': 'solve(numbers: list[int]) -> list[int]',
        'bug': 'Using set removes duplicates: ordering is correct but multiplicity is lost.',
        'buggy': 'def solve(numbers):\n    # Can you spot the missing invariant?\n    return sorted(set(numbers))\n',
        'correct': 'def solve(numbers):\n    return sorted(numbers)\n',
    },
    'first_index': {
        'name': 'Binary search', 'tag': 'SEARCH', 'level': 'CS 173 / 225',
        'description': 'Return the first index of target in a sorted array, or -1 if it is absent.',
        'signature': 'solve(numbers: list[int], target: int) -> int',
        'bug': 'Returning on the first equality can select the middle of a group of duplicates.',
        'buggy': 'def solve(numbers, target):\n    lo, hi = 0, len(numbers) - 1\n    while lo <= hi:\n        mid = (lo + hi) // 2\n        if numbers[mid] == target:\n            return mid\n        if numbers[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid - 1\n    return -1\n',
        'correct': 'def solve(numbers, target):\n    lo, hi = 0, len(numbers)\n    while lo < hi:\n        mid = (lo + hi) // 2\n        if numbers[mid] < target:\n            lo = mid + 1\n        else:\n            hi = mid\n    return lo if lo < len(numbers) and numbers[lo] == target else -1\n',
    },
    'max_subarray': {
        'name': 'Maximum subarray', 'tag': 'DYNAMIC PROGRAMMING', 'level': 'CS 225 / MATH 314',
        'description': 'Return the largest sum of a non-empty contiguous subarray. All values may be negative.',
        'signature': 'solve(numbers: list[int]) -> int',
        'bug': 'Initializing the best sum to zero incorrectly allows an empty subarray.',
        'buggy': 'def solve(numbers):\n    best = current = 0\n    for number in numbers:\n        current = max(number, current + number)\n        best = max(best, current)\n    return best\n',
        'correct': 'def solve(numbers):\n    best = current = numbers[0]\n    for number in numbers[1:]:\n        current = max(number, current + number)\n        best = max(best, current)\n    return best\n',
    },
}


def valid_case(task, case):
    if task not in TASKS or not isinstance(case, dict):
        return False
    numbers = case.get('numbers')
    if not isinstance(numbers, list) or len(numbers) > 32:
        return False
    if any(type(n) is not int or abs(n) > 100 for n in numbers):
        return False
    if task == 'max_subarray' and not numbers:
        return False
    if task == 'first_index':
        return (numbers == sorted(numbers) and type(case.get('target')) is int
                and abs(case['target']) <= 100)
    return True


def oracle(task, case):
    numbers = case['numbers']
    if task == 'sort':
        return sorted(numbers)
    if task == 'first_index':
        return next((i for i, n in enumerate(numbers) if n == case['target']), -1)
    # Independent brute-force oracle: O(n^2) subarrays, O(n) slicing/summing each,
    # hence O(n^3) time. Inputs are deliberately small (at most 16 generated items).
    # Simplicity matters here: reusing the candidate's recurrence could repeat its bug.
    return max(sum(numbers[i:j]) for i in range(len(numbers)) for j in range(i + 1, len(numbers) + 1))


def valid_output(task, value):
    if task == 'sort':
        return isinstance(value, list) and len(value) <= 64 and all(type(x) is int for x in value)
    return type(value) is int


def _sort_bug(numbers):
    return sorted(set(numbers))


def _sort_correct(numbers):
    return sorted(numbers)


def _first_bug(numbers, target):
    lo, hi = 0, len(numbers) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if numbers[mid] == target:
            return mid
        if numbers[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1


def _first_correct(numbers, target):
    lo, hi = 0, len(numbers)
    while lo < hi:
        mid = (lo + hi) // 2
        if numbers[mid] < target:
            lo = mid + 1
        else:
            hi = mid
    return lo if lo < len(numbers) and numbers[lo] == target else -1


def _max_bug(numbers):
    best = current = 0
    for number in numbers:
        current = max(number, current + number)
        best = max(best, current)
    return best


def _max_correct(numbers):
    best = current = numbers[0]
    for number in numbers[1:]:
        current = max(number, current + number)
        best = max(best, current)
    return best


_DEMOS = {
    ('sort', 'buggy'): _sort_bug,
    ('sort', 'correct'): _sort_correct,
    ('first_index', 'buggy'): _first_bug,
    ('first_index', 'correct'): _first_correct,
    ('max_subarray', 'buggy'): _max_bug,
    ('max_subarray', 'correct'): _max_correct,
}


def demo_evaluator(task, variant):
    """Fixed callables only. Source strings above are display artifacts, never exec'd."""
    fn = _DEMOS[(task, variant)]
    def evaluate(case):
        return {'status': 'ok', 'value': fn(**deepcopy(case))}
    return evaluate


def catalog():
    return [{'id': key, **value, 'provenance': 'Hand-authored teaching example, not a model benchmark result'}
            for key, value in TASKS.items()]
