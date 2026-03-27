import type { ReviewRequest } from "../types";

const LANGUAGES = [
  "python",
  "javascript",
  "typescript",
  "java",
  "go",
  "rust",
  "c",
  "cpp",
  "ruby",
  "php",
  "swift",
  "kotlin",
  "scala",
  "bash",
  "sql",
];

interface Props {
  value: ReviewRequest;
  loading: boolean;
  onChange: (req: ReviewRequest) => void;
  onSubmit: () => void;
}

export function CodeEditor({ value, loading, onChange, onSubmit }: Props) {
  function handleKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      if (!loading && value.code.trim()) onSubmit();
    }
  }

  return (
    <section className="editor-section">
      <div className="editor-controls">
        <select
          className="lang-select"
          value={value.language}
          onChange={(e) => onChange({ ...value, language: e.target.value })}
          disabled={loading}
          aria-label="Language"
        >
          {LANGUAGES.map((l) => (
            <option key={l} value={l}>
              {l}
            </option>
          ))}
        </select>

        <input
          className="filename-input"
          type="text"
          placeholder="filename.py (optional)"
          value={value.filename ?? ""}
          onChange={(e) =>
            onChange({ ...value, filename: e.target.value || undefined })
          }
          disabled={loading}
          aria-label="Filename"
        />
      </div>

      <textarea
        className="code-area"
        placeholder="Paste your code here…"
        value={value.code}
        onChange={(e) => onChange({ ...value, code: e.target.value })}
        onKeyDown={handleKey}
        disabled={loading}
        spellCheck={false}
        rows={20}
        aria-label="Code input"
      />

      <div className="editor-footer">
        <span className="char-count">{value.code.length.toLocaleString()} chars</span>
        <button
          className="submit-btn"
          onClick={onSubmit}
          disabled={loading || !value.code.trim()}
          aria-busy={loading}
        >
          {loading ? (
            <>
              <span className="dot-flashing" aria-hidden="true" />
              Reviewing…
            </>
          ) : (
            "Review Code"
          )}
        </button>
      </div>
    </section>
  );
}
