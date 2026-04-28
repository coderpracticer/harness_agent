from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from harness.agents import EvaluatorAgent, SummaryGeneratorAgent, TemplateGeneratorAgent
from harness.llm_client import LLMSettings, create_llm_client
from harness.pipeline import SummarizationPipeline
from harness.reporting import persist_run_artifacts
from harness.rules import load_rules_config
from harness.templates import read_initial_template
from harness.workflows import run_evaluation_batch, run_optimization_batch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harness summary template iteration CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run one text prompt through template->summary->evaluation.")
    run_parser.add_argument("--prompt-file", required=True)
    run_parser.add_argument("--template-type", required=True)
    run_parser.add_argument("--rules-file", default="rules/scoring_rules.yaml")
    run_parser.add_argument("--max-iters", type=int, default=3)
    run_parser.add_argument("--target-score", type=int, default=85)
    run_parser.add_argument("--output-dir", default="")
    _add_llm_args(run_parser)

    optimize_parser = subparsers.add_parser("optimize", help="Optimize templates for all original docx files.")
    _add_batch_common_args(optimize_parser)
    optimize_parser.add_argument("--optimization-data-file", default="file_processing/150data.xlsx")
    optimize_parser.add_argument("--initial-template", required=True, help="Parent template file, for example 母模板.md.")
    optimize_parser.add_argument("--templates-dir", default="templates")
    optimize_parser.add_argument("--max-iters", type=int, default=3)
    optimize_parser.add_argument("--target-score", type=int, default=85)

    evaluate_parser = subparsers.add_parser("evaluate", help="Evaluate every summary folder against all originals.")
    _add_batch_common_args(evaluate_parser)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _run_command(args=args)
    if args.command == "optimize":
        return _optimize_command(args=args)
    if args.command == "evaluate":
        return _evaluate_command(args=args)
    parser.print_help()
    return 1


def _run_command(args: argparse.Namespace) -> int:
    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    context = prompt_path.read_text(encoding="utf-8")

    rules_config = load_rules_config(args.rules_file)
    llm_client = _create_client_from_args(args)
    pipeline = SummarizationPipeline(
        template_agent=TemplateGeneratorAgent(llm_client=llm_client),
        summary_agent=SummaryGeneratorAgent(llm_client=llm_client),
        evaluator_agent=EvaluatorAgent(llm_client=llm_client),
    )

    initial_template = None
    if getattr(args, "initial_template", ""):
        _, initial_template = read_initial_template(
            templates_dir=getattr(args, "templates_dir", "templates"),
            template_name=args.initial_template,
            template_type=args.template_type,
        )

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else Path("outputs") / run_id
    result = pipeline.run(
        context=context,
        template_type=args.template_type,
        rules_config=rules_config,
        initial_template=initial_template,
        max_iters=args.max_iters,
        target_score=args.target_score,
    )
    persist_run_artifacts(
        output_dir=output_dir,
        result=result,
        rules_config=rules_config,
        prompt_file=prompt_path,
    )

    print(f"Run completed. best_score={result.best_score}, best_round={result.best_round}")
    print(f"Artifacts: {output_dir.resolve()}")
    return 0


def _optimize_command(args: argparse.Namespace) -> int:
    rules_config = load_rules_config(args.rules_file)
    llm_client = _create_client_from_args(args)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else Path("outputs") / f"optimize_{run_id}"

    result = run_optimization_batch(
        file_processing_dir=args.file_processing_dir,
        optimization_data_file=args.optimization_data_file,
        templates_dir=args.templates_dir,
        initial_template_name=args.initial_template,
        run_id=run_id,
        output_dir=output_dir,
        template_type=args.template_type,
        rules_config=rules_config,
        template_agent=TemplateGeneratorAgent(llm_client=llm_client),
        summary_agent=SummaryGeneratorAgent(llm_client=llm_client),
        evaluator_agent=EvaluatorAgent(llm_client=llm_client),
        max_iters=args.max_iters,
        target_score=args.target_score,
        type_mapping_file=args.type_mapping_file,
        enable_multimodal_docx=args.enable_multimodal_docx,
    )
    print(f"Optimization completed. documents={result.processed_documents}")
    print(f"Artifacts: {result.output_dir.resolve()}")
    print(f"Generated templates: {result.generated_template_dir.resolve()}")
    return 0


def _evaluate_command(args: argparse.Namespace) -> int:
    rules_config = load_rules_config(args.rules_file)
    llm_client = _create_client_from_args(args)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else Path("outputs") / f"evaluate_{run_id}"

    result = run_evaluation_batch(
        file_processing_dir=args.file_processing_dir,
        run_id=run_id,
        output_dir=output_dir,
        template_type=args.template_type,
        rules_config=rules_config,
        evaluator_agent=EvaluatorAgent(llm_client=llm_client),
        type_mapping_file=args.type_mapping_file,
        enable_multimodal_docx=args.enable_multimodal_docx,
    )
    print(f"Evaluation completed. evaluated_pairs={result.evaluated_pairs}, missing_pairs={result.missing_pairs}")
    print(f"Comparison artifacts: {result.output_dir.resolve()}")
    return 0


def _add_batch_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--file-processing-dir", default="file_processing")
    parser.add_argument("--template-type", default="meeting", help="Fallback type when no filename keyword matches.")
    parser.add_argument("--type-mapping-file", default="file_processing/类型映射.yaml")
    parser.add_argument("--rules-file", default="rules/scoring_rules.yaml")
    parser.add_argument("--output-dir", default="")
    parser.add_argument(
        "--enable-multimodal-docx",
        action="store_true",
        help="Attach extracted docx images to OpenAI-compatible multimodal model requests.",
    )
    _add_llm_args(parser)


def _add_llm_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--llm-backend", choices=["heuristic", "openai"], default="")
    parser.add_argument("--model", default="", help="Model name for OpenAI-compatible backends.")
    parser.add_argument("--base-url", default="", help="OpenAI-compatible base URL, for example vLLM /v1.")
    parser.add_argument("--api-key", default="", help="API key. Optional for local/private base URLs.")
    parser.add_argument("--timeout-seconds", type=int, default=0, help="LLM request timeout in seconds.")


def _create_client_from_args(args: argparse.Namespace):
    settings = LLMSettings.from_env()
    if args.llm_backend:
        settings.backend = args.llm_backend
    if args.model:
        settings.model = args.model
    if args.base_url:
        settings.base_url = args.base_url
    if args.api_key:
        settings.api_key = args.api_key
    if args.timeout_seconds:
        settings.timeout_seconds = args.timeout_seconds
    return create_llm_client(settings=settings)


if __name__ == "__main__":
    raise SystemExit(main())
