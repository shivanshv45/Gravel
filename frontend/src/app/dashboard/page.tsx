"use client";

import { useSession, signOut } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export default function Dashboard() {
  const { data: session, status } = useSession();
  const router = useRouter();
  
  const [repoName, setRepoName] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [repos, setRepos] = useState<any[]>([]);

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
      
      const token = session?.accessToken;
      if (!token) return;

      const res = await fetch(`${apiUrl}/api/repos`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setRepos(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage("Scanning and parsing repository...");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      
      const token = session?.accessToken;

      const res = await fetch(`${apiUrl}/api/repos/ingest`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({ name: repoName, path: repoPath }),
      });

      const data = await res.json();
      if (res.ok) {
        setMessage(`Success! Parsed ${data.file_count} files in ${data.name}.`);
        setRepoName("");
        setRepoPath("");
        fetchRepos(); 
      } else {
        setMessage(`Error: ${data.detail || "Failed to ingest"}`);
      }
    } catch (err) {
      setMessage("An unexpected error occurred.");
    } finally {
      setLoading(false);
    }
  };

  if (status === "loading") {
    return <p style={{ padding: "2rem" }}>Loading...</p>;
  }

  if (!session) {
    return null;
  }

  return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif", maxWidth: "1000px", margin: "0 auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "2rem" }}>
        <h1>Gravel Dashboard</h1>
        <div>
          <span style={{ marginRight: "1rem" }}>{session.user?.email}</span>
          <button onClick={() => signOut()} style={{ padding: "0.5rem 1rem", cursor: "pointer", background: "#f44336", color: "white", border: "none", borderRadius: "4px" }}>
            Sign Out
          </button>
        </div>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
        {}
        <div style={{ padding: "2rem", border: "1px solid #ccc", borderRadius: "8px", background: "#f9f9f9", color: "#333" }}>
          <h2>Ingest Repository</h2>
          <p style={{ marginBottom: "1rem", color: "#666" }}>Point Gravel to a local folder to scan and parse its code.</p>
          
          <form onSubmit={handleIngest} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            <div>
              <label style={{ display: "block", marginBottom: "0.5rem" }}>Repository Name</label>
              <input 
                type="text" 
                value={repoName} 
                onChange={(e) => setRepoName(e.target.value)} 
                required 
                placeholder="e.g. My Secure API"
                style={{ width: "100%", padding: "0.5rem" }}
              />
            </div>
            <div>
              <label style={{ display: "block", marginBottom: "0.5rem" }}>Local Path (Absolute)</label>
              <input 
                type="text" 
                value={repoPath} 
                onChange={(e) => setRepoPath(e.target.value)} 
                required 
                placeholder="e.g. C:/Users/name/projects/my-api"
                style={{ width: "100%", padding: "0.5rem" }}
              />
            </div>
            <button 
              type="submit" 
              disabled={loading}
              style={{ padding: "0.75rem", background: loading ? "#999" : "#000", color: "white", border: "none", cursor: loading ? "wait" : "pointer", borderRadius: "4px" }}
            >
              {loading ? "Ingesting..." : "Scan & Parse Repository"}
            </button>
          </form>
          {message && <p style={{ marginTop: "1rem", fontWeight: "bold", color: message.includes("Error") ? "red" : "green" }}>{message}</p>}
        </div>

        {}
        <div style={{ padding: "2rem", border: "1px solid #ccc", borderRadius: "8px" }}>
          <h2>Your Indexed Repositories</h2>
          {repos.length === 0 ? (
            <p style={{ color: "#666", marginTop: "1rem" }}>No repositories indexed yet.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, marginTop: "1rem" }}>
              {repos.map(repo => (
                <li key={repo.id} style={{ padding: "1rem", borderBottom: "1px solid #eee", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                  <strong>{repo.name}</strong>
                  <span style={{ fontSize: "0.9rem", color: "#666" }}>{repo.local_path}</span>
                  <span style={{ fontSize: "0.85rem", background: "#e0f7fa", color: "#006064", padding: "0.2rem 0.5rem", borderRadius: "12px", width: "fit-content" }}>
                    {repo.file_count} files parsed
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
