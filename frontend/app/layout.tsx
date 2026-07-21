import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import "./globals.css";
import "./theme.css";

export const metadata: Metadata = {
  title: { default: "FIBROTOR ER.15 · Digital Product Passport", template: "%s · FIBRO DPP" },
  description: "Digital Product Passport for the FIBROTOR ER.15 rotary table.",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1, themeColor: "#f7f8f8" };

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return <html lang="en"><body><AppShell>{children}</AppShell></body></html>;
}
