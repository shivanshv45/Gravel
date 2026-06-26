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
    }, 1500);
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h1>Repository Ingestion</h1>
        <p>Add local codebases for deep scanning and secure indexing.</p>
      </div>

      { }

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
        { /* Repositories will be populated here */ }
      </div>
    </div>
  );
}
