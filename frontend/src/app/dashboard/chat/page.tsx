"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect, useState, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import styles from "./page.module.css";

interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  snippet: string;
  relevance_score: number;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  privacy_metadata?: Record<string, any>;
  model?: string;
  confidence_score?: number;
}

interface Repo {
  id: number;
  name: string;
  local_path: string;
  file_count: number;
}

export default function ChatPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const chatEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<number | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.push("/auth/login");
    } else if (status === "authenticated" && (session as any)?.accessToken) {
      fetchRepos();
    }
  }, [status, router, session]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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

  const handleSend = async () => {
    if (!input.trim() || !selectedRepo || loading) return;

    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
      const token = (session as any)?.accessToken;

      const res = await fetch(`${apiUrl}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          query: userMsg.content,
          repo_id: selectedRepo,
          top_k: 5,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Chat request failed");
      }

      const data = await res.json();

      const assistantMsg: Message = {
        role: "assistant",
        content: data.answer,
        citations: data.citations,
        privacy_metadata: data.privacy_metadata,
        model: data.model,
        confidence_score: data.privacy_metadata?.cipher_confidence,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Error: ${e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (status === "loading") {
    return <div className={styles.container}><p style={{ padding: "2rem" }}>Loading...</p></div>;
  }

  return (
    <div className={styles.container}>
      <div className={styles.chatArea}>
        {messages.length === 0 ? (
          <div className={styles.emptyState}>
            <h2>Ask Gravel Anything</h2>
            <p>
              Select a repository and ask questions about your codebase.
              Your code is protected with differential privacy.
            </p>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={styles.messageGroup}>
              {msg.role === "user" ? (
                <div className={styles.userMessage}>{msg.content}</div>
              ) : (
                <div className={styles.assistantMessage}>
                  <div className={styles.markdownContent}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>

                  {msg.citations && msg.citations.length > 0 && (
                    <div className={styles.citations}>
                      <span className={styles.citationsLabel}>Sources</span>
                      {msg.citations.map((c, j) => (
                        <div key={j} className={styles.citationItem}>
                          📄 {c.file_path}:{c.start_line}-{c.end_line}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}

        {loading && (
          <div className={styles.thinking}>
            <div className={styles.dot} />
            <div className={styles.dot} />
            <div className={styles.dot} />
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      <div className={styles.inputArea}>
        <div className={styles.inputRow}>
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

          <textarea
            className={styles.chatInput}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your codebase..."
            rows={1}
          />

          <button
            className={styles.sendBtn}
            onClick={handleSend}
            disabled={loading || !input.trim() || !selectedRepo}
          >
            {loading ? "Thinking..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}
