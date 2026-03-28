import { Link } from "react-router-dom";

import type { ProblemSummary } from "../types/problem";
import { StatusBadge } from "./StatusBadge";

export function ProblemTable({ items }: { items: ProblemSummary[] }) {
  if (items.length === 0) {
    return (
      <div className="empty-state">
        <h3>No problems found</h3>
        <p>Adjust the filters or add a new practice problem.</p>
      </div>
    );
  }

  return (
    <div className="table-shell">
      <table className="problem-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Topic</th>
            <th>Difficulty</th>
            <th>Status</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {items.map((problem) => (
            <tr key={problem.slug}>
              <td>
                <Link to={`/problems/${problem.slug}`} className="problem-link">
                  {problem.title}
                </Link>
              </td>
              <td>{problem.topic}</td>
              <td>
                <span className={`difficulty-pill difficulty-${problem.difficulty}`}>
                  {problem.difficulty}
                </span>
              </td>
              <td>
                <StatusBadge status={problem.status} />
              </td>
              <td>{new Date(problem.updated_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
