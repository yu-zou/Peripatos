from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol

from collections.abc import Mapping


@dataclass
class ComparisonResult:
    paper_id: str
    source_path: Path
    base_markdown: str
    vlm_markdown: str
    base_metrics: Mapping[str, float]
    vlm_metrics: Mapping[str, float]
    deltas: Mapping[str, float]
    timing: Mapping[str, float]
    used_docling_eval: bool
    notes: str | None = None


class DoclingDocument(Protocol):
    def export_to_markdown(self) -> str:
        ...


class DoclingResult(Protocol):
    document: DoclingDocument


class DoclingConverter(Protocol):
    def convert(self, source_path: Path) -> DoclingResult:
        ...


def _count_tables(markdown: str) -> int:
    return sum(1 for line in markdown.splitlines() if line.strip().startswith("|"))


def _count_equations(markdown: str) -> int:
    return markdown.count("$$") // 2


def _count_headings(markdown: str) -> int:
    return sum(1 for line in markdown.splitlines() if line.lstrip().startswith("#"))


def _edit_distance(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, char_a in enumerate(a, start=1):
        curr = [i]
        for j, char_b in enumerate(b, start=1):
            insert_cost = curr[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (char_a != char_b)
            curr.append(min(insert_cost, delete_cost, replace_cost))
        prev = curr
    return prev[-1]


def _compute_custom_metrics(markdown: str) -> dict[str, float]:
    return {
        "char_count": float(len(markdown)),
        "table_count": float(_count_tables(markdown)),
        "equation_count": float(_count_equations(markdown)),
        "heading_count": float(_count_headings(markdown)),
    }


def _compute_deltas(base_metrics: Mapping[str, float], vlm_metrics: Mapping[str, float]) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for key, base_value in base_metrics.items():
        vlm_value = vlm_metrics.get(key)
        if vlm_value is None:
            continue
        if base_value == 0:
            deltas[key] = 100.0 if vlm_value > 0 else 0.0
        else:
            deltas[key] = ((vlm_value - base_value) / base_value) * 100.0
    return deltas


def _convert(converter: DoclingConverter, source_path: Path) -> tuple[str, float]:
    start = perf_counter()
    result = converter.convert(source_path)
    markdown = result.document.export_to_markdown()
    return markdown, perf_counter() - start


def run_comparison(
    source_path: str | Path,
    *,
    base_converter: DoclingConverter,
    vlm_converter: DoclingConverter,
) -> ComparisonResult:
    path = Path(source_path)
    base_markdown, base_seconds = _convert(base_converter, path)
    vlm_markdown, vlm_seconds = _convert(vlm_converter, path)

    base_metrics = _compute_custom_metrics(base_markdown)
    vlm_metrics = _compute_custom_metrics(vlm_markdown)
    text_edit_distance = float(_edit_distance(base_markdown, vlm_markdown))
    base_metrics["edit_distance"] = text_edit_distance
    vlm_metrics["edit_distance"] = 0.0

    deltas = _compute_deltas(base_metrics, vlm_metrics)
    timing = {"base_seconds": base_seconds, "vlm_seconds": vlm_seconds}

    return ComparisonResult(
        paper_id=path.stem,
        source_path=path,
        base_markdown=base_markdown,
        vlm_markdown=vlm_markdown,
        base_metrics=base_metrics,
        vlm_metrics=vlm_metrics,
        deltas=deltas,
        timing=timing,
        used_docling_eval=False,
        notes="docling_eval not available; used custom diff metrics",
    )
