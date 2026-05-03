"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import styles from "./Sidebar.module.css";

export function Sidebar() {
  const pathname = usePathname();

  const navItems = [
    { name: "Chat", path: "/" },
    { name: "Repositories", path: "/repositories" },
    { name: "Privacy Logs", path: "/privacy-logs" },
    { name: "Settings", path: "/settings" },
  ];

  return (
    <aside className={styles.sidebar}>
      <div className={styles.brand}>
        <h2>GRAVEL</h2>
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
          <span>USER PROFILE</span>
        </div>
      </div>
    </aside>
  );
}
