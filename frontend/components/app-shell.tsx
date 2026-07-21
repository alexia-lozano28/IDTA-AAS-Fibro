"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import { Icon } from "./icons";

type NavigationItem = {
  href: string;
  label: string;
  icon: "overview" | "nameplate" | "technical" | "documents" | "upload";
  admin?: boolean;
};

const navigation: NavigationItem[] = [
  { href: "/", label: "Overview", icon: "overview" },
  { href: "/digital-nameplate", label: "Digital Nameplate", icon: "nameplate" },
  { href: "/technical-data", label: "Technical Data", icon: "technical" },
  { href: "/documents", label: "Documents", icon: "documents" },
  { href: "/admin-upload", label: "Admin Upload", icon: "upload", admin: true },
];

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Link className="brand" href="/" aria-label="FIBRO DPP home">
          <span className="brand-mark">F</span>
          <span><strong>FIBRO</strong><small>Digital Product Passport</small></span>
        </Link>
        <nav className="desktop-nav" aria-label="Product passport">
          {navigation.map((item) => {
            const active = pathname === item.href;
            return (
              <Link className={`nav-link${active ? " active" : ""}`} href={item.href} key={item.href} aria-current={active ? "page" : undefined}>
                <Icon name={item.icon} />
                <span>{item.label}</span>
                {item.admin && <span className="admin-chip">Admin</span>}
              </Link>
            );
          })}
        </nav>
        <div className="sidebar-footer">
          <span className="status-dot" />
          <span><strong>Demo passport</strong><small>Generated AAS JSON · POC</small></span>
        </div>
      </aside>

      <header className="mobile-header">
        <Link className="mobile-brand" href="/"><span className="brand-mark">F</span><strong>FIBRO DPP</strong></Link>
        <span className="demo-pill">Demo</span>
      </header>

      <main className="main-content">{children}</main>

      <nav className="mobile-nav" aria-label="Product passport">
        {navigation.map((item) => {
          const active = pathname === item.href;
          return (
            <Link className={active ? "active" : ""} href={item.href} key={item.href} aria-label={item.label} aria-current={active ? "page" : undefined}>
              <Icon name={item.icon} />
              <span>{item.label.replace("Digital ", "").replace("Technical ", "")}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
