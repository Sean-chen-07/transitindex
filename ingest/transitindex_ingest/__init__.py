"""TransitIndex ingestion package.

Writes the `core.*` schema in Postgres (decoupling invariant #9: ingestion
writes, the web app only reads). Core logic is pure stdlib and offline-testable;
real-I/O adapters (psycopg, anthropic, pdfplumber, fastapi) import their deps
lazily so importing this package never requires them.
"""

from .contract import MetricValueRecord, SourceRef

__all__ = ["MetricValueRecord", "SourceRef"]
