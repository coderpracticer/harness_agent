from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from harness.agents import EvaluatorAgent, SummaryGeneratorAgent, TemplateGeneratorAgent
from harness.llm_client import LLMSettings, create_llm_client
from harness.pipeline import SummarizationPipeline
from harness.reporting import persist_run_artifacts
from harness.rules import load_rules_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Harness summary template iteration CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run template->summary->evaluation iterative pipeline.")
    run_parser.add_argument("--prompt-file", required=True, help="Input file under prompt_dir (single task file).")
    run_parser.add_argument("--template-type", required=True, choices=["meeting", "interview"])
    run_parser.add_argument("--rules-file", default="rules/scoring_rules.yaml")
    run_parser.add_argument("--max-iters", type=int, default=3)
    run_parser.add_argument("--target-score", type=int, default=85)
    run_parser.add_argument("--output-dir", default="")
    run_parser.add_argument("--llm-backend", choices=["heuristic", "openai"], default="")
    run_parser.add_argument("--model", default="", help="Model name for OpenAI-compatible backends.")
    run_parser.add_argument("--base-url", default="", help="OpenAI-compatible base URL, for example vLLM /v1.")
    run_parser.add_argument("--api-key", default="", help="API key. Optional for local/private base URLs.")
    run_parser.add_argument("--timeout-seconds", type=int, default=0, help="LLM request timeout in seconds.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return _run_command(args=args)
    parser.print_help()
    return 1


def _run_command(args: argparse.Namespace) -> int:
    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
    context = prompt_path.read_text(encoding="utf-8")

    rules_config = load_rules_config(args.rules_file)

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
    llm_client = create_llm_client(settings=settings)

    template_agent = TemplateGeneratorAgent(llm_client=llm_client)
    summary_agent = SummaryGeneratorAgent(llm_client=llm_client)
    evaluator_agent = EvaluatorAgent(llm_client=llm_client)
    pipeline = SummarizationPipeline(
        template_agent=template_agent,
        summary_agent=summary_agent,
        evaluator_agent=evaluator_agent,
    )

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output_dir) if args.output_dir else Path("outputs") / run_id

    result = pipeline.run(
        context=context,
        template_type=args.template_type,
        rules_config=rules_config,
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


if __name__ == "__main__":
    raise SystemExit(main())
