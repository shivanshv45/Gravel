"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import styles from "./page.module.css";

interface BudgetData {
  repo_id: number;
  repo_name: string;
  total_epsilon: number;
  epsilon_spent: number;
  epsilon_remaining: number;
  utilization_pct: number;
  num_operations: number;
}

interface Repo {
  id: number;
  name: string;
  local_path: string;
  file_count: number;
}

interface ConfigData {
  dp_epsilon: number;
  dp_clip_norm: number;
  dp_mechanism: string;
  retrieval_epsilon: number;
  llm_configured: boolean;
  llm_model: string;
  default_budget: number;
}

export default function PrivacyPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [repos, setRepos] = useState<Repo[]>([]);
  const [budgets, setBudgets] = useState<Map<number, BudgetData>>(new Map());
  const [loading, setLoading] = useState(true);
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/auth/login");
    } else if (status === "authenticated") {
      loadData();
    }
  }, [status, router]);

  const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const getToken = () => (session as any)?.accessToken;

  const loadData = async () => {
    try {
      // Load config
      const configRes = await fetch(`${getApiUrl()}/api/config`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (configRes.ok) {
        setConfig(await configRes.json());
      }

      // Load repos
      const res = await fetch(`${getApiUrl()}/api/repos`, {
        headers: { Authorization: `Bearer ${getToken()}` },
      });
      if (!res.ok) return;
      const repoData: Repo[] = await res.json();
      setRepos(repoData);

      const budgetMap = new Map<number, BudgetData>();
      for (const repo of repoData) {
        try {
          const budgetRes = await fetch(
            `${getApiUrl()}/api/indexing/${repo.id}/budget`,
            { headers: { Authorization: `Bearer ${getToken()}` } }
          );
          if (budgetRes.ok) {
            const b = await budgetRes.json();
            budgetMap.set(repo.id, { ...b, repo_name: repo.name });
          }
        } catch {}
      }
      setBudgets(budgetMap);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (repoId: number, newTotal?: number) => {
    try {
      const res = await fetch(
        `${getApiUrl()}/api/indexing/${repoId}/budget/reset`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify(newTotal ? { new_total: newTotal } : {}),
        }
      );
      if (res.ok) {
        setMessage(`Budget reset for repository.`);
        loadData();
      }
    } catch (e) {
      console.error(e);
    }
  };

  const getBarColor = (pct: number) => {
    if (pct < 50) return "var(--success)";
    if (pct < 80) return "#f59e0b";
    return "var(--danger)";
  };

  if (status === "loading" || loading) {
    return <div className={styles.container}><p>Loading...</p></div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Privacy Dashboard</h1>
        <p>
          Track your differential privacy epsilon (ε) budget per repository.
          Each indexing operation consumes epsilon. When the budget is exhausted,
          re-indexing is blocked until you reset it.
        </p>
      </div>

      {/* System Status */}
      {config && (
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "1rem",
          marginBottom: "2rem",
        }}>
          <div style={{
            padding: "1rem",
            background: "var(--panel-bg, #1a1a2e)",
            borderRadius: "8px",
            border: "1px solid var(--panel-border, #333)",
          }}>
            <div style={{ fontSize: "0.75rem", color: "var(--accent-muted, #888)", textTransform: "uppercase" }}>DP Mechanism</div>
            <div style={{ fontSize: "1.25rem", fontWeight: "bold", marginTop: "0.25rem" }}>{config.dp_mechanism}</div>
            <div style={{ fontSize: "0.8rem", color: "var(--accent-muted, #888)" }}>ε = {config.dp_epsilon} per chunk</div>
          </div>
          <div style={{
            padding: "1rem",
            background: "var(--panel-bg, #1a1a2e)",
            borderRadius: "8px",
            border: "1px solid var(--panel-border, #333)",
          }}>
            <div style={{ fontSize: "0.75rem", color: "var(--accent-muted, #888)", textTransform: "uppercase" }}>Clip Norm</div>
            <div style={{ fontSize: "1.25rem", fontWeight: "bold", marginTop: "0.25rem" }}>{config.dp_clip_norm}</div>
            <div style={{ fontSize: "0.8rem", color: "var(--accent-muted, #888)" }}>L2 sensitivity bound</div>
          </div>
          <div style={{
            padding: "1rem",
            background: "var(--panel-bg, #1a1a2e)",
            borderRadius: "8px",
            border: "1px solid var(--panel-border, #333)",
          }}>
            <div style={{ fontSize: "0.75rem", color: "var(--accent-muted, #888)", textTransform: "uppercase" }}>Retrieval ε</div>
            <div style={{ fontSize: "1.25rem", fontWeight: "bold", marginTop: "0.25rem" }}>{config.retrieval_epsilon}</div>
            <div style={{ fontSize: "0.8rem", color: "var(--accent-muted, #888)" }}>Exponential mechanism</div>
          </div>
          <div style={{
            padding: "1rem",
            background: config.llm_configured ? "var(--panel-bg, #1a1a2e)" : "#2a1a1a",
            borderRadius: "8px",
            border: `1px solid ${config.llm_configured ? "var(--panel-border, #333)" : "#5a2020"}`,
          }}>
            <div style={{ fontSize: "0.75rem", color: "var(--accent-muted, #888)", textTransform: "uppercase" }}>LLM Status</div>
            <div style={{ fontSize: "1.25rem", fontWeight: "bold", marginTop: "0.25rem", color: config.llm_configured ? "var(--success, #4caf50)" : "#f44336" }}>
              {config.llm_configured ? "✓ Connected" : "✗ No API Key"}
            </div>
            <div style={{ fontSize: "0.8rem", color: "var(--accent-muted, #888)" }}>
              {config.llm_configured ? config.llm_model : "Set GROQ_API_KEY in .env"}
            </div>
          </div>
        </div>
      )}

      {message && (
        <div style={{
          padding: "0.75rem 1rem",
          marginBottom: "1rem",
          background: "rgba(76, 175, 80, 0.1)",
          border: "1px solid rgba(76, 175, 80, 0.3)",
          borderRadius: "6px",
          color: "var(--success, #4caf50)",
          fontSize: "0.9rem",
        }}>
          {message}
        </div>
      )}

      <div className={styles.repoList}>
        {repos.length === 0 ? (
          <div className={styles.noRepos}>No repositories found. Ingest a repository first.</div>
        ) : (
          repos.map((repo) => {
            const budget = budgets.get(repo.id);
            const pct = budget?.utilization_pct ?? 0;
            const spent = budget?.epsilon_spent ?? 0;
            const remaining = budget?.epsilon_remaining ?? 1000;
            const total = budget?.total_epsilon ?? 1000;
            const ops = budget?.num_operations ?? 0;

            return (
              <div key={repo.id} className={styles.repoCard}>
                <div className={styles.repoCardHeader}>
                  <span className={styles.repoName}>{repo.name}</span>
                  <div style={{ display: "flex", gap: "0.5rem" }}>
                    <button className={styles.resetBtn} onClick={() => handleReset(repo.id)}>
                      Reset Budget
                    </button>
                  </div>
                </div>

                <div className={styles.budgetBar}>
                  <div className={styles.barTrack}>
                    <div
                      className={styles.barFill}
                      style={{
                        width: `${Math.min(pct, 100)}%`,
                        backgroundColor: getBarColor(pct),
                      }}
                    />
                  </div>
                  <div className={styles.barLabels}>
                    <span>{pct.toFixed(1)}% used</span>
                    <span>ε = {total}</span>
                  </div>
                </div>

                <div className={styles.statsGrid}>
                  <div className={styles.statBox}>
                    <div className={styles.statValue} style={{ color: "var(--success)" }}>
                      {remaining.toFixed(2)}
                    </div>
                    <div className={styles.statLabel}>ε Remaining</div>
                  </div>
                  <div className={styles.statBox}>
                    <div className={styles.statValue} style={{ color: "#f59e0b" }}>
                      {spent.toFixed(2)}
                    </div>
                    <div className={styles.statLabel}>ε Spent</div>
                  </div>
                  <div className={styles.statBox}>
                    <div className={styles.statValue}>{total}</div>
                    <div className={styles.statLabel}>ε Total</div>
                  </div>
                  <div className={styles.statBox}>
                    <div className={styles.statValue}>{ops}</div>
                    <div className={styles.statLabel}>Operations</div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
