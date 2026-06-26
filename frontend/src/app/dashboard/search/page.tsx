"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import styles from "./page.module.css";

interface SearchResult {
  chunk_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  content: string;
  score: number;
}

interface Repo {
  id: number;
  name: string;
  local_path: string;
  file_count: number;
}

export default function SearchPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState("");
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<number | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState("");
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [totalResults, setTotalResults] = useState(0);
  const [searchTime, setSearchTime] = useState(0);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/auth/login");
    } else if (status === "authenticated" && (session as any)?.accessToken) {
      fetchRepos();
    }
  }, [status, router, session]);

  const fetchRepos = async () => {
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = (session as any)?.accessToken;
      if (!token) return;

      const res = await fetch(`${apiUrl}/api/repos`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setRepos(data);
        if (data.length > 0 && !selectedRepo) {
          setSelectedRepo(data[0].id);
        }
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSearch = async () => {
    if (!query.trim() || !selectedRepo || loading) return;

    setLoading(true);
    setSearched(true);
    setError("");
    setExpandedIdx(null);
    const startTime = performance.now();

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = (session as any)?.accessToken;

      const params = new URLSearchParams({
        q: query.trim(),
        repo_id: String(selectedRepo),
        top_k: "10",
      });

      const res = await fetch(`${apiUrl}/api/search?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || `Search failed (${res.status})`);
      }

      const data = await res.json();
      setResults(data.results);
      setTotalResults(data.total_results);
      setSearchTime(performance.now() - startTime);
    } catch (e: any) {
      console.error(e);
      setResults([]);
      setError(e.message || "Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return "var(--success)";
    if (score >= 0.5) return "#f59e0b";
    return "var(--accent-muted)";
  };

  const getFileExtension = (path: string) => {
    const ext = path.split(".").pop()?.toLowerCase() || "";
    return ext;
  };

  const getLanguageLabel = (path: string) => {
    const ext = getFileExtension(path);
    const map: Record<string, string> = {
      py: "Python",
      js: "JavaScript",
      ts: "TypeScript",
      tsx: "TSX",
      jsx: "JSX",
      rs: "Rust",
      go: "Go",
      java: "Java",
      c: "C",
      cpp: "C++",
      cs: "C#",
      rb: "Ruby",
      php: "PHP",
      css: "CSS",
      html: "HTML",
      md: "Markdown",
      json: "JSON",
      yaml: "YAML",
      yml: "YAML",
      sql: "SQL",
      sh: "Shell",
    };
    return map[ext] || ext.toUpperCase();
  };

  if (status === "loading") {
    return <div className={styles.container}><p>Loading...</p></div>;
  }

  const selectedRepoName = repos.find((r) => r.id === selectedRepo)?.name;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Semantic Search</h1>
        <p>Search your codebase using natural language queries.</p>
      </div>

      <div className={styles.searchBar}>
        <select
          className={styles.repoSelect}
          value={selectedRepo ?? ""}
          onChange={(e) => setSelectedRepo(Number(e.target.value))}
        >
          <option value="" disabled>Select repo</option>
          {repos.map((r) => (
            <option key={r.id} value={r.id}>{r.name}</option>
          ))}
        </select>

        <div className={styles.searchInputWrapper}>
          <span className={styles.searchIcon}>⌕</span>
          <input
            ref={inputRef}
            className={styles.searchInput}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder='e.g. "Where is the authentication middleware?"'
          />
          {query && (
            <button
              className={styles.clearBtn}
              onClick={() => { setQuery(""); inputRef.current?.focus(); }}
              aria-label="Clear search"
            >
              ✕
            </button>
          )}
        </div>

        <button
          className={styles.searchBtn}
          onClick={handleSearch}
          disabled={loading || !query.trim() || !selectedRepo}
        >
          {loading ? (
            <span className={styles.searchBtnLoading}>
              <span className={styles.spinner} />
              Searching
            </span>
          ) : (
            "Search"
          )}
        </button>
      </div>

      {/* Error message */}
      {error && (
        <div className={styles.errorBanner}>
          <span>⚠</span> {error}
        </div>
      )}

      {/* Results info bar */}
      {searched && !loading && !error && (
        <div className={styles.resultsInfo}>
          <span>
            {totalResults === 0
              ? "No results found"
              : `${totalResults} result${totalResults !== 1 ? "s" : ""} found`}
            {selectedRepoName && (
              <> in <strong>{selectedRepoName}</strong></>
            )}
          </span>
          {totalResults > 0 && (
            <span className={styles.searchTimeBadge}>
              {(searchTime / 1000).toFixed(2)}s
            </span>
          )}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className={styles.results}>
          {[1, 2, 3].map((i) => (
            <div key={i} className={styles.skeletonCard}>
              <div className={styles.skeletonHeader}>
                <div className={styles.skeletonLine} style={{ width: "60%" }} />
                <div className={styles.skeletonLine} style={{ width: "15%" }} />
              </div>
              <div className={styles.skeletonCode}>
                <div className={styles.skeletonLine} style={{ width: "80%" }} />
                <div className={styles.skeletonLine} style={{ width: "65%" }} />
                <div className={styles.skeletonLine} style={{ width: "90%" }} />
                <div className={styles.skeletonLine} style={{ width: "45%" }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!searched && !loading && (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>⌕</div>
          <h3>Search your codebase</h3>
          <p>
            {repos.length === 0
              ? "No repositories indexed yet. Ingest a repository from the dashboard first."
              : "Type a natural language query to find relevant code across your repositories."}
          </p>
          {repos.length > 0 && (
            <div className={styles.exampleQueries}>
              {[
                "Where is the authentication logic?",
                "How are API routes defined?",
                "Find error handling patterns",
              ].map((q) => (
                <button
                  key={q}
                  className={styles.exampleQuery}
                  onClick={() => {
                    setQuery(q);
                    inputRef.current?.focus();
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* No results */}
      {searched && results.length === 0 && !loading && !error && (
        <div className={styles.emptyState}>
          <div className={styles.emptyIcon}>∅</div>
          <h3>No results found</h3>
          <p>Try rephrasing your query or make sure the repository has been indexed.</p>
        </div>
      )}

      {/* Results */}
      {!loading && results.length > 0 && (
        <div className={styles.results}>
          {results.map((r, i) => {
            const isExpanded = expandedIdx === i;
            const lines = r.content.split("\n");
            const previewLines = lines.slice(0, 8);
            const hasMore = lines.length > 8;

            return (
              <div
                key={i}
                className={`${styles.resultCard} ${isExpanded ? styles.resultCardExpanded : ""}`}
              >
                <div className={styles.resultHeader}>
                  <div className={styles.fileInfo}>
                    <span className={styles.fileIcon}>📄</span>
                    <span className={styles.filePath}>{r.file_path}</span>
                    <span className={styles.langBadge}>{getLanguageLabel(r.file_path)}</span>
                  </div>
                  <span
                    className={styles.score}
                    style={{ color: getScoreColor(r.score) }}
                  >
                    {(r.score * 100).toFixed(1)}%
                  </span>
                </div>

                <div className={styles.codeContainer}>
                  <div className={styles.lineNumbers}>
                    {(isExpanded ? lines : previewLines).map((_, idx) => (
                      <span key={idx}>{r.start_line + idx}</span>
                    ))}
                  </div>
                  <pre className={styles.codeBlock}>
                    {isExpanded ? r.content : previewLines.join("\n")}
                  </pre>
                </div>

                <div className={styles.resultFooter}>
                  <span className={styles.lineRange}>
                    Lines {r.start_line}–{r.end_line}
                  </span>
                  {hasMore && (
                    <button
                      className={styles.expandBtn}
                      onClick={() => setExpandedIdx(isExpanded ? null : i)}
                    >
                      {isExpanded ? "Show less ▲" : `Show all ${lines.length} lines ▼`}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
