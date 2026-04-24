from __future__ import annotations

import json
from pathlib import Path

from harness.schemas import PipelineResult, RulesConfig


def persist_run_artifacts(
    *,
    output_dir: str | Path,
    result: PipelineResult,
    rules_config: RulesConfig,
    prompt_file: str | Path,
) -> Path:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)

    for round_log in result.round_logs:
        round_dir = base / f"round_{round_log.round_index}"
        round_dir.mkdir(parents=True, exist_ok=True)
        (round_dir / "template.md").write_text(round_log.template_draft.content, encoding="utf-8")
        (round_dir / "summary.md").write_text(round_log.summary_draft.content, encoding="utf-8")
        (round_dir / "evaluation.json").write_text(
            round_log.evaluation.model_dump_json(indent=2),
            encoding="utf-8",
        )

    final_dir = base / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    (final_dir / "template.md").write_text(result.final_template, encoding="utf-8")
    (final_dir / "summary.md").write_text(result.final_summary, encoding="utf-8")

    best_log = result.round_logs[result.best_round - 1]
    report_payload = {
        "prompt_file": str(prompt_file),
        "template_type": result.template_type,
        "best_round": result.best_round,
        "best_score": result.best_score,
        "stopped_reason": result.stopped_reason,
        "total_rounds": len(result.round_logs),
        "evaluation": best_log.evaluation.model_dump(),
    }
    (final_dir / "report.json").write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (final_dir / "report.md").write_text(
        _build_markdown_report(result=result, rules_config=rules_config),
        encoding="utf-8",
    )
    return base


def _build_markdown_report(*, result: PipelineResult, rules_config: RulesConfig) -> str:
    best_log = result.round_logs[result.best_round - 1]
    evaluation = best_log.evaluation
    evaluated_ids = set(evaluation.evaluated_rule_ids)
    triggered_ids = {item.rule_id for item in evaluation.deductions}
    non_triggered_ids = sorted(evaluated_ids - triggered_ids)
    total_deduction = sum(item.deducted_points for item in evaluation.deductions)

    lines: list[str] = []
    lines.append(f"# Final Score: {evaluation.total_score}/{evaluation.base_score}")
    lines.append("")
    lines.append(f"- Best Round: {result.best_round}")
    lines.append(f"- Stop Reason: {result.stopped_reason}")
    lines.append(f"- Total Deduction: {total_deduction}")
    lines.append("")
    lines.append("## Deduction Details")
    lines.append("")
    lines.append("| Rule ID | Rule Name | Deducted | Evidence | Rationale |")
    lines.append("|---|---|---:|---|---|")
    if evaluation.deductions:
        for item in evaluation.deductions:
            lines.append(
                f"| {item.rule_id} | {item.rule_name} | {item.deducted_points} | "
                f"{_escape_cell(item.evidence)} | {_escape_cell(item.rationale)} |"
            )
    else:
        lines.append("| - | - | 0 | No deductions | - |")

    lines.append("")
    lines.append("## Non-triggered Rules")
    lines.append("")
    if non_triggered_ids:
        for rule_id in non_triggered_ids:
            rule_name = _lookup_rule_name(rule_id=rule_id, rules_config=rules_config)
            lines.append(f"- {rule_id}: {rule_name}")
    else:
        lines.append("- None")

    lines.append("")
    lines.append("## Improvement Suggestions")
    lines.append("")
    if evaluation.suggestions:
        for suggestion in evaluation.suggestions:
            lines.append(f"- {suggestion}")
    else:
        lines.append("- No immediate suggestions.")

    if evaluation.warnings:
        lines.append("")
        lines.append("## Warnings")
        lines.append("")
        for warning in evaluation.warnings:
            lines.append(f"- {warning}")
    return "\n".join(lines).strip() + "\n"


def _lookup_rule_name(*, rule_id: str, rules_config: RulesConfig) -> str:
    for rule in rules_config.rules:
        if rule.id == rule_id:
            return rule.name
    return "Unknown rule"


def _escape_cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", "<br>")
