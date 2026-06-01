// Auth.js v5 route handler. Runs in the Node.js runtime (default for route handlers),
// which the postgres-backed adapter requires.
import { handlers } from "@/server/auth";

export const { GET, POST } = handlers;
