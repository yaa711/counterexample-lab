"""Print a paired-results table from saved evidence; does not execute candidates."""
import argparse
import json
from collections import Counter
from pathlib import Path
from statistics import median

from .compare import summary


def render(report):
    counts = summary(report)
    lines = ['# Paired reduction pilot', '',
             f"Completed trials: {counts['completed_trials']}/{counts['planned_trials']}. Report complete: {report['complete']}.",
             f"Wrong answers discovered: {counts['wrong_answer_trials']}/{counts['buggy_trials']} buggy-program/seed trials.",
             f"Correct controls passing: {counts['controls_passed']}/{counts['control_trials']} trials.",
             f"Valid paired reductions: {counts['valid_pairs']}. Execution-failure trials: {counts['execution_failure_trials']}.", '',
             'Only pairs with two independently audited, stable failures enter the table below.', '',
             '| Strategy | Paired runs | Total calls | Median calls | Local fixed points | Budget exhausted | Total seconds |',
             '|---|---:|---:|---:|---:|---:|---:|']
    pairs = [t for t in report['trials'] if len(t['paired']) == 2 and all(p['valid'] for p in t['paired'])]
    for strategy in report['config']['strategies']:
        reductions = [p['reduction'] for t in pairs for p in t['paired'] if p['strategy'] == strategy]
        stops = Counter(r['stop_reason'] for r in reductions)
        calls = [r['calls'] for r in reductions]
        lines.append(f"| {strategy} | {len(calls)} | {sum(calls)} | {median(calls) if calls else 'n/a'} | {stops['local_fixed_point']} | {stops['budget_exhausted']} | {sum(r['elapsed_ms'] for r in reductions)/1000:.2f} |")
    lines += ['', 'Calls include original-failure confirmations and proposed-reduction confirmations. The independent final audit adds one call per strategy and is excluded above.', '',
              '## Every program', '', '| Candidate | Kind | Runs | Wrong answers found | All requested tests passed |', '|---|---|---:|---:|---:|']
    for item in counts['by_program']:
        lines.append(f"| {item['candidate_id']} | {item['kind']} | {item['runs']} | {item['wrong_answer_runs']} | {item['completed_pass_runs']} |")
    lines += ['', 'A passing run for a known buggy program means discovery missed its bug in that sample.', '',
              '## Paired details', '', '| Candidate | Seed | Initial complexity | Single: final / calls / stop | Block: final / calls / stop |', '|---|---:|---|---|---|']
    for trial in pairs:
        p = {item['strategy']: item['reduction'] for item in trial['paired']}
        cells = [f"{p[s]['reduced_measure']} / {p[s]['calls']} / {p[s]['stop_reason']}" for s in ('single','block')]
        lines.append(f"| {trial['candidate_id']} | {trial['seed']} | {p['single']['original_measure']} | {cells[0]} | {cells[1]} |")
    lines += ['', 'Complexity is the lexicographic pair (array length, sum of absolute values including target). Seeds within one program are repeated measurements, not independent programs.']
    return '\n'.join(lines)+'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    print(render(json.loads(args.report.read_text())), end='')


if __name__ == '__main__':
    main()
