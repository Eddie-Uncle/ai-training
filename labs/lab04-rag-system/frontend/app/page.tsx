'use client';

import { useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Falls back to the deployed Railway URL if no env var is set
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'https://api-production-7a05.up.railway.app';

interface Source {
  file: string;
  type?: string;
  name?: string;
  line?: number;
  relevance: number;
}

interface SearchResult {
  answer: string;
  sources: Source[];
  context_used: string;
}

interface IndexResult {
  indexed_chunks: number;
  files_indexed: number;
  repo: string;
}

export default function Home() {
  // ── Index state ──────────────────────────────────────────────────────────
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [indexing, setIndexing] = useState(false);
  const [indexResult, setIndexResult] = useState<IndexResult | null>(null);
  const [indexError, setIndexError] = useState('');

  // ── Query state ───────────────────────────────────────────────────────────
  const [question, setQuestion] = useState('');
  const [searching, setSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [searchError, setSearchError] = useState('');

  // ── Meta state ────────────────────────────────────────────────────────────
  const [provider, setProvider] = useState('');
  const [chunkCount, setChunkCount] = useState<number | null>(null);

  // ── Fetch server info on mount ────────────────────────────────────────────
  const fetchStats = useCallback(async () => {
    try {
      const [health, stats] = await Promise.all([
        fetch(`${API_URL}/health`).then((r) => r.json()),
        fetch(`${API_URL}/stats`).then((r) => r.json()),
      ]);
      setProvider(health.provider ?? '');
      setChunkCount(stats.count ?? 0);
    } catch {
      // server may be cold-starting
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  // ── Index a GitHub repo ───────────────────────────────────────────────────
  const handleIndex = async () => {
    if (!repoUrl.trim()) return;
    setIndexing(true);
    setIndexError('');
    setIndexResult(null);
    try {
      const res = await fetch(`${API_URL}/index/github`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: repoUrl.trim(),
          branch: branch.trim() || undefined,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Indexing failed');
      setIndexResult(data);
      setChunkCount(data.indexed_chunks);
    } catch (e: unknown) {
      setIndexError(e instanceof Error ? e.message : 'Indexing failed');
    } finally {
      setIndexing(false);
    }
  };

  // ── Clear the vector index ────────────────────────────────────────────────
  const handleClear = async () => {
    await fetch(`${API_URL}/index`, { method: 'DELETE' });
    setIndexResult(null);
    setChunkCount(0);
    setSearchResult(null);
    setSearchError('');
    setQuestion('');
  };

  // ── Query the indexed codebase ────────────────────────────────────────────
  const handleSearch = async () => {
    if (!question.trim()) return;
    setSearching(true);
    setSearchError('');
    setSearchResult(null);
    try {
      const res = await fetch(`${API_URL}/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: question.trim(), n_results: 5 }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? 'Search failed');
      setSearchResult(data);
    } catch (e: unknown) {
      setSearchError(e instanceof Error ? e.message : 'Search failed');
    } finally {
      setSearching(false);
    }
  };

  return (
    <main className="max-w-3xl mx-auto px-6 py-10">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-3">
          🔍 RAG Code Search — Training Module 4
        </h1>
        <div className="flex gap-2 items-center flex-wrap">
          {provider && (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
              Provider: {provider}
            </span>
          )}
          {chunkCount !== null && (
            <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-700">
              {chunkCount} chunks
            </span>
          )}
        </div>
      </div>

      {/* ── Index GitHub Repository ─────────────────────────────────────── */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">
          Index GitHub Repository
        </h2>
        <div className="flex gap-2 mb-2 flex-wrap sm:flex-nowrap">
          <input
            type="url"
            className="flex-1 min-w-0 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="https://github.com/owner/repo"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleIndex()}
          />
          <input
            type="text"
            className="w-36 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="branch (optional)"
            value={branch}
            onChange={(e) => setBranch(e.target.value)}
          />
          <button
            onClick={handleIndex}
            disabled={indexing || !repoUrl.trim()}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
          >
            {indexing ? 'Indexing…' : 'Index'}
          </button>
          <button
            onClick={handleClear}
            className="px-4 py-2 bg-white text-gray-700 text-sm font-medium rounded border border-gray-300 hover:bg-gray-50 whitespace-nowrap"
          >
            Clear
          </button>
        </div>
        <p className="text-xs text-gray-500 mb-3">
          Paste a public GitHub repository URL, index it, then ask questions below.
        </p>

        {indexing && (
          <div className="border border-blue-200 bg-blue-50 px-4 py-3 rounded text-sm text-blue-700">
            Fetching files and building embeddings — this may take 30–60 seconds for large repos…
          </div>
        )}
        {indexError && (
          <div className="border-l-4 border-red-500 bg-red-50 px-4 py-3 rounded text-sm text-red-700">
            {indexError}
          </div>
        )}
        {indexResult && !indexError && (
          <div className="border-l-4 border-green-500 bg-green-50 px-4 py-3 rounded text-sm text-green-700">
            Indexed {indexResult.indexed_chunks} chunks from {indexResult.files_indexed} files (
            {indexResult.repo})
          </div>
        )}
      </section>

      {/* ── Search bar ─────────────────────────────────────────────────── */}
      <div className="flex gap-2 mb-8">
        <input
          type="text"
          className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="how does authentication work?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
        />
        <button
          onClick={handleSearch}
          disabled={searching || !question.trim()}
          className="px-5 py-2 bg-blue-600 text-white text-sm font-medium rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          {searching ? 'Searching…' : 'Search'}
        </button>
      </div>

      {/* ── Answer ─────────────────────────────────────────────────────── */}
      {searchError && (
        <div className="border-l-4 border-red-500 bg-red-50 px-4 py-3 rounded text-sm text-red-700 mb-4">
          {searchError}
        </div>
      )}

      {searching && (
        <div className="border-l-4 border-blue-300 bg-blue-50 px-4 py-3 rounded text-sm text-blue-600 mb-4">
          Generating answer…
        </div>
      )}

      {searchResult && (
        <section>
          {/* Answer box */}
          <div className="border-l-4 border-blue-500 pl-4 py-1 mb-6">
            <p className="text-sm font-semibold text-blue-600 mb-2">Answer</p>
            <div className="prose prose-sm max-w-none text-gray-800">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  code({ children, ...props }: any) {
                    const isBlock = /\n/.test(String(children ?? ''));
                    if (isBlock) {
                      return (
                        <pre className="bg-gray-50 border border-gray-200 rounded p-3 overflow-x-auto my-3">
                          <code className="text-xs font-mono text-gray-800" {...props}>
                            {children}
                          </code>
                        </pre>
                      );
                    }
                    return (
                      <code
                        className="bg-gray-100 text-blue-700 px-1.5 py-0.5 rounded text-xs font-mono"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  },
                }}
              >
                {searchResult.answer}
              </ReactMarkdown>
            </div>
          </div>

          {/* Sources */}
          {searchResult.sources.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Sources
              </p>
              <div className="space-y-1.5">
                {searchResult.sources.map((src, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-xs text-gray-600 flex-wrap"
                  >
                    <span className="font-mono bg-gray-100 px-1.5 py-0.5 rounded">
                      {src.file}
                    </span>
                    {src.name && (
                      <span className="text-gray-400">
                        {src.type}: {src.name}
                      </span>
                    )}
                    {src.line && (
                      <span className="text-gray-400">L{src.line}</span>
                    )}
                    <span className="ml-auto text-gray-400 tabular-nums">
                      {Math.round(src.relevance * 100)}% match
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
