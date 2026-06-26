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
  const [resettingRepo, setResettingRepo] = useState<number | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/auth/login");
    } else if (status === "authenticated" && (session as any)?.accessToken) {
      loadData();
    }
  }, [status, router, session]);

  // Auto-dismiss success messages
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => setMessage(""), 4000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  const getApiUrl = () => process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const getToken = () => (session as any)?.accessToken;

  const loadData = async () => {
    const apiUrl = getApiUrl();
    const token = getToken();
    if (!token) {
      setLoading(false);
      return;
    }

    // Fetch config independently — don't let it block repos
    try {
      const configRes = await fetch(`${apiUrl}/api/config`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (configRes.ok) {
        setConfig(await configRes.json());
      }
    } catch (e) {
      console.error("Failed to load config:", e);
    }

    // Fetch repos and budgets
    try {
      const res = await fetch(`${apiUrl}/api/repos`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        setLoading(false);
        return;
      }
      const repoData: Repo[] = await res.json();
      setRepos(repoData);

      const budgetMap = new Map<number, BudgetData>();
      for (const repo of repoData) {
        try {
          const budgetRes = await fetch(
            `${apiUrl}/api/indexing/${repo.id}/budget`,
            { headers: { Authorization: `Bearer ${token}` } }
          );
          if (budgetRes.ok) {
            const b = await budgetRes.json();
            budgetMap.set(repo.id, { ...b, repo_name: repo.name });
          }
        } catch {}
      }
      setBudgets(budgetMap);
    } catch (e) {
      console.error("Failed to load repos:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async (repoId: number) => {
    if (!confirm("Reset the privacy budget for this repository? This will re-enable indexing.")) return;
    
    setResettingRepo(repoId);
    try {
      const res = await fetch(
        `${getApiUrl()}/api/indexing/${repoId}/budget/reset`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${getToken()}`,
          },
          body: JSON.stringify({}),
        }
      );
      if (res.ok) {
        setMessage("Privacy budget reset successfully.");
        loadData();
      }
    } catch (e) {
      console.error(e);
      setMessage("Failed to reset budget.");
    } finally {
      setResettingRepo(null);
    }
  };

  const getBarColor = (pct: number) => {
    if (pct < 50) return "var(--success)";
    if (pct < 80) return "#f59e0b";
    return "var(--danger)";
  };

  const getStatusLabel = (pct: number) => {
    if (pct < 50) return { text: "Healthy", className: styles.statusHealthy };
    if (pct < 80) return { text: "Moderate", className: styles.statusModerate };
    return { text: "Critical", className: styles.statusCritical };
  };

  if (status === "loading" || loading) {
    return <div className={styles.container}><p>Loading...</p></div>;
  }

  // Aggregate stats
  const totalBudget = Array.from(budgets.values()).reduce((a, b) => a + b.total_epsilon, 0);
  const totalSpent = Array.from(budgets.values()).reduce((a, b) => a + b.epsilon_spent, 0);
  const totalOps = Array.from(budgets.values()).reduce((a, b) => a + b.num_operations, 0);
  const avgUtilization = budgets.size > 0
    ? Array.from(budgets.values()).reduce((a, b) => a + b.utilization_pct, 0) / budgets.size
    : 0;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Privacy Dashboard</h1>
        <p>
          Monitor differential privacy epsilon (ε) consumption across your repositories.
          Each indexing operation consumes epsilon from the budget.
        </p>
      </div>

      {/* Success message */}
      {message && (
        <div className={styles.successBanner}>
          <span>✓</span> {message}
        </div>
      )}

      {/* System config cards */}
      {config && (
        <div className={styles.configSection}>
          <h2 className={styles.sectionTitle}>System Configuration</h2>
          <div className={styles.configGrid}>
            <div className={styles.configCard}>
              <div className={styles.configIcon}>ε</div>
              <div className={styles.configDetails}>
                <div className={styles.configValue}>{config.dp_epsilon}</div>
                <div className={styles.configLabel}>Epsilon per Chunk</div>
                <div className={styles.configSub}>
                  {config.dp_mechanism.charAt(0).toUpperCase() + config.dp_mechanism.slice(1)} mechanism
                </div>
              </div>
            </div>

            <div className={styles.configCard}>
              <div className={styles.configIcon}>‖·‖</div>
              <div className={styles.configDetails}>
                <div className={styles.configValue}>{config.dp_clip_norm}</div>
                <div className={styles.configLabel}>L2 Clip Norm</div>
                <div className={styles.configSub}>Sensitivity bound</div>
              </div>
            </div>

            <div className={styles.configCard}>
              <div className={styles.configIcon}>ε<sub>r</sub></div>
              <div className={styles.configDetails}>
                <div className={styles.configValue}>{config.retrieval_epsilon}</div>
                <div className={styles.configLabel}>Retrieval Epsilon</div>
                <div className={styles.configSub}>Exponential mechanism</div>
              </div>
            </div>

            <div className={`${styles.configCard} ${config.llm_configured ? styles.configCardOk : styles.configCardWarn}`}>
              <div className={styles.configIcon}>
                {config.llm_configured ? "✓" : "✗"}
              </div>
              <div className={styles.configDetails}>
                <div className={`${styles.configValue} ${config.llm_configured ? styles.valueOk : styles.valueWarn}`}>
                  {config.llm_configured ? "Connected" : "Not Connected"}
                </div>
                <div className={styles.configLabel}>LLM Status</div>
                <div className={styles.configSub}>
                  {config.llm_configured ? config.llm_model : "Set GROQ_API_KEY in .env"}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Aggregate overview */}
      {repos.length > 0 && (
        <div className={styles.overviewSection}>
          <h2 className={styles.sectionTitle}>Budget Overview</h2>
          <div className={styles.overviewGrid}>
            <div className={styles.overviewCard}>
              <div className={styles.overviewValue}>{totalSpent.toFixed(2)}</div>
              <div className={styles.overviewLabel}>Total ε Spent</div>
            </div>
            <div className={styles.overviewCard}>
              <div className={styles.overviewValue}>{(totalBudget - totalSpent).toFixed(2)}</div>
              <div className={styles.overviewLabel}>Total ε Remaining</div>
            </div>
            <div className={styles.overviewCard}>
              <div className={styles.overviewValue}>{avgUtilization.toFixed(1)}%</div>
              <div className={styles.overviewLabel}>Avg Utilization</div>
            </div>
            <div className={styles.overviewCard}>
              <div className={styles.overviewValue}>{totalOps}</div>
              <div className={styles.overviewLabel}>Total Operations</div>
            </div>
          </div>
        </div>
      )}

      {/* Per-repo budgets */}
      <div className={styles.repoSection}>
        <h2 className={styles.sectionTitle}>Repository Budgets</h2>
        <div className={styles.repoList}>
          {repos.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>ε</div>
              <h3>No repositories found</h3>
              <p>Ingest a repository from the dashboard to start tracking privacy budgets.</p>
            </div>
          ) : (
            repos.map((repo) => {
              const budget = budgets.get(repo.id);
              const pct = budget?.utilization_pct ?? 0;
              const spent = budget?.epsilon_spent ?? 0;
              const remaining = budget?.epsilon_remaining ?? 1000;
              const total = budget?.total_epsilon ?? 1000;
              const ops = budget?.num_operations ?? 0;
              const statusInfo = getStatusLabel(pct);

              return (
                <div key={repo.id} className={styles.repoCard}>
                  <div className={styles.repoCardHeader}>
                    <div className={styles.repoInfo}>
                      <span className={styles.repoName}>{repo.name}</span>
                      <span className={statusInfo.className}>{statusInfo.text}</span>
                    </div>
                    <button
                      className={styles.resetBtn}
                      onClick={() => handleReset(repo.id)}
                      disabled={resettingRepo === repo.id}
                    >
                      {resettingRepo === repo.id ? "Resetting..." : "Reset Budget"}
                    </button>
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
    </div>
  );
}
