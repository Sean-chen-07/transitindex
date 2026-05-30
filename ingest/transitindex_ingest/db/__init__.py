"""Repository layer: the abstract write/read interface plus its backends.

`Repository` (Protocol) is what every pipeline component codes against.
`InMemoryRepository` is the offline workhorse for tests; `PostgresRepository`
is the real backend (psycopg, imported lazily).
"""

from .repository import Repository
from .memory import InMemoryRepository

__all__ = ["Repository", "InMemoryRepository"]
