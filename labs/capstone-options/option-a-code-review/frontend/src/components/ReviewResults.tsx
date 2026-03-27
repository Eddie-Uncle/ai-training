import type { ReviewResponse } from "../types";
import { IssueCard } from "./IssueCard";
import { MetricsBar } from "./MetricsBar";

const SEVERITY_ORDER = { critical: 0, high: 1, medium: 2, low: 3 };

interface Props {
  results: ReviewResponse;
}

export function ReviewResults({ results }: Props) {
  const sorted = [...results.issues].sort(
    (a, b) => SEVERITY_ORDER[a.severity] - SEVERITY_ORDER[b.severity]
  );

  const criticalCount = results.issues.filter((i) => i.severity === "critical").length;
  const highCount = results.issues.filter((i) => i.severity === "high").length;

  return (
    <section className="results-section">
      <h2 className="results-title">Review Results</h2>

      <div className="summary-card">
        <p className="summary-text">{results.summary}</p>
        <div className="summary-counts">
          {criticalCount > 0 && (
            <span className="badge badge-critical">{criticalCount} critical</span>
          )}
          {highCount > 0 && (
            <span className="badge badge-high">{highCount} high</span>
          )}
          <span className="badge badge-category">
            {results.issues.length} issue{results.issues.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      <MetricsBar metrics={results.metrics} />

      {sorted.length > 0 && (
        <div className="issues-list">
          <h3 className="section-heading">Issues</h3>
          {sorted.map((issue, i) => (
            <IssueCard key={i} issue={issue} index={i} />
          ))}
        </div>
      )}

      {results.suggestions.length > 0 && (
        <div className="suggestions">
          <h3 className="section-heading">General Suggestions</h3>
          <ul className="suggestions-list">
            {results.suggestions.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
