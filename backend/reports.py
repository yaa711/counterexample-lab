"""Experiment provenance and comparable manual-model feedback prompts."""
import hashlib
import json
from datetime import datetime, timezone

from .tasks import TASKS


def source_record(task, mode, variant, code):
    return {'mode': mode, 'variant': variant if mode == 'demo' else None, 'code': code,
            'sha256': hashlib.sha256(code.encode()).hexdigest(),
            'provenance': 'Hand-authored teaching example' if mode == 'demo' else 'User-provided code; model provenance unverified'}


def prompts(report):
    if report['status'] != 'wrong_answer':
        return {}
    task = TASKS[report['task']]
    common = (f"Repair this Python function. Return the complete corrected function.\n"
              f"Contract: {task['signature']}\n{task['description']}\n"
              f"Candidate:\n```python\n{report['source']['code']}\n```\n")
    result = {'failure_only': common + 'Feedback: the implementation failed a correctness test.\n'}
    for name, record in [('original', report['failure']), ('reduced', report['shrink']['reduced'])]:
        result[name] = common + ('Feedback: the implementation failed a correctness test.\n'
                                f"Input: {json.dumps(record['input'], ensure_ascii=False)}\n"
                                f"Expected: {json.dumps(record['expected'])}\n"
                                f"Actual: {json.dumps(record['actual'])}\n")
    return result


def timestamp():
    return datetime.now(timezone.utc).isoformat()
