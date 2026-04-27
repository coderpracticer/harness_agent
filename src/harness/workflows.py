from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from harness.agents import EvaluatorAgent, SummaryGeneratorAgent, TemplateGeneratorAgent
from harness.document_reader import list_docx_files, read_document_content
from harness.pipeline import SummarizationPipeline
from harness.reporting import persist_run_artifacts
from harness.rules import select_rules_for_type
from harness.schemas import EvaluationReport, RulesConfig, SummaryDraft, TemplateType
from harness.templates import (
    load_type_mapping,
    persist_generated_templates,
    read_template_for_scene,
    type_for_file,
)


@dataclass(frozen=True)
class OptimizeBatchResult:
    output_dir: Path
    generated_template_dir: Path
    processed_documents: int


@dataclass(frozen=True)
class EvaluationBatchResult:
    output_dir: Path
    evaluated_pairs: int
    missing_pairs: int


def run_optimization_batch(
    *,
    file_processing_dir: str | Path,
    templates_dir: str | Path,
    initial_template_name: str,
    run_id: str,
    output_dir: str | Path,
    template_type: TemplateType,
    rules_config: RulesConfig,
    template_agent: TemplateGeneratorAgent,
    summary_agent: SummaryGeneratorAgent,
    evaluator_agent: EvaluatorAgent,
    max_iters: int,
    target_score: int,
    type_mapping_file: str | Path | None = None,
    enable_multimodal_docx: bool = False,
) -> OptimizeBatchResult:
    original_dir = Path(file_processing_dir) / "original"
    original_files = list_docx_files(original_dir)
    if not original_files:
        raise FileNotFoundError(f"No .docx files found in {original_dir}")

    type_mapping = load_type_mapping(type_mapping_file)
    pipeline = SummarizationPipeline(
        template_agent=template_agent,
        summary_agent=summary_agent,
        evaluator_agent=evaluator_agent,
    )

    base_output = Path(output_dir)
    generated_base = Path(templates_dir) / "generated" / run_id
    manifest: list[dict[str, object]] = []

    for original_file in original_files:
        document_content = read_document_content(original_file, include_images=enable_multimodal_docx)
        detected_type = type_for_file(
            file_name=original_file.name,
            file_stem=original_file.stem,
            type_mapping=type_mapping,
            default_type=template_type,
        )
        initial_template_paths, initial_template = read_template_for_scene(
            templates_dir=templates_dir,
            template_name=initial_template_name,
            template_type=detected_type,
            scene_name=detected_type or None,
        )
        result = pipeline.run(
            context=document_content.text,
            template_type=detected_type,
            rules_config=rules_config,
            initial_template=initial_template,
            context_images=document_content.images,
            max_iters=max_iters,
            target_score=target_score,
        )
        doc_output = base_output / original_file.stem
        persist_run_artifacts(
            output_dir=doc_output,
            result=result,
            rules_config=rules_config,
            prompt_file=original_file,
        )
        generated_dir = persist_generated_templates(
            templates_dir=templates_dir,
            run_id=run_id,
            document_stem=original_file.stem,
            round_templates=[(log.round_index, log.template_draft.content) for log in result.round_logs],
            final_template=result.final_template,
        )
        manifest.append(
            {
                "document": str(original_file),
                "template_type": detected_type,
                "initial_template_components": [str(path) for path in initial_template_paths],
                "generated_template_dir": str(generated_dir),
                "best_round": result.best_round,
                "best_score": result.best_score,
            }
        )

    base_output.mkdir(parents=True, exist_ok=True)
    (base_output / "optimization_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return OptimizeBatchResult(
        output_dir=base_output,
        generated_template_dir=generated_base,
        processed_documents=len(original_files),
    )


def run_evaluation_batch(
    *,
    file_processing_dir: str | Path,
    run_id: str,
    output_dir: str | Path,
    template_type: TemplateType,
    rules_config: RulesConfig,
    evaluator_agent: EvaluatorAgent,
    type_mapping_file: str | Path | None = None,
    enable_multimodal_docx: bool = False,
) -> EvaluationBatchResult:
    base = Path(file_processing_dir)
    original_dir = base / "original"
    original_files = list_docx_files(original_dir)
    if not original_files:
        raise FileNotFoundError(f"No .docx files found in {original_dir}")

    summary_dirs = sorted(path for path in base.iterdir() if path.is_dir() and path.name != "original")
    if not summary_dirs:
        raise FileNotFoundError(f"No summary folders found in {base}")

    type_mapping = load_type_mapping(type_mapping_file)

    rows: list[dict[str, object]] = []
    missing: list[dict[str, str]] = []
    output_base = Path(output_dir)
    details_dir = output_base / "details"
    details_dir.mkdir(parents=True, exist_ok=True)

    for original_file in original_files:
        original_content = read_document_content(original_file, include_images=enable_multimodal_docx)
        detected_type = type_for_file(
            file_name=original_file.name,
            file_stem=original_file.stem,
            type_mapping=type_mapping,
            default_type=template_type,
        )
        selected_rules = select_rules_for_type(rules_config, template_type=detected_type)
        if not selected_rules:
            selected_rules = select_rules_for_type(rules_config, template_type=template_type)
        if not selected_rules:
            raise ValueError(f"No rules apply to template_type={detected_type}")
        for summary_dir in summary_dirs:
            summary_file = _match_summary_file(summary_dir=summary_dir, original_file=original_file)
            if summary_file is None:
                missing.append({"original": str(original_file), "summary_folder": str(summary_dir)})
                continue
            summary_content = read_document_content(summary_file, include_images=enable_multimodal_docx)
            report = evaluator_agent.evaluate(
                context=original_content.text,
                summary_draft=SummaryDraft(content=summary_content.text or "(empty summary)"),
                rules=selected_rules,
                base_score=rules_config.base_score,
                context_images=original_content.images,
                summary_images=summary_content.images,
            )
            detail_path = details_dir / f"{original_file.stem}__{summary_dir.name}.json"
            detail_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")
            rows.append(_evaluation_row(original_file, summary_dir, summary_file, detected_type, report, detail_path))

    _write_evaluation_outputs(output_base=output_base, run_id=run_id, rows=rows, missing=missing)
    return EvaluationBatchResult(
        output_dir=output_base,
        evaluated_pairs=len(rows),
        missing_pairs=len(missing),
    )


def _match_summary_file(*, summary_dir: Path, original_file: Path) -> Path | None:
    exact = summary_dir / original_file.name
    if exact.exists():
        return exact
    matches = sorted(summary_dir.glob(f"{original_file.stem}*.docx"))
    return matches[0] if matches else None


def _evaluation_row(
    original_file: Path,
    summary_dir: Path,
    summary_file: Path,
    template_type: str,
    report: EvaluationReport,
    detail_path: Path,
) -> dict[str, object]:
    return {
        "original_file": original_file.name,
        "summary_folder": summary_dir.name,
        "summary_file": summary_file.name,
        "template_type": template_type,
        "score": report.total_score,
        "total_deduction": report.total_deduction,
        "deduction_count": len(report.deductions),
        "deductions": "; ".join(f"{item.rule_id}:{item.deducted_points}" for item in report.deductions),
        "detail_path": str(detail_path),
    }


def _write_evaluation_outputs(
    *,
    output_base: Path,
    run_id: str,
    rows: list[dict[str, object]],
    missing: list[dict[str, str]],
) -> None:
    output_base.mkdir(parents=True, exist_ok=True)
    rows_sorted = sorted(rows, key=lambda item: (str(item["original_file"]), -int(item["score"]), str(item["summary_folder"])))

    (output_base / "comparison.json").write_text(
        json.dumps({"run_id": run_id, "results": rows_sorted, "missing": missing}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if rows_sorted:
        with (output_base / "comparison.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows_sorted[0].keys()))
            writer.writeheader()
            writer.writerows(rows_sorted)

    lines = [f"# Evaluation Comparison ({run_id})", ""]
    lines.append("| Original | Type | Summary Folder | Score | Total Deduction | Deductions |")
    lines.append("|---|---|---|---:|---:|---|")
    for row in rows_sorted:
        lines.append(
            f"| {row['original_file']} | {row['template_type']} | {row['summary_folder']} | {row['score']} | "
            f"{row['total_deduction']} | {row['deductions'] or '-'} |"
        )

    if missing:
        lines.extend(["", "## Missing Summary Files", ""])
        for item in missing:
            lines.append(f"- {item['original']} missing in {item['summary_folder']}")

    (output_base / "comparison.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
