import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Outfit } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const outfit = Outfit({ subsets: ["latin"], variable: "--font-outfit", display: "swap" });

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: {
    default: "TransitIndex — Canadian transit agency fundamentals",
    template: "%s · TransitIndex",
  },
  description:
    "A free directory of Canadian transit agencies ranked on the fundamentals. Every rank and every number is free to view.",
  openGraph: {
    title: "TransitIndex — Canadian transit agency fundamentals",
    description:
      "A free directory of Canadian transit agencies ranked on the fundamentals. Every rank and every number is free to view.",
    siteName: "TransitIndex",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "TransitIndex — Canadian transit agency fundamentals",
    description:
      "A free directory of Canadian transit agencies ranked on the fundamentals.",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={outfit.variable}>
      <body className="min-h-screen font-sans antialiased">
        <header className="border-b border-line bg-card/60">
          <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
            <Link
              href="/"
              className="-my-2 inline-flex items-center py-2 text-lg font-bold text-ink"
            >
              TransitIndex
            </Link>
            <span className="text-xs text-ink-3">Canadian transit fundamentals</span>
          </div>
        </header>
        <div className="mx-auto max-w-5xl px-4 py-10">{children}</div>
        <footer className="mt-16 border-t border-line">
          <div className="mx-auto max-w-5xl px-4 py-6 text-xs leading-relaxed text-ink-3">
            Every rank and every number is free to view, computed from public sources.
            Nothing is estimated; every figure is cited per agency.
          </div>
        </footer>
      </body>
    </html>
  );
}
