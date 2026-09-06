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
  const [strategy, setStrategy] = useState<"single" | "block">("block");
  const [profile, setProfile] = useState<"demo" | "evaluation">("demo");
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
        strategy,
        profile,
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
        <a href="/" className="brand" aria-label="Find My Bug home">
          <span className="brand-mark">[·]</span>
          <span>
            Find My Bug<span className="brand-sub">PYTHON PRACTICE</span>
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
            <strong>A small example can help</strong>
            <p>
              Find an input your code misses.
              <br />
              Make a change. Check it again.
            </p>
          </div>
          <div className="version">
            <span>v{health.version}</span>
            <span>LEARN BY TESTING</span>
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
                <div className="eyebrow">
                  PRACTICE WITH THREE PYTHON PROBLEMS
                </div>
                <h1>Find the input that breaks your code.</h1>
                <p>Try an example, spot the difference, and check your fix.</p>
              </div>
              <button
                className="secondary export-button"
                disabled={!report || busy}
                onClick={() =>
                  report &&
                  download(`find-my-bug-${report.run_id.slice(0, 8)}.json`, {
                    ...report,
                    verification,
                  })
                }
              >
                <Icon name="download" /> Export results
              </button>
            </div>

            <div className="pipeline">
              <div className="pipeline-step current">
                <span>01</span> Write code
              </div>
              <i />
              <div className={`pipeline-step ${report ? "current" : ""}`}>
                <span>02</span> Find a failing case
              </div>
              <i />
              <div className={`pipeline-step ${verification ? "current" : ""}`}>
                <span>03</span> Check your fix
              </div>
              <small>Start with the example below</small>
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
              <div className="problem-example">
                <strong>Example</strong>
                <code>
                  {task.id === "sort"
                    ? "[3, 1, 3] → [1, 3, 3]"
                    : task.id === "first_index"
                      ? "[1, 3, 3], target = 3 → 1 (indexes start at 0)"
                      : "[-2, 3, -1, 2] → 4 (from [3, -1, 2])"}
                </code>
              </div>
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
                    <Icon name="terminal" /> 1. Your code
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
                      Try an example
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
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() =>
                        setCode(
                          task.id === "first_index"
                            ? "def solve(numbers, target):\n    # Return the first matching index, or -1.\n    pass\n"
                            : `def solve(numbers):\n    # ${task.description}\n    pass\n`,
                        )
                      }
                    >
                      Use starter code
                    </button>
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
                  <span>FUNCTION</span>
                  <code>{task.signature}</code>
                </div>
                <div className="editor-footer">
                  <span
                    className={`status-dot ${mode === "custom" && !health.runner.available ? "amber" : ""}`}
                  />
                  <span>
                    {mode === "demo"
                      ? "Example code · Choose Your code to edit it"
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
                    <Icon name="flask" /> Ready to test?
                  </h2>
                  <span className="muted">Step 2</span>
                </div>
                <div className="config-body">
                  <p>
                    Find an input where your answer differs from the expected
                    answer. No settings needed to try the example.
                  </p>
                  <details className="advanced-settings">
                    <summary>Advanced settings</summary>
                    <label htmlFor="strategy">Reduction strategy</label>
                    <select
                      id="strategy"
                      value={strategy}
                      disabled={busy}
                      onChange={(e) =>
                        setStrategy(e.target.value as "single" | "block")
                      }
                    >
                      <option value="single">
                        Single deletion + value simplification
                      </option>
                      <option value="block">
                        Block deletion + value simplification
                      </option>
                    </select>
                    <p className="field-help">
                      Both strategies use the same value transformations and
                      failure checks.
                    </p>
                    <label htmlFor="profile">Input generation</label>
                    <select
                      id="profile"
                      value={profile}
                      disabled={busy}
                      onChange={(e) =>
                        setProfile(e.target.value as "demo" | "evaluation")
                      }
                    >
                      <option value="demo">Teaching demo</option>
                      <option value="evaluation">Evaluation</option>
                    </select>
                    <p className="field-help">
                      Evaluation uses seeded random inputs and generic
                      boundaries, without the teaching examples.
                    </p>
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
                      Maximum evaluations: 1–500 for search, 0–500 for
                      reduction.
                    </p>
                  </details>
                  <button
                    className="primary run-button"
                    disabled={!canRun}
                    onClick={run}
                  >
                    {busy ? (
                      <>
                        <span className="spinner" /> Finding a failing case…
                      </>
                    ) : (
                      <>
                        <Icon name="play" /> Find a failing case{" "}
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
                        : "We look for a wrong answer, then try to make the input smaller."}
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
                Passing these tests does not mean your code works for every
                input.
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
      <div className="eyebrow">GETTING STARTED</div>
      <h1>A small input makes a bug easier to see.</h1>
      <p className="guide-intro">
        Practice sorting, binary search, and maximum subarray problems in
        Python. Start with a built-in example; editing and running your own code
        requires Docker.
      </p>
      {[
        [
          "01",
          "Read the problem and try some code",
          "Use the example to get started, or choose Your code and fill in the solve function. Check the problem's rules and example output first.",
        ],
        [
          "02",
          "Compare the answers",
          "Click Find a failing case. If we find a wrong answer, we try smaller inputs that still fail. Compare Expected with Your output. The result is a useful small example, not necessarily the smallest possible one.",
        ],
        [
          "03",
          "Make a change and check your fix",
          "Edit the failed code in the fix editor. We check the displayed failure again, then test other inputs you have not seen. Passing tests does not prove your solution works for every input.",
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
      <p>
        Curious about the algorithm? Open the test details after a run. The
        repository also includes paired reduction experiments and their
        limitations.
      </p>
      <button className="primary" onClick={onBack}>
        Try an example <Icon name="arrow" />
      </button>
    </div>
  );
}
