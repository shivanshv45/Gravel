"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession, signOut } from "next-auth/react";
import styles from "./Sidebar.module.css";

export function Sidebar() {
  const pathname = usePathname();
  const { data: session } = useSession();

  const navItems = [
    { name: "Dashboard", path: "/dashboard" },
    { name: "Chat", path: "/dashboard/chat" },
    { name: "Search", path: "/dashboard/search" },
    { name: "Privacy", path: "/dashboard/privacy" },
  ];

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <h2>GRAVEL</h2>
        <span className={styles.version}>v1.0 · DP-ENABLED</span>
      </div>

      <div className={styles.shieldStatus}>
        🛡 PRIVACY SHIELD ACTIVE
      </div>

      <nav className={styles.nav}>
        {navItems.map((item) => (
          <Link
            key={item.path}
            href={item.path}
            className={`${styles.navItem} ${
              pathname === item.path ? styles.active : ""
            }`}
          >
            {item.name}
          </Link>
        ))}
      </nav>

      <div className={styles.footer}>
        <div className={styles.userProfile}>
          <span className={styles.userIcon}>👤</span>
          <span>{session?.user?.email || "USER"}</span>
        </div>
        {session && (
          <button
            onClick={() => signOut()}
            style={{
              width: "100%",
              marginTop: "0.5rem",
              padding: "0.5rem",
              background: "transparent",
              border: "1px solid var(--panel-border)",
              color: "var(--accent-muted)",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "0.75rem",
              textTransform: "uppercase",
              letterSpacing: "0.05em",
            }}
          >
            Sign Out
          </button>
        )}
      </div>
    </aside>
  );
}
