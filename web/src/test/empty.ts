// Test-only stub. In vitest's plain-Node environment the `server-only` / `client-only`
// marker packages throw on import (they rely on Next's bundler export conditions, which
// vitest does not set). The vitest config aliases both to this empty module so server
// modules can be imported and exercised directly in tests. It changes nothing about the
// real build, where the genuine markers still enforce the server/client boundary.
export {};
