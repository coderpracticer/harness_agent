from pathlib import Path

from harness.reporting import persist_run_artifacts
from harness.schemas import (
    EvaluationReport,
    PipelineResult,
    RoundLog,
    Rule,
    RulesConfig,
    SummaryDraft,
    TemplateDraft,
)


def test_persist_run_artifacts_strips_think_blocks(tmp_path: Path):
    rules_config = RulesConfig(
        version="1.0",
        rules=[
            Rule(
                id="r1",
                name="Rule",
                applies_to="all",
                max_deduction=10,
                judge_prompt="Check",
                deduction_guide="0-10",
            )
        ],
    )
    evaluation = EvaluationReport(base_score=100, total_score=100, evaluated_rule_ids=["r1"])
    result = PipelineResult(
        template_type="meeting",
        best_round=1,
        best_score=100,
        stopped_reason="target reached",
        final_template="<think>\ninternal reasoning\n</think>\n# Final Template",
        final_summary="<think>hidden</think>\n# Final Summary",
        round_logs=[
            RoundLog(
                round_index=1,
                template_draft=TemplateDraft(
                    template_type="meeting",
                    content="<think>draft reasoning</think>\n# Round Template",
                ),
                summary_draft=SummaryDraft(content="<think>\nsummary reasoning\n</think>\n# Round Summary"),
                evaluation=evaluation,
            )
        ],
    )

    persist_run_artifacts(
        output_dir=tmp_path,
        result=result,
        rules_config=rules_config,
        prompt_file="prompt.md",
    )

    paths = [
        tmp_path / "round_1" / "template.md",
        tmp_path / "round_1" / "summary.md",
        tmp_path / "final" / "template.md",
        tmp_path / "final" / "summary.md",
    ]
    for path in paths:
        content = path.read_text(encoding="utf-8")
        assert "<think>" not in content
        assert "</think>" not in content
        assert "reasoning" not in content
        assert "hidden" not in content
