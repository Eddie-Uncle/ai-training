import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import './App.css';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  const [task, setTask] = useState('');
  const [maxIter, setMaxIter] = useState(5);
  const [status, setStatus] = useState('idle'); // idle | running | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');

  async function run() {
    if (!task.trim() || status === 'running') return;
    setStatus('running');
    setResult(null);
    setError('');

    try {
      const res = await fetch(`${API_URL}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: task.trim(), max_iterations: maxIter }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || `Server error ${res.status}`);
      }

      const data = await res.json();
      setResult(data);
      setStatus('done');
    } catch (err) {
      const isNetwork = err.name === 'TypeError' || err.message.toLowerCase().includes('fetch');
      setError(isNetwork ? 'Cannot reach server — is it running?' : err.message);
      setStatus('error');
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) run();
  };

  return (
    <div className="page">
      <div className="wrap">

        {/* ── header ── */}
        <header className="hdr">
          <div>
            <h1 className="title">Agent Workspace</h1>
            <p className="sub">Researcher → Writer · powered by Claude</p>
          </div>
          {result && (
            <span className="chip">{result.steps_taken} steps</span>
          )}
        </header>

        {/* ── task input card ── */}
        <div className="card">
          <label className="lbl" htmlFor="task">Research prompt</label>
          <textarea
            id="task"
            className="ta"
            rows={4}
            placeholder="e.g. Write a brief blog post explaining how vector databases work…"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            onKeyDown={onKeyDown}
          />
          <div className="controls">
            <div className="controls-left">
              <span className="dim">Max steps</span>
              <select
                className="sel"
                value={maxIter}
                onChange={(e) => setMaxIter(+e.target.value)}
              >
                {[3, 4, 5, 6, 7, 8, 10].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
              <span className="dim hint-key">⌘ + ↵ to run</span>
            </div>
            <button
              className="btn"
              onClick={run}
              disabled={!task.trim() || status === 'running'}
            >
              {status === 'running' ? '…' : 'Run'}
            </button>
          </div>
          {status === 'error' && <p className="err">{error}</p>}
        </div>

        {/* ── output card ── */}
        {(status === 'running' || status === 'done') && (
          <div className="card">
            <div className="out-hdr">
              <span className="lbl">Output</span>
              {result && (
                <span className="dim">{result.steps_taken} agent steps</span>
              )}
            </div>

            {status === 'running' ? (
              <p className="working">
                <span className="dot" />
                Agents at work…
              </p>
            ) : (
              <div className="md">
                <ReactMarkdown>{result.result}</ReactMarkdown>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
