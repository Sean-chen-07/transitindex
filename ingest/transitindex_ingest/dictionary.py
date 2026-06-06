"""Per-metric data dictionary: the single human + machine source of truth.

`metric_dictionary.yaml` holds the rich, human-authored spec for every metric
(what it IS / is NOT, included/excluded, EN+FR label variants as they appear in
annual reports, where it lives in a report, common confusions, source tier).
This module LOADS that file, JOINS it with the structural catalog
(`refdata.METRICS` for unit/unit_type/is_derived and `equations` for the formula
+ which equations each metric participates in), and GENERATES the surfaces that
must never drift from it:

  - `docs/data-dictionary.md`              -- the human doc (`generate_markdown`)
  - PDF-extraction prompt fragments        -- `pdf/llm.py` (Phase 4)
  - FOI request templates                  -- (Phase 4)
  - the workbook's inline definitions      -- `workbook.py` (Phase 3)

`yaml` is imported LAZILY, so importing this module never requires PyYAML; the
rest of the package stays pure stdlib (PyYAML is an optional dependency, like
openpyxl / anthropic).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .equations import EQUATIONS, display_formula
from .refdata import METRICS

# Source tiers a metric can be sourced from (mirrors source-registry.md tiers).
SOURCE_TIERS: frozenset[str] = frozenset(
    {"statcan", "open_data", "annual_report", "foi", "derived"}
)

# Required keys every YAML metric entry must carry (the rest are recommended).
_REQUIRED_FIELDS: tuple[str, ...] = (
    "display_name",
    "plain_meaning",
    "definition",
    "is_not",
    "source_tier",
)

_DICTIONARY_FILE = "metric_dictionary.yaml"


@dataclass(frozen=True)
class MetricSpec:
    """One metric's full spec: rich YAML fields joined with the structural catalog."""

    code: str
    display_name: str
    plain_meaning: str
    definition: str  # what it IS
    is_not: str  # what it is NOT
    unit: str  # from refdata
    unit_type: str  # from refdata
    is_derived: bool  # from refdata
    formula: Optional[str]  # from equations.display_formula (derived only)
    source_tier: str
    period_semantics: str = ""
    includes: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()
    labels_en: tuple[str, ...] = ()
    labels_fr: tuple[str, ...] = ()
    report_location: str = ""
    confusions: tuple[str, ...] = ()
    equations: tuple[str, ...] = ()  # equation codes this metric participates in


def _dictionary_path() -> str:
    return os.path.join(os.path.dirname(__file__), _DICTIONARY_FILE)


def _load_yaml() -> dict:
    """Parse the YAML file. Imports PyYAML lazily."""
    import yaml  # lazy: keeps the package stdlib-only unless the dictionary is used

    with open(_dictionary_path(), encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict) or "metrics" not in data:
        raise ValueError("metric_dictionary.yaml must have a top-level 'metrics:' map")
    return data["metrics"]


def _equations_for(code: str) -> tuple[str, ...]:
    """Equation codes whose operands include this metric."""
    return tuple(sorted(eq.code for eq in EQUATIONS if code in eq.operands))


def _tuple(value) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(str(v) for v in value)


def load_dictionary() -> dict[str, MetricSpec]:
    """Load every metric spec, in `refdata.METRICS` order.

    Rich human fields come from the YAML; unit/unit_type/is_derived come from
    `refdata` and the formula from the equation catalog -- so those structural
    facts have one source and cannot drift from the YAML.
    """
    raw = _load_yaml()
    problems = validate_dictionary(raw)
    if problems:
        raise ValueError("metric_dictionary.yaml invalid:\n  " + "\n  ".join(problems))

    specs: dict[str, MetricSpec] = {}
    for code, meta in METRICS.items():
        entry = raw[code]
        specs[code] = MetricSpec(
            code=code,
            display_name=str(entry["display_name"]),
            plain_meaning=str(entry["plain_meaning"]),
            definition=str(entry["definition"]),
            is_not=str(entry["is_not"]),
            unit=str(meta["unit"]),
            unit_type=str(meta["unit_type"]),
            is_derived=bool(meta["is_derived"]),
            formula=display_formula(code),
            source_tier=str(entry["source_tier"]),
            period_semantics=str(entry.get("period_semantics", "")),
            includes=_tuple(entry.get("includes")),
            excludes=_tuple(entry.get("excludes")),
            labels_en=_tuple(entry.get("labels_en")),
            labels_fr=_tuple(entry.get("labels_fr")),
            report_location=str(entry.get("report_location", "")),
            confusions=_tuple(entry.get("confusions")),
            equations=_equations_for(code),
        )
    return specs


def validate_dictionary(raw: dict) -> list[str]:
    """Return human-readable problems with the YAML (empty list = valid).

    Enforces parity (one entry per `refdata` metric, no extras) and that every
    entry carries the required fields with a known source tier.
    """
    problems: list[str] = []
    yaml_codes = set(raw)
    refdata_codes = set(METRICS)
    for missing in sorted(refdata_codes - yaml_codes):
        problems.append(f"missing dictionary entry for metric '{missing}'")
    for extra in sorted(yaml_codes - refdata_codes):
        problems.append(f"dictionary entry '{extra}' is not a known metric")
    for code in sorted(yaml_codes & refdata_codes):
        entry = raw[code]
        if not isinstance(entry, dict):
            problems.append(f"'{code}': entry must be a mapping")
            continue
        for field in _REQUIRED_FIELDS:
            if not entry.get(field):
                problems.append(f"'{code}': missing required field '{field}'")
        tier = entry.get("source_tier")
        if tier is not None and tier not in SOURCE_TIERS:
            problems.append(f"'{code}': unknown source_tier '{tier}'")
    return problems


# --- markdown generation -----------------------------------------------------

_GENERATED_HEADER = (
    "<!-- AUTO-GENERATED from ingest/transitindex_ingest/metric_dictionary.yaml. "
    "Do not hand-edit: run `python -m transitindex_ingest.dictionary` to regenerate. -->"
)

# Static narrative the table cannot carry (kept verbatim so the doc stays whole).
_FISCAL_NOTE = """\
## Years & fiscal years

Most agencies report on the **calendar year** (January–December), so a period labelled
"2024" means January to December 2024. Two agencies differ: **Metrolinx / GO Transit** and
**BC Transit** end their financial year in **March**, so their "2024" means the 2024–25 fiscal
year (April 2024 to March 2025), shown as "FY2024-25". Period granularity (monthly / quarterly
/ annual) is a **dimension** of each value, not part of the metric name — one `ridership`
metric holds monthly, quarterly, and annual figures, and the annual figure is the sum of the
twelve months when all twelve are present."""

_QUALITY_NOTE = """\
## Data quality & how calculated values stay honest

Every value carries a quality label (**verified** — from an audited/official figure;
**preliminary** — published but not final; **estimated** / **imputed** — a source's own
estimate). A **calculated** value never claims more certainty than its inputs: it inherits the
weakest input's quality. Calculated values are produced by exact arithmetic on same-period
values only — never across years or agencies, never dividing by zero, never fabricated. Each
one records the equation and the exact input values it came from, so it is fully reconstructable.
When a value is both published and calculable, the two are cross-checked; a disagreement is
flagged for review rather than silently resolved."""


def generate_markdown() -> str:
    """Render the full data-dictionary doc from the YAML + catalog. Deterministic."""
    specs = load_dictionary()
    lines: list[str] = [_GENERATED_HEADER, "", "# TransitIndex — Data Dictionary", ""]
    lines.append(
        "A precise, plain-language spec for every metric: what it is, what it is not, where it "
        "comes from, and the equations it links into. This file is the single source that drives "
        "PDF-extraction prompts, FOI request templates, and the spreadsheet's inline definitions."
    )
    lines.append("")

    # Summary table.
    lines.append("## All metrics at a glance")
    lines.append("")
    lines.append("| Metric | Plain meaning | Unit | Kind | Formula | Source |")
    lines.append("|---|---|---|---|---|---|")
    for s in specs.values():
        kind = "Calculated" if s.is_derived else "Sourced"
        formula = s.formula or "—"
        lines.append(
            f"| {s.display_name} | {s.plain_meaning} | {s.unit} | {kind} | {formula} | {s.source_tier} |"
        )
    lines.append("")

    # Per-metric detail.
    lines.append("## Metric specifications")
    lines.append("")
    for s in specs.values():
        lines.append(f"### {s.display_name} (`{s.code}`)")
        lines.append("")
        lines.append(f"- **Is:** {s.definition}")
        lines.append(f"- **Is NOT:** {s.is_not}")
        lines.append(f"- **Unit:** {s.unit} ({s.unit_type})")
        if s.formula:
            lines.append(f"- **Formula:** `{s.formula}`")
        if s.period_semantics:
            lines.append(f"- **Period:** {s.period_semantics}")
        if s.includes:
            lines.append(f"- **Includes:** {'; '.join(s.includes)}")
        if s.excludes:
            lines.append(f"- **Excludes:** {'; '.join(s.excludes)}")
        if s.labels_en:
            lines.append(f"- **Labels (EN):** {'; '.join(s.labels_en)}")
        if s.labels_fr:
            lines.append(f"- **Labels (FR):** {'; '.join(s.labels_fr)}")
        if s.report_location:
            lines.append(f"- **Where in a report:** {s.report_location}")
        if s.confusions:
            lines.append("- **Common confusions:**")
            for c in s.confusions:
                lines.append(f"  - {c}")
        if s.equations:
            lines.append(f"- **Equations:** {', '.join(f'`{e}`' for e in s.equations)}")
        lines.append(f"- **Source tier:** {s.source_tier}")
        lines.append("")

    lines.append(_FISCAL_NOTE)
    lines.append("")
    lines.append(_QUALITY_NOTE)
    lines.append("")
    return "\n".join(lines)


# --- extraction + FOI generators (the dictionary drives both) ----------------


def extraction_guidance(codes: Optional[list[str]] = None) -> str:
    """Per-metric guidance for the PDF-extraction system prompt.

    For each metric (default: the sourced ones a model may emit) emits what it IS
    / is NOT, the EN+FR labels it appears under in reports, where it lives, and the
    common confusions -- so the model maps a printed figure to the right metric and
    avoids the classic mix-ups (unlinked vs linked trips, operating vs total
    revenue, a metro car vs a bus in "fleet").
    """
    specs = load_dictionary()
    if codes is None:
        codes = [c for c, s in specs.items() if not s.is_derived]
    out: list[str] = []
    for code in codes:
        s = specs[code]
        out.append(f"- {code} ({s.display_name}): {s.definition}")
        if s.is_not:
            out.append(f"    NOT: {s.is_not}")
        if s.labels_en or s.labels_fr:
            en = "; ".join(s.labels_en)
            fr = "; ".join(s.labels_fr)
            out.append(f"    Appears as — EN: [{en}]  FR: [{fr}]")
        if s.report_location:
            out.append(f"    Where in a report: {s.report_location}")
        if s.confusions:
            out.append(f"    Watch out: {'; '.join(s.confusions)}")
    return "\n".join(out)


def foi_request_template(
    codes: list[str],
    *,
    agency: str = "[AGENCY]",
    years: str = "FY2022, FY2023, FY2024",
) -> str:
    """A plain-language data-request / FOI body for specific metrics.

    Each requested item carries the metric's precise definition + what is
    included/excluded, so a records officer knows exactly which figure is wanted
    (and is less likely to send the wrong line). Pairs with the channel guidance
    in foi-sourcing-plan.md (informal email first; FOI as the narrow fallback).
    """
    specs = load_dictionary()
    items: list[str] = []
    for code in codes:
        s = specs[code]
        line = f"  - {s.display_name}: {s.definition}"
        if s.includes:
            line += f" (include: {'; '.join(s.includes)})"
        if s.excludes:
            line += f" (exclude: {'; '.join(s.excludes)})"
        items.append(line)
    return (
        f"For {agency}, for fiscal years {years}, I'm requesting these figures — "
        f"from the audited financial statements / published operating statistics where "
        f"available:\n\n" + "\n".join(items) + "\n\n"
        "If any of these are already published, a link (or the spreadsheet behind the "
        "report) is perfect — I don't need a formal record where the data is already public."
    )


def write_markdown(path: Optional[str] = None) -> str:
    """Write `docs/data-dictionary.md` (or `path`). Returns the path written."""
    if path is None:
        # repo_root/ingest/transitindex_ingest/ -> repo_root/docs/data-dictionary.md
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        path = os.path.join(repo_root, "docs", "data-dictionary.md")
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(generate_markdown())
    return path


if __name__ == "__main__":  # pragma: no cover
    print("wrote", write_markdown())
