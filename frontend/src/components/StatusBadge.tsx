import type { ProblemStatus } from "../types/problem";

const LABELS: Record<ProblemStatus, string> = {
  not_started: "Not Started",
  attempted: "Attempted",
  solved: "Solved",
};

export function StatusBadge({ status }: { status: ProblemStatus }) {
  return <span className={`status-badge status-${status}`}>{LABELS[status]}</span>;
}
