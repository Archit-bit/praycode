import type { ProblemDetail } from "../types/problem";
import { StatusBadge } from "./StatusBadge";

export function ProblemStatement({ problem }: { problem: ProblemDetail }) {
  return (
    <section className="panel statement-panel">
      <div className="statement-header">
        <div>
          <p className="eyebrow">Practice Problem</p>
          <h2>{problem.title}</h2>
        </div>
        <StatusBadge status={problem.status} />
      </div>

      <div className="statement-meta">
        <span className={`difficulty-pill difficulty-${problem.difficulty}`}>{problem.difficulty}</span>
        <span className="meta-chip">{problem.topic}</span>
        <span className="meta-chip">Function: {problem.function_name}</span>
      </div>

      <div className="statement-content">{problem.description}</div>
    </section>
  );
}
