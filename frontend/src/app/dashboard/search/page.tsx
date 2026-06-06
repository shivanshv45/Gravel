"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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

  const [query, setQuery] = useState("");
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<number | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/auth/login");
    } else if (status === "authenticated") {
      fetchRepos();
    }
  }, [status, router]);

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
        throw new Error("Search failed");
      }

      const data = await res.json();
      setResults(data.results);
    } catch (e) {
      console.error(e);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handleSearch();
    }
  };

  if (status === "loading") {
    return <div className={styles.container}><p>Loading...</p></div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Semantic Search</h1>
        <p>Search your codebase using natural language queries. Results are retrieved from differentially private embeddings.</p>
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

        <input
          className={styles.searchInput}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder='e.g. "Where is the authentication middleware?"'
        />

        <button
          className={styles.searchBtn}
          onClick={handleSearch}
          disabled={loading || !query.trim() || !selectedRepo}
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      <div className={styles.results}>
        {searched && results.length === 0 && !loading && (
          <div className={styles.noResults}>No results found. Make sure the repository is indexed first.</div>
        )}

        {results.map((r, i) => (
          <div key={i} className={styles.resultCard}>
            <div className={styles.resultHeader}>
              <span className={styles.filePath}>{r.file_path}</span>
              <span className={styles.score}>{(r.score * 100).toFixed(1)}% match</span>
            </div>
            <div className={styles.codeBlock}>{r.content}</div>
            <div className={styles.lineRange}>Lines {r.start_line}–{r.end_line}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
