import { useState } from "react";
import { download, errorMessage, request } from "./api";
import { Icon } from "./Icons";
import { Results } from "./Results";
import type { Health, Report, Task, Verification } from "./types";
export function Workbench({
  tasks,
  initialHealth,
}: {
  tasks: Task[];
  initialHealth: Health;
}) {
  const [taskId, setTaskId] = useState(tasks[0].id);
  const [health, setHealth] = useState(initialHealth);
  const [mode, setMode] = useState<"demo" | "custom">("demo");
  const [variant, setVariant] = useState<"buggy" | "correct">("buggy");
  const [code, setCode] = useState(tasks[0].buggy);
  const [seed, setSeed] = useState("42");
  const [count, setCount] = useState("100");
  const [budget, setBudget] = useState("100");
  // Keep executed evidence separate from the editable draft: later edits must not
  // make an old result appear to describe code that was never tested.
  const [report, setReport] = useState<Report | null>(null);
  const [verification, setVerification] = useState<Verification | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [guide, setGuide] = useState(false);
  const task = tasks.find((t) => t.id === taskId)!;
  const displayedCode = mode === "demo" ? task[variant] : code;
  const settingsValid =
    [seed, count, budget].every((value) => /^\d+$/.test(value)) &&
    Number(seed) <= 4294967295 &&
    Number(count) >= 1 &&
    Number(count) <= 500 &&
    Number(budget) <= 500;
  const canRun =
    settingsValid &&
    !busy &&
    (mode === "demo" || health.runner.available) &&
    displayedCode.trim().length > 0;
  function selectTask(next: Task) {
    setTaskId(next.id);
    setCode(next.buggy);
    setVariant("buggy");
    setReport(null);
    setVerification(null);
    setError("");
    setGuide(false);
  }
  async function run() {
    setBusy(true);
    setError("");
    setVerification(null);
    try {
      const result = await request<Report>("run", {
        task: taskId,
        mode,
        variant,
        code: displayedCode,
        seed: Number(seed),
        count: Number(count),
        shrink_budget: Number(budget),
      });
      setReport(result);
    } catch (error) {
      setError(errorMessage(error));
    } finally {
      setBusy(false);
    }
  }
  async function refreshRunner() {
    try {
      setHealth(await request<Health>("health"));
      setError("");
    } catch (error) {
      setError(errorMessage(error));
    }
  }
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a href="/" className="brand" aria-label="Counterexample Lab home">
          <span className="brand-mark">[·]</span>
          <span>
            Counterexample<span className="brand-sub">LAB / CODE RESEARCH</span>
          </span>
        </a>
        <div className="workspace-label">
          <span className="status-dot" /> LOCAL WORKSPACE
        </div>
        <nav aria-label="Workspace navigation">
          <button
            className={`nav-item ${!guide ? "active" : ""}`}
            onClick={() => setGuide(false)}
          >
            <Icon name="flask" /> Workbench{" "}
            <span className="nav-count">01</span>
          </button>
          <button
            className={`nav-item ${guide ? "active" : ""}`}
            onClick={() => setGuide(true)}
          >
            <Icon name="book" /> How it works
          </button>
        </nav>
        <div className="sidebar-section-title">
          PROBLEMS <span>03</span>
        </div>
        <nav className="task-list" aria-label="Choose a problem">
          {tasks.map((item, i) => (
            <button
              key={item.id}
              disabled={busy}
              aria-pressed={taskId === item.id}
              className={`task-link ${taskId === item.id ? "selected" : ""}`}
              onClick={() => selectTask(item)}
            >
              <span className="task-number">0{i + 1}</span>
              <span>{item.name}</span>
              {taskId === item.id ? <span className="tiny-dot" /> : null}
            </button>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="research-note">
            <Icon name="layers" />
            <strong>Start with one counterexample</strong>
            <p>
              Find the failure. Reduce the input.
              <br />
              Understand why the code breaks.
            </p>
          </div>
          <div className="version">
            <span>v{health.version}</span>
            <span>OPEN RESEARCH</span>
          </div>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="breadcrumb">
            Workspace <span>/</span>{" "}
            <strong>{guide ? "How it works" : "Workbench"}</strong>
          </div>
          <span className="local-badge">
            <span className="status-dot" /> Local · No API key needed
          </span>
        </header>
        {guide ? (
          <Guide onBack={() => setGuide(false)} />
        ) : (
          <div className="page-content">
            <div className="page-heading">
              <div>
                <div className="eyebrow">SMALLER INPUT. CLEARER INSIGHT.</div>
                <h1>
                  Make failures explainable<span>.</span>
                </h1>
                <p>
                  Find counterexamples, reduce the input, and see exactly where
                  your code goes wrong.
                </p>
              </div>
              <button
                className="secondary export-button"
                disabled={!report || busy}
                onClick={() =>
                  report &&
                  download(`counterexample-${report.run_id.slice(0, 8)}.json`, {
                    ...report,
                    verification,
                  })
                }
              >
                <Icon name="download" /> Export experiment
              </button>
            </div>

            <div className="pipeline">
              <div className="pipeline-step current">
                <span>01</span> Define
              </div>
              <i />
              <div className={`pipeline-step ${report ? "current" : ""}`}>
                <span>02</span> Find & reduce
              </div>
              <i />
              <div className={`pipeline-step ${verification ? "current" : ""}`}>
                <span>03</span> Verify repair
              </div>
              <small>Reproducible · Inspectable · Exportable</small>
            </div>

            <section className="task-overview">
              <div className="task-heading">
                <span className="task-icon">
                  <Icon name="code" size={22} />
                </span>
                <div>
                  <div className="eyebrow">{task.tag}</div>
                  <h2>{task.name}</h2>
                </div>
              </div>
              <p>{task.description}</p>
              <span className="course-tag">{task.level}</span>
            </section>

            {error ? (
              <div className="error-banner" role="alert">
                <strong>Action incomplete</strong> {error}
                <button aria-label="Dismiss error" onClick={() => setError("")}>
                  <Icon name="close" />
                </button>
              </div>
            ) : null}

            <div className="workbench-grid">
              <section className="panel code-panel">
                <div className="panel-heading">
                  <h2>
                    <Icon name="terminal" /> Candidate code
                  </h2>
                  <span className="language-tag">Python 3</span>
                </div>
                <div className="editor-toolbar">
                  <div className="segmented" aria-label="Code source">
                    <button
                      disabled={busy}
                      className={mode === "demo" ? "selected" : ""}
                      aria-pressed={mode === "demo"}
                      onClick={() => setMode("demo")}
                    >
                      Built-in demo
                    </button>
                    <button
                      disabled={busy}
                      className={mode === "custom" ? "selected" : ""}
                      aria-pressed={mode === "custom"}
                      onClick={() => {
                        setCode(displayedCode);
                        setMode("custom");
                      }}
                    >
                      Your code
                    </button>
                  </div>
                  {mode === "demo" ? (
                    <select
                      aria-label="Choose an example"
                      disabled={busy}
                      value={variant}
                      onChange={(e) =>
                        setVariant(e.target.value as "buggy" | "correct")
                      }
                    >
                      <option value="buggy">Buggy example</option>
                      <option value="correct">Correct example</option>
                    </select>
                  ) : (
                    <span className="muted">Isolated with Docker</span>
                  )}
                </div>
                <div className="file-tab">
                  <span className="file-dot" /> candidate.py{" "}
                  <span>
                    {mode === "demo" ? "Read-only example" : "Editable"}
                  </span>
                </div>
                <div className="code-editor">
                  <div className="line-numbers" aria-hidden="true">
                    {displayedCode.split("\n").map((_, i) => (
                      <span key={i}>{i + 1}</span>
                    ))}
                  </div>
                  <textarea
                    aria-label="Candidate Python code"
                    spellCheck={false}
                    readOnly={mode === "demo" || busy}
                    value={displayedCode}
                    onChange={(e) => setCode(e.target.value)}
                  />
                </div>
                <div className="contract">
                  <span>CONTRACT</span>
                  <code>{task.signature}</code>
                </div>
                <div className="editor-footer">
                  <span
                    className={`status-dot ${mode === "custom" && !health.runner.available ? "amber" : ""}`}
                  />
                  <span>
                    {mode === "demo"
                      ? "Hand-authored demo \u00B7 runs a fixed trusted function"
                      : health.runner.reason}
                  </span>
                  {mode === "custom" ? (
                    <button className="text-button" onClick={refreshRunner}>
                      Check again
                    </button>
                  ) : null}
                </div>
              </section>

              <section className="panel config-panel">
                <div className="panel-heading">
                  <h2>
                    <Icon name="flask" /> Experiment settings
                  </h2>
                  <span className="muted mono">CONFIG</span>
                </div>
                <div className="config-body">
                  <label htmlFor="seed">
                    Random seed <span>SEED</span>
                  </label>
                  <input
                    id="seed"
                    type="number"
                    min="0"
                    max="4294967295"
                    value={seed}
                    disabled={busy}
                    onChange={(e) => setSeed(e.target.value)}
                  />
                  <p className="field-help">
                    Same seed. Same generated inputs.
                  </p>
                  <div className="number-fields">
                    <div>
                      <label htmlFor="count">Search budget</label>
                      <input
                        id="count"
                        type="number"
                        min="1"
                        max="500"
                        disabled={busy}
                        value={count}
                        onChange={(e) => setCount(e.target.value)}
                      />
                    </div>
                    <div>
                      <label htmlFor="budget">Reduction budget</label>
                      <input
                        id="budget"
                        type="number"
                        min="0"
                        max="500"
                        disabled={busy}
                        value={budget}
                        onChange={(e) => setBudget(e.target.value)}
                      />
                    </div>
                  </div>
                  <p className="field-help">
                    Maximum evaluations: 1–500 for search, 0–500 for reduction.
                  </p>
                  <div className="config-checks">
                    <span>
                      <Icon name="check" size={15} /> Independent reference
                      implementation
                    </span>
                    <span>
                      <Icon name="check" size={15} /> Contract-preserving input
                      reduction
                    </span>
                    <span>
                      <Icon name="check" size={15} /> Fixed seeds and a complete
                      audit trail
                    </span>
                  </div>
                  <button
                    className="primary run-button"
                    disabled={!canRun}
                    onClick={run}
                  >
                    {busy ? (
                      <>
                        <span className="spinner" /> Running experiment…
                      </>
                    ) : (
                      <>
                        <Icon name="play" /> Run experiment{" "}
                        <span className="button-arrow">↗</span>
                      </>
                    )}
                  </button>
                  {!settingsValid ? (
                    <p className="field-error">
                      Check the integer ranges in the settings.
                    </p>
                  ) : null}
                  {mode === "custom" && !health.runner.available ? (
                    <p className="field-error">
                      Install Docker and build the runner as described in the
                      README. Built-in demos remain available.
                    </p>
                  ) : (
                    <p className="run-caption">
                      {busy
                        ? "Executing real tests. Custom code may take about a minute."
                        : "Reduction starts automatically after the first failure."}
                    </p>
                  )}
                </div>
              </section>
            </div>

            <Results
              key={report?.run_id ?? "empty"}
              report={report}
              task={task}
              health={health}
              busy={busy}
              setBusy={setBusy}
              verification={verification}
              onVerified={setVerification}
            />
            <footer className="page-footer">
              <button className="footer-guide" onClick={() => setGuide(true)}>
                How it works ↗
              </button>
              <span>
                Finite tests are not a proof. Keep every conclusion in context.
              </span>
            </footer>
          </div>
        )}
      </main>
    </div>
  );
}
function Guide({ onBack }: { onBack: () => void }) {
  return (
    <div className="page-content guide">
      <div className="eyebrow">THE METHOD</div>
      <h1>Understand before you trust.</h1>
      <p className="guide-intro">
        Three inspectable steps connect the workflow. You can study
        model-generated code without knowing the internals of the model.
      </p>
      {[
        [
          "01",
          "Differential testing",
          "Give the same input to the candidate and an independent reference. Different answers reveal a counterexample. Sorting preserves duplicates; search returns the first match; the maximum subarray must be non-empty.",
        ],
        [
          "02",
          "Counterexample reduction",
          "Delete chunks, then individual elements, then simplify values toward zero. Accept a change only if the input remains valid, its size measure strictly decreases, and the error repeats. This is local reduction, not a guarantee of a global minimum.",
        ],
        [
          "03",
          "Held-out verification",
          "Test the repair using a different seed and exclude all inputs seen during discovery and reduction. Passing means only that these tests found no errors. Repeated verification reuses the same set, so do not tune against it.",
        ],
      ].map(([n, title, text]) => (
        <article className="guide-card" key={n}>
          <span>{n}</span>
          <div>
            <h2>{title}</h2>
            <p>{text}</p>
          </div>
        </article>
      ))}
      <div className="guide-card">
        <Icon name="book" size={28} />
        <div>
          <h2>How does this become a research project?</h2>
          <p>
            Compare failure-only, full-input and reduced-input feedback. Fix the
            model version, candidate and generation settings. Use a fresh model
            conversation for each condition and retain every result. See
            docs/EXPERIMENTS.md for the protocol.
          </p>
          <p>
            Built-in examples teach and validate the tool; they are not a model
            benchmark. The app does not call a model automatically or fabricate
            repairs.
          </p>
        </div>
      </div>
      <button className="primary" onClick={onBack}>
        Start experimenting <Icon name="arrow" />
      </button>
    </div>
  );
}
