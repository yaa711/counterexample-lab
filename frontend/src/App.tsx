import { useEffect, useState } from "react";
import { errorMessage, request } from "./api";
import { Icon } from "./Icons";
import type { Health, Task } from "./types";
import { Workbench } from "./Workbench";
export function App() {
  const [data, setData] = useState<{
    tasks: Task[];
    health: Health;
  } | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    Promise.all([
      request<{
        tasks: Task[];
      }>("tasks"),
      request<Health>("health"),
    ])
      .then(([catalog, health]) => {
        if (active) setData({ tasks: catalog.tasks, health });
      })
      .catch((error) => {
        if (active) setError(errorMessage(error));
      });
    return () => {
      active = false;
    };
  }, [attempt]);
  if (!data)
    return (
      <main className="loading-page">
        <div className="brand-mark">[·]</div>
        <h1>Counterexample Lab</h1>
        {error ? (
          <>
            <p role="alert">{error}</p>
            <p>Start the Python backend, then reconnect.</p>
            <button
              className="primary"
              onClick={() => {
                setError("");
                setAttempt((a) => a + 1);
              }}
            >
              Reconnect <Icon name="arrow" />
            </button>
          </>
        ) : (
          <p role="status">Connecting to the local workbench…</p>
        )}
      </main>
    );
  return <Workbench tasks={data.tasks} initialHealth={data.health} />;
}
