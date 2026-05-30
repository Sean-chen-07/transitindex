"""Milestone 2: the LLM-assisted PDF extraction pipeline (Tier 2).

Turns an annual-report / budget PDF into core.pending_values rows. Tier 2
values ALWAYS land as review_status='pending' -- a human is the only door to
core.metric_values (Invariant #1). The package is split so the offline core
never needs the I/O deps:

  - extract.py  -- page text (pdfplumber imported lazily) + a passthrough.
  - llm.py      -- the extraction contract, the system prompt, and the
                   Anthropic (lazy) / Fake LLM clients.
  - pipeline.py -- run_pdf: extract -> llm -> MetricValueRecord -> stage pending.
"""

from __future__ import annotations

from .llm import (
    EXTRACTION_SYSTEM_PROMPT,
    AnthropicLLMClient,
    ExtractedValue,
    FakeLLMClient,
    LLMClient,
)
from .pipeline import run_pdf

__all__ = [
    "EXTRACTION_SYSTEM_PROMPT",
    "AnthropicLLMClient",
    "ExtractedValue",
    "FakeLLMClient",
    "LLMClient",
    "run_pdf",
]
