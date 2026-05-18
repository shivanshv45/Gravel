import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";
import { Providers } from "@/components/Providers";
import { Sidebar } from "@/components/Sidebar";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});
const geistMono = localFont({
  src: "./fonts/GeistMonoVF.woff",
  variable: "--font-geist-mono",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "Gravel ",
  description: "Privacy-first AI-powered code intelligence platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable}`}>
        <Providers>
          <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
            <Sidebar />
            <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
              {}
              <header style={{ height: "60px", borderBottom: "1px solid var(--panel-border)", display: "flex", alignItems: "center", padding: "0 2rem", justifyContent: "space-between" }}>
                <div style={{ color: "var(--accent-muted)", fontSize: "0.875rem" }}>Gravel Dashboard</div>
                <div style={{ display: "flex", gap: "1rem" }}>
                   {}
                </div>
              </header>
              <main style={{ flex: 1, overflow: "hidden", minHeight: 0 }}>
                {children}
              </main>
            </div>
          </div>
        </Providers>
      </body>
    </html>
  );
}
