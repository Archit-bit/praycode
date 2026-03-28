import type { ExecutionResponse } from "../types/problem";

function formatJson(value: unknown) {
  return JSON.stringify(value, null, 2);
}

export function RunResultsPanel({
  result,
  isLoading,
}: {
  result: ExecutionResponse | null;
  isLoading: boolean;
}) {
  return (
    <section className="panel side-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Execution</p>
          <h3>Run Results</h3>
        </div>
        {result ? (
          <span className={`result-pill ${result.all_passed ? "success" : "warning"}`}>
            {result.passed_count}/{result.total_count} passed
          </span>
        ) : null}
      </div>

      {isLoading ? <div className="empty-state compact">Running code...</div> : null}

      {!isLoading && !result ? (
        <div className="empty-state compact">
          <h3>No run yet</h3>
          <p>Run or submit your code to see detailed case-by-case feedback here.</p>
        </div>
      ) : null}

      {result?.error ? <div className="error-box">{result.error}</div> : null}

      <div className="card-stack">
        {result?.results.map((item, index) => (
          <article key={index} className={`result-card ${item.passed ? "pass" : "fail"}`}>
            <div className="result-header">
              <strong>Case {index + 1}</strong>
              <span>{item.passed ? "Passed" : "Failed"}</span>
            </div>
            <div className="json-block">
              <span>Input</span>
              <pre>{formatJson(item.input)}</pre>
            </div>
            <div className="json-block">
              <span>Expected</span>
              <pre>{formatJson(item.expected_output)}</pre>
            </div>
            <div className="json-block">
              <span>Actual</span>
              <pre>{formatJson(item.actual_output)}</pre>
            </div>
            {item.stdout ? (
              <div className="json-block">
                <span>Stdout</span>
                <pre>{item.stdout}</pre>
              </div>
            ) : null}
            {item.error ? <div className="error-box">{item.error}</div> : null}
          </article>
        ))}
      </div>
    </section>
  );
}
