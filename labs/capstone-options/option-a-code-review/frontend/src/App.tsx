import { useState } from "react";
import { reviewCode } from "./api";
import { CodeEditor } from "./components/CodeEditor";
import { ReviewResults } from "./components/ReviewResults";
import type { ReviewRequest, ReviewResponse } from "./types";

const DEFAULT_REQUEST: ReviewRequest = {
  code: "",
  language: "python",
  filename: undefined,
};

export function App() {
  const [request, setRequest] = useState<ReviewRequest>(DEFAULT_REQUEST);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ReviewResponse | null>(null);

  async function handleSubmit() {
    if (!request.code.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const data = await reviewCode(request);
      setResults(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-inner">
          <h1 className="app-title">
            <span className="title-icon" aria-hidden="true">🔍</span>
            AI Code Review Bot
          </h1>
          <p className="app-subtitle">
            Paste code · select language · get categorised feedback from Claude
          </p>
        </div>
      </header>

      <main className="app-main">
        <CodeEditor
          value={request}
          loading={loading}
          onChange={setRequest}
          onSubmit={handleSubmit}
        />

        {error && (
          <div className="error-banner" role="alert">
            <strong>Error:</strong> {error}
          </div>
        )}

        {results && <ReviewResults results={results} />}
      </main>

      <footer className="app-footer">
        Powered by <a href="https://www.anthropic.com" target="_blank" rel="noreferrer">Claude</a>
        {" · "}
        <a href="/docs" target="_blank" rel="noreferrer">API docs</a>
      </footer>
    </div>
  );
}
