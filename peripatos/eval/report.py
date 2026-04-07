from __future__ import annotations

from typing import Iterable

from peripatos.eval.compare import ComparisonResult


def _format_percent(value: float) -> str:
    return f"{value:.1f}%"


def _recommendation(results: Iterable[ComparisonResult]) -> tuple[str, str]:
    improved_metrics = 0
    for result in results:
        for delta in result.deltas.values():
            if delta >= 5.0:
                improved_metrics += 1
    if improved_metrics >= 2:
        return "ADOPT", "At least two metrics improved by ≥5%."
    if improved_metrics == 0:
        return "SKIP", "No metrics improved by ≥5%."
    return "INCONCLUSIVE", "Only one metric improved by ≥5%."


def generate_report(results: Iterable[ComparisonResult]) -> str:
    results_list = list(results)
    total = len(results_list)
    used_docling_eval = any(result.used_docling_eval for result in results_list)
    recommendation, rationale = _recommendation(results_list)

    lines: list[str] = []
    lines.append("# Evaluation Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Papers evaluated: {total}")
    lines.append(f"- Metrics source: {'docling-eval' if used_docling_eval else 'custom diff'}")
    lines.append(f"- Recommendation: {recommendation}")
    lines.append("")
    lines.append("## Per-Paper Results")
    lines.append("")

    for result in results_list:
        lines.append(f"### {result.paper_id}")
        lines.append(f"- Source: {result.source_path}")
        lines.append(f"- Used docling-eval: {result.used_docling_eval}")
        if result.notes:
            lines.append(f"- Notes: {result.notes}")
        lines.append("")
        lines.append("#### Metrics")
        lines.append("")
        for key, base_value in result.base_metrics.items():
            vlm_value = result.vlm_metrics.get(key)
            delta = result.deltas.get(key)
            if vlm_value is None or delta is None:
                continue
            lines.append(
                f"- {key}: base={base_value:.2f}, vlm={vlm_value:.2f}, delta={_format_percent(delta)}"
            )
        lines.append("")
        lines.append("#### Timing")
        lines.append(
            f"- base_seconds: {result.timing.get('base_seconds', 0.0):.2f}"
        )
        lines.append(
            f"- vlm_seconds: {result.timing.get('vlm_seconds', 0.0):.2f}"
        )
        lines.append("")

    lines.append("## Metrics")
    lines.append("")
    lines.append("Metrics are reported per paper in the section above.")
    lines.append("")
    lines.append("## Timing")
    lines.append("")
    lines.append("Timing is reported per paper in the section above.")
    lines.append("")
    lines.append("## Recommendation")
    lines.append("")
    lines.append(f"**{recommendation}** — {rationale}")

    return "\n".join(lines)
