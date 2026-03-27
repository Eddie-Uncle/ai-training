import type { ReviewIssue } from "../types";

const SEVERITY_CLASS: Record<ReviewIssue["severity"], string> = {
  critical: "badge-critical",
  high: "badge-high",
  medium: "badge-medium",
  low: "badge-low",
};

const SEVERITY_LABEL: Record<ReviewIssue["severity"], string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

interface Props {
  issue: ReviewIssue;
  index: number;
}

export function IssueCard({ issue, index }: Props) {
  return (
    <article className="issue-card">
      <header className="issue-header">
        <span className={`badge ${SEVERITY_CLASS[issue.severity]}`}>
          {SEVERITY_LABEL[issue.severity]}
        </span>
        <span className="badge badge-category">{issue.category}</span>
        {issue.line !== null && (
          <span className="issue-line">line {issue.line}</span>
        )}
        <span className="issue-index">#{index + 1}</span>
      </header>
      <p className="issue-description">{issue.description}</p>
      <details className="issue-suggestion">
        <summary>Suggestion</summary>
        <p>{issue.suggestion}</p>
      </details>
    </article>
  );
}
