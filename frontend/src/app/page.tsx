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
      alert("Mock: Query processed! (This is a mock UI)");
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
        
        <div className={styles.mockNotice}>
          <strong>Note:</strong> Enter any mock details above. Hitting scan will transition you to the chat interface.
        </div>
      </div>
    );
  }

  
  return (
    <div className={styles.container}>
      <div className={styles.mockNotice}>
        <strong>Note:</strong> This chat/intel interface is currently a mock for design layout. It does not actually process queries yet.
      </div>

      <div className={styles.intelGrid}>
        {}
        <div className={styles.feedColumn}>
          <div className={styles.feedHeader}>
            <span>Chat</span>
          </div>

          <div className={styles.feedContent}>
            <div className={styles.messageRow}>
              <div className={styles.userQueryBox}>
                Analyze the recent authentication failures in cluster gamma. Identify any patterns related to the deprecated v2 API endpoints.
              </div>
              <div className={styles.userLabel}>You 👤</div>
            </div>

            <div className={styles.messageRow}>
              <div className={styles.aiLabel}>🧠 Gravel Assistant</div>
              <div className={styles.aiResponseBox}>
                <p>Analysis complete. Correlated <span className={styles.highlightBlock}>482</span> events across cluster gamma over the last 72 hours.</p>
                <p>Identified primary vector: Legacy services attempting payload validation against <code className={styles.inlineCode}>/api/v2/auth/token</code> which was aggressively rate-limited post-migration.</p>
                
                <div className={styles.aiResponseFooter}>
                  <span>CONFIDENCE: 98.4%</span>
                  <span className={styles.actionReq}>Action Required</span>
                </div>
              </div>
            </div>

            <div className={styles.messageRow}>
              <div className={styles.userQueryBox}>
                Generate the patch script to redirect those calls to v3, keeping the payload structure intact.
              </div>
              <div className={styles.userLabel}>You 👤</div>
            </div>

             <div className={styles.messageRow}>
              <div className={styles.aiLabel}>🔄 Processing...</div>
              <div className={styles.processingBox}>
                Awaiting input
              </div>
            </div>
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
{`{
  "stream_id": "sys_gamma_auth_fail_0x9A",
  "timestamp": 1715849201,
  "anonymized_entities": [
    {
      "id": "ENT_001",
      "type": "ipv4_hash",
      "val": "[REDACTED_HASH_A]"
    },
    {
      "id": "ENT_002",
      "type": "service_account",
      "val": "svc_legacy_importer"
    }
  ],
  "logic_block_generated": {
    "target": "api_gateway_routes",
    "action": "REWRITE",
    "script": "
      function process_route(req) {
        if (req.path === '/api/v2/auth/token') {
          log_event('REDIRECT_V3', req.headers);
          return redirect('/api/v3/auth/token', 307);
        }
        return continue();
      }
    "
  },
  "privacy_policy_applied": true,
  "execution_clearance": "PENDING_ADMIN_APPROVAL"
}`}
            </pre>
          </div>
          <div className={styles.skeletonFooter}>
            <div className={styles.syncStatus}>
              <span className={styles.syncDot}></span> Synced
            </div>
            <div className={styles.lineCount}>LINES: 34</div>
          </div>
        </div>
      </div>
    </div>
  );
}
