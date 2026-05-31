import type { NextConfig } from "next";
import { fileURLToPath } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));

const nextConfig: NextConfig = {
  // Pin the file-tracing root to web/ (a stray lockfile in the home dir otherwise
  // confuses Next's workspace-root inference).
  outputFileTracingRoot: here,
  // `postgres` (postgres-js) is server-only; keep it out of the bundler so it runs as
  // a normal Node dependency in server components / route handlers.
  serverExternalPackages: ["postgres"],
};

export default nextConfig;
