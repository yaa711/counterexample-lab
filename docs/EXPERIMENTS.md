# Manual LLM repair study protocol

## Question

Does a reduced counterexample improve code repair on held-out tests, compared with a full failing input or a failure-only message?

This release implements the measurement tool. It contains no completed model study and no claimed positive result.

## Pilot before a larger study

Use the three built-in examples to validate the mechanics only. For the study, collect multiple independent candidate programs from a named model, record the task contract and original generation prompt, and keep every candidate (including correct ones). Distinguish the fraction initially incorrect from repair success conditional on an initial failure.

Do not count hundreds of inputs for one program as hundreds of independent repair experiments. The candidate program/task is the relevant experimental unit for the repair comparison.

## Matched feedback conditions

For each reproducible wrong-answer candidate, export the discovery report and use all three feedback conditions:

1. `failure_only`: same contract and code, told only that a test failed.
2. `original`: same contract/code plus original input, expected output and actual output.
3. `reduced`: same contract/code plus reduced input, expected output and actual output.

Use independent fresh model conversations for every condition, hold model version and available sampling settings fixed, and randomize condition order. Do not let one condition see another condition's answer. Record when a provider cannot fix sampling or model version. The instrument does not automate provider calls or promise deterministic model output.

When shrinking is unstable, incomplete or infrastructure-limited, record that fact and decide an inclusion rule before comparing results. Do not silently drop difficult examples after seeing outcomes. Consider comparing feedback lengths separately: any improvement may be due to shorter context rather than semantic minimality.

## Validation

Paste the returned function in the repair panel and validate it using Docker. Each condition tied to the same discovery run uses the same independent test suite for comparability. Verification excludes discovery and reduction inputs. This version runs a fixed derived seed; repeated verification is not a new test set. Do not iteratively tune repairs against it.

After running a condition, export its report immediately (the UI retains only the latest verification result). Give each export a distinct filename. Keep the original model response separately. A report becoming stale after a restart requires replaying discovery with exactly the same source and settings.

If a repair has an exception, timeout or invalid output, record that category. A container startup/daemon error is an infrastructure issue, not evidence of model repair failure. Resource-limited and incomplete runs must not be called full-suite passes.

## Suggested record fields

```csv
candidate_id,task,model,model_version,condition,replicate,model_settings,discovery_seed,source_sha256,original_length,reduced_length,shrink_stop_reason,verification_seed,requested_tests,executed_tests,passed_tests,status,model_latency_seconds,notes,report_file
```

Fill these fields from actual runs; leave unavailable provider metadata explicitly marked unavailable. The app's JSON already contains code, hashes, generator version, inputs, counts and timing for the tool. Tool runtime does not include manual model response time.

## Reporting

Report candidate counts, counts in each outcome category, and repair success per condition. Use paired comparisons where conditions share the candidate. Any uncertainty interval should reflect variation between independent candidates, not just between correlated input tests. A larger confirmatory study should separate development tasks from final evaluation tasks.

Include null or negative findings and representative failures. Finite tests cannot prove general correctness, a small hand-selected task suite cannot establish general LLM ability, and novelty requires a separate literature review. Archive the exact Git revision and release dependencies used.
