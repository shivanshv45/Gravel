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

export default function PrivacyPage() {
  const { data: session, status } = useSession();
  const router = useRouter();

  const [repos, setRepos] = useState<Repo[]>([]);
  const [budgets, setBudgets] = useState<Map<number, BudgetData>>(new Map());
  const [loading, setLoading] = useState(true);

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

  const handleReset = async (repoId: number) => {
    try {
      const res = await fetch(
        `${getApiUrl()}/api/indexing/${repoId}/budget/reset`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${getToken()}` },
        }
      );
      if (res.ok) {
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
        <h1>Privacy Budget</h1>
        <p>
          Track your differential privacy epsilon (ε) budget per repository.
          Each indexing operation consumes epsilon. When the budget is exhausted,
          re-indexing is blocked until an admin resets it.
        </p>
      </div>

      <div className={styles.repoList}>
        {repos.length === 0 ? (
          <div className={styles.noRepos}>No repositories found. Ingest a repository first.</div>
        ) : (
          repos.map((repo) => {
            const budget = budgets.get(repo.id);
            const pct = budget?.utilization_pct ?? 0;
            const spent = budget?.epsilon_spent ?? 0;
            const remaining = budget?.epsilon_remaining ?? 10;
            const total = budget?.total_epsilon ?? 10;
            const ops = budget?.num_operations ?? 0;

            return (
              <div key={repo.id} className={styles.repoCard}>
                <div className={styles.repoCardHeader}>
                  <span className={styles.repoName}>{repo.name}</span>
                  <button className={styles.resetBtn} onClick={() => handleReset(repo.id)}>
                    Reset Budget
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
  );
}
