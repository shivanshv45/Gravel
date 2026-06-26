"use client";

import { useState, useEffect } from "react";
import styles from "./page.module.css";

export default function Home() {
  const [view, setView] = useState<"loading" | "ingestion" | "chat">("loading");
  
  
  const [repoName, setRepoName] = useState("");
  const [repoPath, setRepoPath] = useState("");
  const [isScanning, setIsScanning] = useState(false);

  
  const [query, setQuery] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);

  
  useEffect(() => {
    if (view === "loading") {
      const timer = setTimeout(() => {
        setView("ingestion");
      }, 3500); 
      return () => clearTimeout(timer);
    }
  }, [view]);

  
  const handleScan = (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoName || !repoPath) return;
    
    setIsScanning(true);
    
    setTimeout(() => {
      setIsScanning(false);
      setView("chat");
    }, 2000);
  };

  
  const handleQuery = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    setIsProcessing(true);
    setTimeout(() => {
      setIsProcessing(false);
      setQuery("");
    }, 1500);
  };

  
  if (view === "loading") {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.loadingContent}>
          <h1 className={styles.loadingBrand}>GRAVEL</h1>
          
          <div className={styles.codeSkeleton}>
            <div className={`${styles.codeLineWrapper} ${styles.line1}`} style={{ width: '90%' }}>
              <div className={styles.codeLineMasked}></div>
            </div>
            <div className={`${styles.codeLineWrapper} ${styles.line2}`} style={{ width: '55%', marginLeft: '12%' }}>
              <div className={styles.codeLineMasked}></div>
            </div>
            <div className={`${styles.codeLineWrapper} ${styles.line3}`} style={{ width: '70%', marginLeft: '12%' }}>
              <div className={styles.codeLineMasked}></div>
            </div>
          </div>

        </div>
      </div>
    );
  }

  
  if (view === "ingestion") {
    return (
      <div className={styles.ingestionContainer}>
        <div className={styles.header}>
          <h1>Repository Ingestion</h1>
          <p>Add a local codebase to begin secure parsing and anonymization.</p>
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
                {isScanning ? "SECURING & PARSING..." : "SCAN & PARSE"}
              </button>
            </div>
          </form>
        </div>
        
      </div>
    );
  }

  
  return (
    <div className={styles.container}>

      <div className={styles.intelGrid}>
        {}
        <div className={styles.feedColumn}>
          <div className={styles.feedHeader}>
            <span>Chat</span>
          </div>

          <div className={styles.feedContent}>
            { /* Chat messages will appear here */ }
          </div>

          <div className={styles.inputArea}>
            <form onSubmit={handleQuery} className={styles.queryForm}>
              <input 
                type="text" 
                placeholder="Ask Gravel a question..." 
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                disabled={isProcessing}
                className={styles.queryInput}
              />
              <div className={styles.inputActions}>
                <button type="button" className={styles.iconBtn}>📁</button>
                <button type="button" className={styles.iconBtn}>⌨️</button>
                <button type="submit" disabled={isProcessing || !query.trim()} className={styles.submitBtn}>
                  {isProcessing ? "..." : "►"}
                </button>
              </div>
            </form>
          </div>
        </div>

        {}
        <div className={styles.skeletonColumn}>
          <div className={styles.skeletonHeader}>
            <div className={styles.skeletonTitle}>
              <span>⧉</span> Request Payload
            </div>
            <button className={styles.viewPayloadBtn}>
              👁️ View Details
            </button>
          </div>

          <div className={styles.codeView}>
            <pre className={styles.codeBlock}>
{}
            </pre>
          </div>
          <div className={styles.skeletonFooter}>
            <div className={styles.syncStatus}>
              <span className={styles.syncDot}></span> Synced
            </div>
            <div className={styles.lineCount}>LINES: 0</div>
          </div>
        </div>
      </div>
    </div>
  );
}
