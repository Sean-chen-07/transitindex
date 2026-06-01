import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

// In vitest's plain-Node env, the `server-only`/`client-only` marker packages throw on
// import (they depend on Next's bundler export conditions). Alias them to an empty module
// so server modules (queries.ts, entitlement.ts, …) can be imported and tested directly.
// This is test-only; the real `next build` still enforces the server/client boundary.
const emptyModule = fileURLToPath(new URL("./src/test/empty.ts", import.meta.url));

export default defineConfig({
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      "server-only": emptyModule,
      "client-only": emptyModule,
    },
  },
});
