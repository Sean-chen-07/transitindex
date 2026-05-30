"""Minimal fetch + parse seams shared by source adapters.

A `Fetcher` returns the raw bytes/text behind a URL; `FileFetcher` reads a
local path (the offline default). An `Adapter` turns that raw text into a list
of `MetricValueRecord`s. No orchestration here -- callers wire fetch -> parse.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from ..contract import MetricValueRecord


@runtime_checkable
class Fetcher(Protocol):
    """Returns the raw payload at a URL/identifier."""

    def fetch(self, url: str) -> str: ...


class FileFetcher:
    """Reads a local file as UTF-8 text. The offline-friendly default."""

    def fetch(self, url: str) -> str:
        return Path(url).read_text(encoding="utf-8")


@runtime_checkable
class Adapter(Protocol):
    """Parses one source's raw text into canonical records."""

    def parse(self, raw_csv_text: str) -> list[MetricValueRecord]: ...
