import type { SubmissionHistoryItem } from "../types/problem";

export function SubmissionHistoryPanel({
  items,
  onLoadCode,
}: {
  items: SubmissionHistoryItem[];
  onLoadCode: (code: string) => void;
}) {
  return (
    <section className="panel submission-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Submission History</p>
          <h3>Previous Submit Attempts</h3>
        </div>
      </div>

      {items.length === 0 ? (
        <div className="empty-state compact">
          <h3>No submissions yet</h3>
          <p>Your submit attempts will appear here with their pass rate and saved code snapshot.</p>
        </div>
      ) : null}

      <div className="card-stack">
        {items.map((item) => (
          <article key={item.id} className={`result-card ${item.all_passed ? "pass" : "fail"}`}>
            <div className="result-header">
              <strong>{new Date(item.created_at).toLocaleString()}</strong>
              <span>
                {item.passed_count}/{item.total_count} passed
              </span>
            </div>
            {item.error ? <div className="error-box">{item.error}</div> : null}
            <div className="history-actions">
              <span className={`result-pill ${item.all_passed ? "success" : "warning"}`}>
                {item.all_passed ? "Accepted" : "Needs Work"}
              </span>
              <button className="ghost-button" type="button" onClick={() => onLoadCode(item.code_snapshot)}>
                Load This Code
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
