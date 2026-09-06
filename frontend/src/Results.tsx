import { useState } from "react";
import { errorMessage, request } from "./api";
import { Icon } from "./Icons";
import type {
  Case,
  Failure,
  Health,
  Report,
  Status,
  Task,
  Verification,
} from "./types";
const STATUS: Record<Status, string> = {
  passed: "No errors found in these tests",
  wrong_answer: "Found a failing case",
  exception: "Execution error",
  timeout: "Execution timed out",
  invalid_output: "Invalid output",
  infrastructure_error: "Runner unavailable",
  incomplete: "Tests incomplete",
};
const STOP: Record<string, string> = {
  local_fixed_point: "Local fixed point reached",
  budget_exhausted: "Reduction budget exhausted",
  time_limit: "Time limit reached",
  unstable_failure: "Failure is not reproducible",
  infrastructure_error: "Runner failed; reduction stopped",
};
const PROMPTS = [
  { id: "failure_only", label: "Failure only" },
  { id: "original", label: "Original input" },
  { id: "reduced", label: "Reduced input" },
];
function InputView({
  value,
  compact = false,
}: {
  value: Case;
  compact?: boolean;
}) {
  return (
    <div className={compact ? "array-view compact" : "array-view"}>
      <span className="array-bracket">[</span>
      {value.numbers.length ? (
        value.numbers.map((number, index) => (
          <span className="array-number" key={index}>
            {number}
          </span>
        ))
      ) : (
        <span className="muted">empty</span>
      )}
      <span className="array-bracket">]</span>
      {value.target !== undefined ? (
        <span className="target-value">target = {value.target}</span>
      ) : null}
    </div>
  );
}
function Output({ value }: { value: unknown }) {
  return <code>{JSON.stringify(value) ?? "No return value"}</code>;
}
export function Results({
  report,
  task,
  health,
  busy,
  setBusy,
  verification,
  onVerified,
}: {
  report: Report | null;
  task: Task;
  health: Health;
  busy: boolean;
  setBusy: (value: boolean) => void;
  verification: Verification | null;
  onVerified: (value: Verification) => void;
}) {
  const [prompt, setPrompt] = useState("reduced");
  const [copied, setCopied] = useState(false);
  const [repairMode, setRepairMode] = useState<"demo" | "custom">("custom");
  const [repairCode, setRepairCode] = useState(
    report?.source.code ?? task.buggy,
  );
  const [error, setError] = useState("");
  if (!report)
    return (
      <section className="panel empty-result" aria-live="polite">
        <div className="empty-diagram">
          <span>[ 8, 3, …, 8 ]</span>
          <Icon name="arrow" />
          <span className="empty-small">[ 0, 0 ]</span>
        </div>
        <h2>
          {busy
            ? "Running tests\u2026"
            : "Your failing example will appear here."}
        </h2>
        <p>
          {busy
            ? "Actual results will appear here when the run completes."
            : "Click Find a failing case to test the code above."}
        </p>
        <span className="empty-label">
          Illustration only · No experiment results yet
        </span>
      </section>
    );
  const reduction = report.shrink;
  const failure = report.failure;
  const reduced = reduction?.reduced;
  const originalSize = failure?.input.numbers.length ?? 0;
  const finalSize = reduced?.input.numbers.length ?? originalSize;
  const change = originalSize
    ? Math.round((1 - finalSize / originalSize) * 100)
    : 0;
  const activePrompt = report.prompts[prompt] ? prompt : "original";
  const hasPrompts = Object.keys(report.prompts).length > 0;
  async function copyPrompt() {
    try {
      await navigator.clipboard.writeText(report!.prompts[activePrompt]);
      setCopied(true);
    } catch {
      setError(
        "Clipboard access is unavailable. Select the prompt and copy it manually.",
      );
    }
  }
  async function verifyRepair() {
    setBusy(true);
    setError("");
    try {
      onVerified(
        await request<Verification>("verify", {
          run_id: report!.run_id,
          mode: repairMode,
          variant: "correct",
          code: repairCode,
          count: 100,
        }),
      );
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="results" aria-live="polite">
      <div className="results-heading">
        <h2>
          2. Look at this result{" "}
          <span className="mono">#{report.run_id.slice(0, 8)}</span>
        </h2>
        <span
          className={`result-status ${report.status === "passed" ? "success" : "warning"}`}
        >
          {STATUS[report.status]}
        </span>
      </div>
      {failure ? (
        <section className="panel failing-example">
          <div className="eyebrow">
            {reduced
              ? "A SMALL INPUT THAT STILL FAILS"
              : "THE INPUT THAT FAILED"}
          </div>
          <InputView value={(reduced ?? failure).input} />
          <ResultPair record={reduced ?? failure} />
          <p>
            This result belongs to the code you last ran. Editing your draft
            does not update it.
          </p>
          {report.status === "wrong_answer" ? (
            <details className="thinking-hint">
              <summary>A question to think about</summary>
              <p>
                {task.id === "sort"
                  ? "Does your result keep every number, including repeated numbers, in ascending order?"
                  : task.id === "first_index"
                    ? "If the target appears more than once, which index does the problem ask for? What if it is absent?"
                    : "Which consecutive numbers give the largest sum? Remember that the chosen group cannot be empty."}
              </p>
            </details>
          ) : null}
        </section>
      ) : (
        <div className="panel passed-panel">
          <Icon name="check" />
          <p>
            {report.status === "passed"
              ? "These tests found no errors."
              : "Not all requested tests completed."}{" "}
            This is not a proof of correctness for every input.
          </p>
        </div>
      )}
      <section className="panel repair-panel">
        <div className="panel-heading">
          <h2>
            <Icon name="check" /> 3. Check your fix
          </h2>
          <span className="muted">Check against 100 unseen inputs</span>
        </div>
        <div className="repair-body">
          <div className="repair-intro">
            <p>
              Start from the code that failed. Make a change below, then check
              the failing example and other unseen inputs.
            </p>
            <div className="segmented">
              <button
                disabled={busy}
                aria-pressed={repairMode === "demo"}
                className={repairMode === "demo" ? "selected" : ""}
                onClick={() => setRepairMode("demo")}
              >
                Show a working example
              </button>
              <button
                disabled={busy}
                aria-pressed={repairMode === "custom"}
                className={repairMode === "custom" ? "selected" : ""}
                onClick={() => setRepairMode("custom")}
              >
                Edit your fix
              </button>
            </div>
          </div>
          <textarea
            className="repair-code"
            aria-label="Repair Python code"
            spellCheck={false}
            readOnly={repairMode === "demo" || busy}
            value={repairMode === "demo" ? task.correct : repairCode}
            onChange={(e) => setRepairCode(e.target.value)}
          />
          <div className="repair-actions">
            <span className="muted">
              {repairMode === "demo"
                ? "This runs the built-in working example. Your edited draft is kept separately."
                : health.runner.available
                  ? "Your repair will run inside Docker."
                  : "Requires Docker. You can verify the correct demo first."}
            </span>
            <button
              className="primary"
              disabled={
                busy ||
                (repairMode === "custom" &&
                  (!health.runner.available || !repairCode.trim()))
              }
              onClick={verifyRepair}
            >
              <Icon name="check" /> Check your fix
            </button>
          </div>
          {error ? (
            <p className="field-error" role="alert">
              {error}
            </p>
          ) : null}
          {verification ? (
            <div
              className={`verification-result ${verification.status === "passed" && (!verification.regression || verification.regression.status === "passed") ? "good" : "bad"}`}
              role="status"
            >
              <strong>
                Unseen inputs: {STATUS[verification.status]} ·{" "}
                {verification.passed}/{verification.tested}
              </strong>
              {verification.regression ? (
                <div className="regression-result">
                  <strong>
                    Previous failing example:{" "}
                    {verification.regression.status === "passed"
                      ? "passed"
                      : "still fails"}
                  </strong>
                  <InputView value={verification.regression.input} compact />
                  <ResultPair record={verification.regression} />
                </div>
              ) : null}
              <p>
                Verification seed {verification.seed} · Overlap with prior
                inputs: {verification.overlap_count} · Requested:{" "}
                {verification.requested} inputs
              </p>
              <p>{verification.claim}</p>
              <details>
                <summary>View the code checked in this result</summary>
                <pre>{verification.source.code}</pre>
              </details>
              <p>
                This records the last checked code. Editing the fix above does
                not update these results.
              </p>
              {verification.failures[0] ? (
                <details>
                  <summary>Inspect the first verification failure</summary>
                  <pre>{JSON.stringify(verification.failures[0], null, 2)}</pre>
                </details>
              ) : null}
            </div>
          ) : null}
        </div>
      </section>
      <details className="test-details">
        <summary>Test details and how the input got smaller</summary>
        <p className="evidence-note" data-testid="recorded-settings">
          Recorded strategy:{" "}
          {report.strategy === "single" ? "Single deletion" : "Block deletion"}{" "}
          + value simplification
          {" · "}Generator:{" "}
          {report.profile === "demo" ? "Teaching demo" : "Evaluation"}
          {" · "}Total candidate calls: {report.candidate_calls} (including
          failure confirmations).
        </p>
        <div className="stats-grid">
          <Metric
            label="Inputs tested"
            value={String(report.tested)}
            detail={`Budget: ${report.requested} calls`}
          />
          <Metric
            label="Original → reduced size"
            value={failure ? `${originalSize} → ${finalSize}` : "\u2014"}
            detail={
              failure ? `${change}% fewer elements` : "No counterexample found"
            }
          />
          <Metric
            label="Reduction calls"
            value={String(reduction?.calls ?? 0)}
            detail={
              reduction
                ? `Budget: ${reduction.budget} calls`
                : "Reduction not started"
            }
          />
          <Metric
            label="Elapsed time"
            value={
              report.elapsed_ms < 1000
                ? `${report.elapsed_ms.toFixed(0)} ms`
                : `${(report.elapsed_ms / 1000).toFixed(1)} s`
            }
            detail={`Seed ${report.seed}`}
          />
        </div>
        <p className="evidence-note">
          Recorded source:{report.source.provenance} ·{" "}
          {report.source.mode === "demo"
            ? "fixed trusted function"
            : "Python code in Docker"}{" "}
          · SHA-256 {report.source.sha256.slice(0, 12)}. Editing the code above
          does not change this result.
        </p>
        {failure ? (
          <div className="panel failing-example">
            <div className="eyebrow">ORIGINAL INPUT</div>
            <InputView value={failure.input} />
            <ResultPair record={failure} />
          </div>
        ) : null}
        {reduction ? (
          <section className="panel trace-panel">
            <div className="panel-heading">
              <h2>
                <Icon name="layers" /> Reduction trace
              </h2>
              <span className="trace-state">
                {STOP[reduction.stop_reason] ?? reduction.stop_reason}
              </span>
            </div>
            <div className="trace-list">
              {reduction.steps.map((step, i) => (
                <div className="trace-row" key={i}>
                  <span className="trace-index">
                    {String(i).padStart(2, "0")}
                  </span>
                  <div className="trace-description">
                    <strong>{step.reason}</strong>
                    <InputView value={step.input} compact />
                  </div>
                  <span className="trace-proof">
                    {i === 0 ? "Original failure" : "Still failing"}
                  </span>
                </div>
              ))}
            </div>
            <details className="attempt-details">
              <summary>
                All reduction attempts ({reduction.attempts.length})
              </summary>
              <p className="field-help">
                Skipped inputs do not consume calls. Accepted reductions have a
                separate confirmation call. This is an algorithm trace, not a
                line-by-line code trace.
              </p>
              <p>
                Complexity (length, absolute-value sum including target):{" "}
                {JSON.stringify(reduction.original_measure)} →{" "}
                {JSON.stringify(reduction.reduced_measure)}
              </p>
              <ol className="attempt-list">
                {reduction.attempts.map((attempt, index) => (
                  <li key={index}>
                    <strong>{attempt.decision.replaceAll("_", " ")}</strong>
                    {" · "}
                    {attempt.reason}
                    {" · "}
                    {attempt.call === null
                      ? "Skipped"
                      : `Call ${attempt.call} · ${attempt.elapsed_ms.toFixed(1)} ms`}
                    <pre>{JSON.stringify(attempt.input)}</pre>
                    {attempt.status ? (
                      <span>
                        {STATUS[attempt.status]} · Expected:{" "}
                        <Output value={attempt.expected} /> · Actual:{" "}
                        <Output value={attempt.actual} />
                      </span>
                    ) : null}
                  </li>
                ))}
              </ol>
            </details>
            <div className="trace-footer">
              {!reduction.stable
                ? "Stability was not confirmed for this run. "
                : ""}
              {reduction.claim}
            </div>
          </section>
        ) : null}
      </details>
      {hasPrompts ? (
        <details className="model-details">
          <summary>Copy feedback for an AI assistant (optional)</summary>
          <section className="panel feedback-panel">
            <div className="panel-heading">
              <h2>
                <Icon name="copy" /> Repair feedback for the model
              </h2>
              <span className="muted">Copy manually · No API calls</span>
            </div>
            <div className="feedback-body">
              <div className="prompt-tabs" aria-label="Feedback condition">
                {PROMPTS.filter((item) => report.prompts[item.id]).map(
                  (item) => (
                    <button
                      key={item.id}
                      className={activePrompt === item.id ? "active" : ""}
                      aria-pressed={activePrompt === item.id}
                      onClick={() => {
                        setPrompt(item.id);
                        setCopied(false);
                      }}
                    >
                      {item.label}
                    </button>
                  ),
                )}
                <button className="copy-button" onClick={copyPrompt}>
                  <Icon name={copied ? "check" : "copy"} size={15} />{" "}
                  {copied ? "Copied" : "Copy prompt"}
                </button>
              </div>
              <textarea
                aria-label="Repair prompt"
                className="prompt-text"
                readOnly
                value={report.prompts[activePrompt]}
              />
              <p className="field-help">
                Use a fresh conversation for each condition. Keep the model and
                settings fixed, and retain all responses.
              </p>
            </div>
          </section>
        </details>
      ) : null}
      <details className="source-details">
        <summary>Inspect the exact executed source and provenance</summary>
        <p>{report.source.provenance}</p>
        <pre>{report.source.code}</pre>
        <code>{report.source.sha256}</code>
      </details>
    </div>
  );
}
function Metric({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail: string;
}) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}
function ResultPair({ record }: { record: Failure }) {
  return (
    <div className="output-pair">
      <div>
        <span>Expected</span>
        <Output value={record.expected} />
      </div>
      <div>
        <span>Your output</span>
        <Output value={record.actual} />
      </div>
      {record.message ? <p>{record.message}</p> : null}
    </div>
  );
}
