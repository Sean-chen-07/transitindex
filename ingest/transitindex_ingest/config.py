"""Runtime configuration. Reads the repo-root ``.env`` if present.

Uses python-dotenv when installed, otherwise a tiny stdlib parser, so config
loads with no third-party dependency. Both DATABASE_URL and ANTHROPIC_API_KEY
may be None offline -- callers that need them check at use time, never at import.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Repo root is two levels up from this file: <root>/ingest/transitindex_ingest/config.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_ENV_PATH = _REPO_ROOT / ".env"


@dataclass(frozen=True)
class Config:
    """Resolved settings. Anything unset in the environment/.env is None."""

    database_url: Optional[str]
    anthropic_api_key: Optional[str]
    review_api_token: Optional[str]


def load_config(env_path: Optional[Path] = None) -> Config:
    """Load settings from the process environment, layered over ``.env``.

    Real OS environment variables win over ``.env`` entries.
    """
    file_values = _read_env_file(env_path or _DEFAULT_ENV_PATH)
    return Config(
        database_url=os.environ.get("DATABASE_URL") or file_values.get("DATABASE_URL"),
        anthropic_api_key=(
            os.environ.get("ANTHROPIC_API_KEY") or file_values.get("ANTHROPIC_API_KEY")
        ),
        review_api_token=(
            os.environ.get("REVIEW_API_TOKEN") or file_values.get("REVIEW_API_TOKEN")
        ),
    )


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse ``.env`` into a dict. Prefers python-dotenv; stdlib fallback."""
    if not path.is_file():
        return {}
    try:
        from dotenv import dotenv_values  # type: ignore

        return {k: v for k, v in dotenv_values(path).items() if v is not None}
    except ImportError:
        return _parse_env_text(path.read_text(encoding="utf-8"))


def _parse_env_text(text: str) -> dict[str, str]:
    """Minimal KEY=VALUE parser: skips blanks/comments, strips quotes."""
    values: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values
