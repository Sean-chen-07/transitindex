"""Enable `python -m transitindex_ingest <command>`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
