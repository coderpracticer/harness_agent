from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

TemplateType = str
RuleAppliesTo = str


class Rule(BaseModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    applies_to: RuleAppliesTo
    max_deduction: int = Field(ge=0)
    judge_prompt: str = Field(min_length=1)
    deduction_guide: str = Field(min_length=1)


class RulesConfig(BaseModel):
    version: str = Field(min_length=1)
    base_score: int = Field(default=100, ge=0)
    rules: list[Rule] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rule_ids(self) -> "RulesConfig":
        ids = [rule.id for rule in self.rules]
        if len(ids) != len(set(ids)):
            raise ValueError("Rule IDs must be unique.")
        return self


class TemplateDraft(BaseModel):
    template_type: TemplateType
    content: str = Field(min_length=1)
    notes: list[str] = Field(default_factory=list)


class SummaryDraft(BaseModel):
    content: str = Field(min_length=1)


class DeductionItem(BaseModel):
    rule_id: str
    rule_name: str
    deducted_points: int = Field(ge=0)
    evidence: str
    rationale: str


class EvaluationReport(BaseModel):
    base_score: int = Field(ge=0)
    total_score: int = Field(ge=0)
    deductions: list[DeductionItem] = Field(default_factory=list)
    evaluated_rule_ids: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @property
    def total_deduction(self) -> int:
        return sum(item.deducted_points for item in self.deductions)

    @property
    def triggered_rule_ids(self) -> list[str]:
        return [item.rule_id for item in self.deductions if item.deducted_points > 0]


class RoundLog(BaseModel):
    round_index: int = Field(ge=1)
    input_feedback: str = ""
    template_draft: TemplateDraft
    summary_draft: SummaryDraft
    evaluation: EvaluationReport


class PipelineResult(BaseModel):
    template_type: TemplateType
    best_round: int = Field(ge=1)
    best_score: int = Field(ge=0)
    stopped_reason: str
    final_template: str
    final_summary: str
    round_logs: list[RoundLog] = Field(default_factory=list)
