import { defineConfig } from "drizzle-kit";

// INTROSPECT-ONLY. The web app never defines or migrates tables — db/migrations
// (Lane 0) owns the schema. The only command wired in package.json is `db:pull`
// (drizzle-kit pull), which reads the live schema into committed read types.
// There is intentionally NO push/generate/migrate script. Belt-and-suspenders:
// DATABASE_URL must be a least-privilege login (web_reader-equivalent) so Postgres
// itself refuses any DDL even if a `push` were attempted by hand.
export default defineConfig({
  dialect: "postgresql",
  schemaFilter: ["core", "app"],
  out: "./src/db/schema",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
});
