export interface ReviewRequest {
  code: string;
  language: string;
  filename?: string;
}

export interface ReviewIssue {
  severity: "critical" | "high" | "medium" | "low";
  category: "bug" | "security" | "performance" | "style";
  line: number | null;
  description: string;
  suggestion: string;
}

export interface ReviewMetrics {
  overall_score: number;
  complexity: "low" | "medium" | "high";
  maintainability: "poor" | "fair" | "good" | "excellent";
}

export interface ReviewResponse {
  summary: string;
  issues: ReviewIssue[];
  suggestions: string[];
  metrics: ReviewMetrics;
}
