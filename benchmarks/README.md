# Reduction comparison

The benchmark compares `single` and `block` deletion with identical value transformations. It contains nine hand-written faulty Python functions and three correct controls across sorting, first-index search, and maximum subarray. It does not sample real-world bugs or model-generated programs.

Every candidate includes a documented witness. The loader checks that witness against the host oracle; the CLI then reproduces the declared output inside Docker. Witnesses are used only to validate fixtures. They are never fed to discovery or reduction.

## Run

Start Docker and build the runner from the repository root:

```sh
docker build -t counterexample-lab-runner:1 runner
python3 -m benchmarks.compare --seeds 7 42 --count 12 --budget 30 --seconds 90 --output artifacts/comparison.json
python3 -m benchmarks.summarize artifacts/comparison.json
```

The output path must not exist. Each completed trial is checkpointed; an interrupted report remains marked `complete: false`. Candidate source always runs in isolated containers, including the correct controls. The command has no host-execution fallback.

A smaller smoke run:

```sh
python3 -m benchmarks.compare --only sort-drop-last sort-control --seeds 42 --count 4 --budget 10 --output artifacts/smoke.json
```

## What is controlled

For each candidate and seed, discovery runs once with the `evaluation` profile and no reduction. The profile starts with random arrays, then generic boundary inputs. It does not include the long teaching fixtures. Correct programs and missed bugs remain in the report.

When discovery finds a wrong answer, both strategies receive that exact record, the same call budget, and the same per-phase wall-time limit. Odd and even seeds reverse strategy order. This simple alternation reduces a fixed order bias; it is not a randomized timing study.

Both strategies confirm the original failure twice and each accepted proposal once more. These evaluations consume the budget. Both restart their transformation sequence after accepting a reduction, use the same value transformations, and stop at a local fixed point, budget exhaustion, timeout, instability, or infrastructure failure. A final audit runs separately and adds one explicitly recorded call per strategy.

The complexity measure is `(array length, sum of absolute array values + absolute target)`, compared lexicographically. A shorter array takes priority over smaller values. A local fixed point only refers to the implemented transformations; neither strategy guarantees a globally minimal counterexample.

## Reading the results

Discovery rate counts wrong-answer discoveries among buggy-program/seed trials. An exception or infrastructure failure is not a wrong-answer discovery. A `passed` search result for a known buggy fixture means the sample missed that bug. The summary keeps those misses in the denominator and also lists every program separately.

Reduction quality and cost are reported for pairs whose reduced failures pass a separate stability audit. Compare length and value magnitude separately. Call counts include stability checks; final audits and fixture-witness checks are separate. Wall time includes Docker launch and cleanup, so it depends on the host and its workload. Phase deadlines are checked between evaluations; an in-flight evaluation and cleanup can extend them.

Seeds reproduce generated inputs for this generator version, not timings or arbitrary nondeterministic candidate behavior. The report contains candidate source and hashes, fixture hash, implementation hashes, runner image ID, platform, settings, discovery evidence, and reduction attempts. Rebuilding the floating base image later can change the runtime; record and compare its image ID.

## First pilot

[Raw report](results/pilot-2026-09-05.json) · [Generated tables](results/pilot-2026-09-05.md)

The pilot completed 24 trials: 18 for faulty functions and six for correct controls. It found wrong answers in 16/18 faulty trials (eight of nine faulty programs in both seeds). All six control runs passed their 12 requested tests. `search-any-match` was missed under both seeds, despite its separately verified witness. That is a limitation of this small search sample, not evidence that the candidate is correct.

Across the 16 valid pairs, single deletion used 317 reduction calls and block deletion used 265. Eleven single runs and fourteen block runs reached a local fixed point; the remaining five and two runs exhausted the 30-call budget. Several pairs produced identical results and costs. For `search-insertion` at seed 42, block deletion reached complexity `[0, 0]` in 14 calls, while single deletion exhausted its budget at `[2, 24]`.

These observations support inspecting deletion order under a constrained budget. They do not establish general superiority: there are only nine designed faults, two seeds per program, and three task contracts. Seeds within a program are repeated measurements. Timing was collected on a development laptop with other work running and should be treated as diagnostic, not a performance claim. No LLM repair study was run.

The original pilot used the exact command above with `--output artifacts/pilot.json`. The checked-in JSON is the same parsed data with compact whitespace. Recreate its table without executing code:

```sh
python3 -m benchmarks.summarize benchmarks/results/pilot-2026-09-05.json
```
