"use client";

import { useState, useEffect } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

interface ShortenResponse {
  short_code: string;
  short_url: string;
  original_url: string;
}

interface URLHistory {
  short_code: string;
  short_url: string;
  original_url: string;
  created_at: string;
}

export default function Home() {
  const [url, setUrl] = useState("");
  const [shortUrl, setShortUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState("");
  const [history, setHistory] = useState<URLHistory[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    setLoadingHistory(true);
    try {
      const response = await fetch("/api/urls", {
        signal: AbortSignal.timeout(10000), // 10 second timeout
      });
      if (response.ok) {
        const data = await response.json();
        setHistory(data);
      } else {
        console.error("Failed to fetch history: HTTP", response.status);
      }
    } catch (err) {
      if (err instanceof Error) {
        if (err.name === 'AbortError' || err.name === 'TimeoutError') {
          console.error("Request timeout: Backend server not responding");
        } else if (err.message.includes('fetch')) {
          console.error("Network error: Unable to connect to backend");
        } else {
          console.error("Failed to fetch history:", err.message);
        }
      }
    } finally {
      setLoadingHistory(false);
    }
  };

  const clearHistory = async () => {
    if (!confirm("Clear all shortened URLs?")) return;
    
    try {
      const response = await fetch(`${API_URL}/urls`, {
        method: "DELETE",
        signal: AbortSignal.timeout(10000),
      });
      
      if (response.ok) {
        setHistory([]);
        setShortUrl("");
      } else {
        const errorText = await response.text().catch(() => "Unknown error");
        setError(`Failed to clear history: ${errorText}`);
      }
    } catch (err) {
      if (err instanceof Error) {
        if (err.name === 'AbortError' || err.name === 'TimeoutError') {
          setError("Request timeout: Backend not responding");
        } else {
          setError(`Network error: ${err.message}`);
        }
      } else {
        setError("Failed to clear history");
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setShortUrl("");

    if (!url.trim()) {
      setError("Please enter a URL");
      return;
    }

    if (!url.startsWith("http://") && !url.startsWith("https://")) {
      setError("URL must start with http:// or https://");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch("/api/shorten", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
        signal: AbortSignal.timeout(10000),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({
          detail: `HTTP ${response.status}: ${response.statusText}`
        }));
        throw new Error(errorData.detail || "Failed to shorten URL");
      }

      const data: ShortenResponse = await response.json();
      setShortUrl(data.short_url);
      fetchHistory();
    } catch (err) {
      if (err instanceof Error) {
        if (err.name === 'AbortError' || err.name === 'TimeoutError') {
          setError("Request timeout: Backend server not responding");
        } else if (err.message.includes('fetch') || err.message.includes('Failed to fetch')) {
          setError("Network error: Unable to connect to backend. Is it running?");
        } else {
          setError(err.message);
        }
      } else {
        setError("An unexpected error occurred");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(id);
      setTimeout(() => setCopied(""), 2000);
    } catch (err) {
      setError("Failed to copy");
    }
  };

  const truncate = (str: string, max: number) => {
    return str.length > max ? str.substring(0, max) + "..." : str;
  };

  return (
    <div className="min-h-screen bg-[#0d0208] p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-3xl md:text-4xl font-bold text-[--matrix-text] mb-2">
            URL Shortener
          </h1>
          <p className="text-[--matrix-text-dim] text-sm">
            Shorten URLs quickly
          </p>
        </div>

        <div className="matrix-border bg-[--matrix-bg-secondary] rounded p-6 mb-6">
          <form onSubmit={handleSubmit} className="space-y-4">
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com/long/url"
              className="w-full px-4 py-3 matrix-input rounded font-mono text-sm"
              disabled={loading}
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full matrix-button py-3 px-6 rounded font-mono text-sm uppercase"
            >
              {loading ? "Processing..." : "Shorten"}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-3 border border-red-500 bg-red-900/20 rounded">
              <p className="text-red-400 font-mono text-sm">{error}</p>
            </div>
          )}

          {shortUrl && (
            <div className="mt-4 p-4 matrix-border bg-green-900/10 rounded">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={shortUrl}
                  readOnly
                  className="flex-1 px-3 py-2 matrix-input rounded font-mono text-sm"
                />
                <button
                  onClick={() => handleCopy(shortUrl, "main")}
                  className="matrix-button px-4 py-2 rounded font-mono text-sm"
                >
                  {copied === "main" ? "✓" : "Copy"}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="matrix-border bg-[--matrix-bg-secondary] rounded p-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold text-[--matrix-text]">
              History
            </h2>
            <div className="flex gap-2">
              <button
                onClick={fetchHistory}
                disabled={loadingHistory}
                className="matrix-button px-4 py-2 rounded font-mono text-xs"
              >
                {loadingHistory ? "..." : "Refresh"}
              </button>
              <button
                onClick={clearHistory}
                className="matrix-button px-4 py-2 rounded font-mono text-xs"
              >
                Clear
              </button>
            </div>
          </div>

          {history.length === 0 ? (
            <div className="text-center text-[--matrix-text-dim] py-8 font-mono text-sm">
              No URLs yet
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full font-mono text-xs">
                <thead>
                  <tr className="border-b border-[--matrix-border]">
                    <th className="text-left py-2 px-2 text-[--matrix-text-dim]">Original</th>
                    <th className="text-left py-2 px-2 text-[--matrix-text-dim]">Short URL</th>
                    <th className="text-center py-2 px-2 text-[--matrix-text-dim]">Code</th>
                    <th className="text-center py-2 px-2 text-[--matrix-text-dim]">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((item) => (
                    <tr
                      key={item.short_code}
                      className="border-b border-[--matrix-border] hover:bg-green-900/10"
                    >
                      <td className="py-2 px-2 text-[--matrix-text]">
                        {truncate(item.original_url, 40)}
                      </td>
                      <td className="py-2 px-2">
                        <a
                          href={item.short_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[--matrix-text] hover:underline"
                        >
                          {truncate(item.short_url, 30)}
                        </a>
                      </td>
                      <td className="py-2 px-2 text-center">
                        <span className="px-2 py-1 bg-[--matrix-green-dark] text-black rounded text-xs">
                          {item.short_code}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-center">
                        <button
                          onClick={() => handleCopy(item.short_url, item.short_code)}
                          className="matrix-button px-2 py-1 rounded text-xs"
                        >
                          {copied === item.short_code ? "✓" : "Copy"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
