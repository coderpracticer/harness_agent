from harness.agents import EvaluatorAgent, SummaryGeneratorAgent, TemplateGeneratorAgent
from harness.llm_client import HeuristicLLMClient
from harness.pipeline import SummarizationPipeline
from harness.pipeline import truncate_context
from harness.schemas import (
    DeductionItem,
    EvaluationReport,
    RoundLog,
    Rule,
    RulesConfig,
    SummaryDraft,
    TemplateDraft,
)


def test_evaluator_clamps_out_of_range_deduction():
    evaluator = EvaluatorAgent(llm_client=HeuristicLLMClient())
    rules = [
        Rule(
            id="r1",
            name="Clamp Rule",
            applies_to="all",
            max_deduction=5,
            judge_prompt="force_over_max",
            deduction_guide="test",
        )
    ]
    report = evaluator.evaluate(context="a", summary_draft=SummaryDraft(content="b"), rules=rules, base_score=100)
    assert report.total_score == 95
    assert report.deductions[0].deducted_points == 5
    assert any("clamped" in warning for warning in report.warnings)


def test_pipeline_stops_when_target_reached():
    rules = RulesConfig(
        version="1.0",
        base_score=100,
        rules=[
            Rule(
                id="rule_ok",
                name="结构",
                applies_to="all",
                max_deduction=10,
                judge_prompt="检查结构",
                deduction_guide="0-10",
            )
        ],
    )
    pipeline = SummarizationPipeline(
        template_agent=TemplateGeneratorAgent(llm_client=HeuristicLLMClient()),
        summary_agent=SummaryGeneratorAgent(llm_client=HeuristicLLMClient()),
        evaluator_agent=EvaluatorAgent(llm_client=HeuristicLLMClient()),
    )
    result = pipeline.run(
        context="本次会议决定推进发布。王敏负责在5月1日前完成联调。",
        template_type="meeting",
        rules_config=rules,
        max_iters=3,
        target_score=85,
    )
    assert len(result.round_logs) == 1
    assert result.best_round == 1


def test_pipeline_runs_to_max_iterations_if_target_not_reached():
    rules = RulesConfig(
        version="1.0",
        base_score=100,
        rules=[
            Rule(
                id="rule_force_low",
                name="低分",
                applies_to="all",
                max_deduction=20,
                judge_prompt="force_over_max",
                deduction_guide="0-20",
            )
        ],
    )
    pipeline = SummarizationPipeline(
        template_agent=TemplateGeneratorAgent(llm_client=HeuristicLLMClient()),
        summary_agent=SummaryGeneratorAgent(llm_client=HeuristicLLMClient()),
        evaluator_agent=EvaluatorAgent(llm_client=HeuristicLLMClient()),
    )
    result = pipeline.run(
        context="普通文本",
        template_type="meeting",
        rules_config=rules,
        max_iters=3,
        target_score=95,
    )
    assert len(result.round_logs) == 3
    assert "max iterations" in result.stopped_reason


class RecordingTemplateAgent:
    def __init__(self):
        self.feedback_history: list[str | None] = []

    def generate(self, context, template_type, eval_feedback=None, prev_template=None):
        del context, prev_template
        self.feedback_history.append(eval_feedback)
        return TemplateDraft(template_type=template_type, content="# T\n## A\n## B")


class FixedSummaryAgent:
    def generate(self, context, template_draft, context_images=None):
        del context, template_draft, context_images
        return SummaryDraft(content="# S\n## A\n- x")


class ScriptedEvaluatorAgent:
    def __init__(self):
        self.scores = [70, 90, 80]
        self.idx = 0

    def evaluate(self, context, summary_draft, rules, base_score=100, context_images=None, summary_images=None):
        del context, summary_draft, rules, base_score, context_images, summary_images
        score = self.scores[self.idx]
        self.idx += 1
        deductions = [
            DeductionItem(
                rule_id="r",
                rule_name="rule",
                deducted_points=100 - score,
                evidence="e",
                rationale="需要优化结构",
            )
        ]
        return EvaluationReport(
            base_score=100,
            total_score=score,
            deductions=deductions,
            evaluated_rule_ids=["r"],
            suggestions=["优化结构"],
            warnings=[],
        )


def test_pipeline_passes_feedback_and_selects_best_round():
    template_agent = RecordingTemplateAgent()
    pipeline = SummarizationPipeline(
        template_agent=template_agent,
        summary_agent=FixedSummaryAgent(),
        evaluator_agent=ScriptedEvaluatorAgent(),
    )
    rules = RulesConfig(
        version="1.0",
        base_score=100,
        rules=[
            Rule(
                id="r",
                name="rule",
                applies_to="all",
                max_deduction=30,
                judge_prompt="结构",
                deduction_guide="0-30",
            )
        ],
    )
    result = pipeline.run(
        context="x",
        template_type="meeting",
        rules_config=rules,
        max_iters=3,
        target_score=95,
    )
    assert result.best_round == 2
    assert result.best_score == 90
    assert template_agent.feedback_history[0] in ("", None)
    assert template_agent.feedback_history[1]


def test_truncate_context_keeps_head_and_tail():
    context = "A" * 100 + "B" * 100

    truncated = truncate_context(context=context, max_chars=80)

    assert len(truncated) <= 80
    assert truncated.startswith("A")
    assert truncated.endswith("B")
    assert "input truncated" in truncated
