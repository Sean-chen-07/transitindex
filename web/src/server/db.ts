import "server-only";
import { drizzle } from "drizzle-orm/postgres-js";
import postgres from "postgres";
import * as schema from "@/db/schema";

// The ONE database connection for the whole server. Read-only by privilege: the
// DATABASE_URL login is a least-privilege web_reader member (see web/.env.example),
// so Postgres itself refuses DDL. Supabase session pooler (port 5432) → prepare:false
// is safe for both session and transaction poolers.
const url = process.env.DATABASE_URL;
if (!url) {
  throw new Error(
    "DATABASE_URL is not set. Copy web/.env.example to web/.env.local and set the web_reader connection string.",
  );
}

const globalForDb = globalThis as unknown as {
  __tiClient?: ReturnType<typeof postgres>;
};

const client = globalForDb.__tiClient ?? postgres(url, { prepare: false });
if (process.env.NODE_ENV !== "production") globalForDb.__tiClient = client;

export const db = drizzle(client, { schema });
