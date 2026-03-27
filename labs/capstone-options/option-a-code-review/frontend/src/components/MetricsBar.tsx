import type { ReviewMetrics } from "../types";

const COMPLEXITY_CLASS: Record<ReviewMetrics["complexity"], string> = {
  low: "pill-green",
  medium: "pill-yellow",
  high: "pill-red",
};

const MAINT_CLASS: Record<ReviewMetrics["maintainability"], string> = {
  excellent: "pill-green",
  good: "pill-teal",
  fair: "pill-yellow",
  poor: "pill-red",
};

interface Props {
  metrics: ReviewMetrics;
}

export function MetricsBar({ metrics }: Props) {
  const pct = (metrics.overall_score / 10) * 100;
  const scoreClass =
    metrics.overall_score >= 8
      ? "score-good"
      : metrics.overall_score >= 5
        ? "score-mid"
        : "score-bad";

  return (
    <div className="metrics-bar">
      <div className="score-wrap">
        <span className="score-label">Score</span>
        <div className="score-track">
          <div
            className={`score-fill ${scoreClass}`}
            style={{ width: `${pct}%` }}
            role="progressbar"
            aria-valuenow={metrics.overall_score}
            aria-valuemin={1}
            aria-valuemax={10}
          />
        </div>
        <span className={`score-value ${scoreClass}`}>
          {metrics.overall_score}/10
        </span>
      </div>

      <div className="pills">
        <span className="pill-label">Complexity</span>
        <span className={`pill ${COMPLEXITY_CLASS[metrics.complexity]}`}>
          {metrics.complexity}
        </span>
        <span className="pill-label">Maintainability</span>
        <span className={`pill ${MAINT_CLASS[metrics.maintainability]}`}>
          {metrics.maintainability}
        </span>
      </div>
    </div>
  );
}
