"use client";

import { useState } from "react";
import styles from "./Repositories.module.css";

export default function Repositories() {
  const [repoName, setRepoName] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [isScanning, setIsScanning] = useState(false);

  const handleScan = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoName || !repoPath) return;

    setIsScanning(true);

    setTimeout(() => {
      setIsScanning(false);
      setRepoName("");
      setRepoPath("");
      alert("Mock: Repository scan completed! (This is a mock UI, no actual scan was performed)");
    }, 1500);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Repository Ingestion</h1>
        <p>Add local codebases for deep scanning and secure indexing.</p>
      </div>

      { }
      <div className={styles.mockNotice}>
        <strong>Note:</strong> This interface is currently a mock for design and layout purposes. Form submissions are simulated.
      </div>

      <div className={styles.ingestionFormCard}>
        <form onSubmit={handleScan}>
          <div className={styles.formGrid}>
            <div className={styles.inputGroup}>
              <label>REPOSITORY NAME</label>
              <input
                type="text"
                placeholder="e.g., core-services-api"
                value={repoName}
                onChange={(e) => setRepoName(e.target.value)}
                disabled={isScanning}
              />
            </div>

            <div className={styles.inputGroup}>
              <label>LOCAL ABSOLUTE PATH</label>
              <div className={styles.pathInputWrapper}>
                <span className={styles.folderIcon}>📁</span>
                <input
                  type="text"
                  placeholder="/Users/dev/projects/core-services"
                  value={repoPath}
                  onChange={(e) => setRepoPath(e.target.value)}
                  disabled={isScanning}
                />
              </div>
            </div>
          </div>

          <div className={styles.formActions}>
            <button type="submit" disabled={isScanning || !repoName || !repoPath} className={styles.scanButton}>
              {isScanning ? "SCANNING..." : "SCAN & PARSE"}
            </button>
          </div>
        </form>
      </div>

      <div className={styles.sectionHeader}>
        <h2>Indexed Repositories</h2>
        <div className={styles.line}></div>
      </div>

      <div className={styles.repoGrid}>
        { }
        <div className={styles.repoCard}>
          <div className={styles.repoCardHeader}>
            <div className={styles.repoTitle}>
              <span className={styles.repoIcon}>📁</span>
              <h3>auth-gateway</h3>
            </div>
            <div className={styles.statusBadge}>
              <span className={styles.checkIcon}>✓</span>
              Indexed
            </div>
          </div>
          <div className={styles.repoStats}>
            <div className={styles.stat}>
              <span className={styles.statLabel}>FILES</span>
              <span className={styles.statValue}>1,240</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>LANGUAGE</span>
              <span className={styles.statValue}>TypeScript</span>
            </div>
          </div>
        </div>

        { }
        <div className={styles.repoCard}>
          <div className={styles.repoCardHeader}>
            <div className={styles.repoTitle}>
              <span className={styles.repoIcon}>📁</span>
              <h3>payment-processor</h3>
            </div>
            <div className={styles.statusBadge}>
              <span className={styles.checkIcon}>✓</span>
              Indexed
            </div>
          </div>
          <div className={styles.repoStats}>
            <div className={styles.stat}>
              <span className={styles.statLabel}>FILES</span>
              <span className={styles.statValue}>856</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>LANGUAGE</span>
              <span className={styles.statValue}>Go</span>
            </div>
          </div>
        </div>

        { }
        <div className={styles.repoCard}>
          <div className={styles.repoCardHeader}>
            <div className={styles.repoTitle}>
              <span className={styles.repoIcon}>📁</span>
              <h3>frontend-client</h3>
            </div>
            <div className={styles.statusBadge}>
              <span className={styles.checkIcon}>✓</span>
              Indexed
            </div>
          </div>
          <div className={styles.repoStats}>
            <div className={styles.stat}>
              <span className={styles.statLabel}>FILES</span>
              <span className={styles.statValue}>3,102</span>
            </div>
            <div className={styles.stat}>
              <span className={styles.statLabel}>LANGUAGE</span>
              <span className={styles.statValue}>React / TS</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
