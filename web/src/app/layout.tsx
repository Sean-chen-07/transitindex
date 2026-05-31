import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Outfit } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit", display: "swap" });

export const metadata: Metadata = {
  title: {
    default: "TransitIndex — Canadian transit agency fundamentals",
    template: "%s · TransitIndex",
  },
  description:
    "A free directory of Canadian transit agencies ranked on the fundamentals. Ranks are free; the raw numbers are membership-only.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={outfit.variable}>
      <body className="min-h-screen font-sans antialiased">
        <header className="border-b border-line bg-card/60">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
            <Link href="/" className="text-lg font-bold text-ink">
              TransitIndex
            </Link>
            <span className="text-xs text-ink-3">Canadian transit fundamentals</span>
          </div>
        </header>
        <div className="mx-auto max-w-5xl px-4 py-10">{children}</div>
        <footer className="mt-16 border-t border-line">
          <div className="mx-auto max-w-5xl px-4 py-6 text-xs leading-relaxed text-ink-3">
            Ranks are free and computed from public sources. Raw numbers are
            membership-only. Nothing is estimated; every figure is cited per agency.
          </div>
        </footer>
      </body>
    </html>
  );
}
