from __future__ import annotations

from harness.agents import EvaluatorAgent, SummaryGeneratorAgent, TemplateGeneratorAgent
from harness.rules import select_rules_for_type
from harness.schemas import PipelineResult, RoundLog, RulesConfig, TemplateType


class SummarizationPipeline:
    def __init__(
        self,
        template_agent: TemplateGeneratorAgent,
        summary_agent: SummaryGeneratorAgent,
        evaluator_agent: EvaluatorAgent,
    ):
        self._template_agent = template_agent
        self._summary_agent = summary_agent
        self._evaluator_agent = evaluator_agent

    def run(
        self,
        *,
        context: str,
        template_type: TemplateType,
        rules_config: RulesConfig,
        initial_template: str | None = None,
        max_iters: int = 3,
        target_score: int = 85,
    ) -> PipelineResult:
        if max_iters <= 0:
            raise ValueError("max_iters must be > 0")

        selected_rules = select_rules_for_type(rules_config, template_type=template_type)
        if not selected_rules:
            raise ValueError(f"No rules apply to template_type={template_type}")

        round_logs: list[RoundLog] = []
        best_round_log: RoundLog | None = None
        stopped_reason = f"Reached max iterations ({max_iters})."

        eval_feedback = ""
        prev_template: str | None = initial_template

        for round_index in range(1, max_iters + 1):
            if round_index == 1 and initial_template:
                template_draft = self._template_agent.generate(
                    context=context,
                    template_type=template_type,
                    eval_feedback=None,
                    prev_template=initial_template,
                )
            else:
                template_draft = self._template_agent.generate(
                    context=context,
                    template_type=template_type,
                    eval_feedback=eval_feedback or None,
                    prev_template=prev_template,
                )
            summary_draft = self._summary_agent.generate(context=context, template_draft=template_draft)
            evaluation = self._evaluator_agent.evaluate(
                context=context,
                summary_draft=summary_draft,
                rules=selected_rules,
                base_score=rules_config.base_score,
            )
            round_log = RoundLog(
                round_index=round_index,
                input_feedback=eval_feedback,
                template_draft=template_draft,
                summary_draft=summary_draft,
                evaluation=evaluation,
            )
            round_logs.append(round_log)

            if best_round_log is None or round_log.evaluation.total_score > best_round_log.evaluation.total_score:
                best_round_log = round_log

            if evaluation.total_score >= target_score:
                stopped_reason = f"Reached target score ({target_score}) at round {round_index}."
                break

            eval_feedback = _build_eval_feedback(round_log=round_log)
            prev_template = template_draft.content

        if best_round_log is None:
            raise RuntimeError("Pipeline produced no rounds.")

        return PipelineResult(
            template_type=template_type,
            best_round=best_round_log.round_index,
            best_score=best_round_log.evaluation.total_score,
            stopped_reason=stopped_reason,
            final_template=best_round_log.template_draft.content,
            final_summary=best_round_log.summary_draft.content,
            round_logs=round_logs,
        )


def _build_eval_feedback(round_log: RoundLog) -> str:
    if not round_log.evaluation.deductions:
        return "No deductions in this round; keep the current structure and coverage."
    lines = ["Improve the template according to these deductions:"]
    for item in round_log.evaluation.deductions:
        lines.append(f"- Rule {item.rule_id} deducted {item.deducted_points}: {item.rationale}")
    return "\n".join(lines)
