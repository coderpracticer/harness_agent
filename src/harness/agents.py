from __future__ import annotations

import json
import re
from typing import Sequence

from harness.llm_client import LLMClient
from harness.schemas import DeductionItem, EvaluationReport, Rule, SummaryDraft, TemplateDraft, TemplateType


class TemplateGeneratorAgent:
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def generate(
        self,
        context: str,
        template_type: TemplateType,
        eval_feedback: str | None = None,
        prev_template: str | None = None,
    ) -> TemplateDraft:
        del context
        if self._llm.backend_name == "openai":
            content = self._generate_with_llm(
                template_type=template_type,
                eval_feedback=eval_feedback,
                prev_template=prev_template,
            )
        else:
            content = self._generate_heuristic(
                template_type=template_type,
                eval_feedback=eval_feedback,
                prev_template=prev_template,
            )
        return TemplateDraft(template_type=template_type, content=content, notes=[eval_feedback or ""])

    def _generate_heuristic(
        self,
        template_type: TemplateType,
        eval_feedback: str | None,
        prev_template: str | None,
    ) -> str:
        template = (prev_template or "").strip() or _default_template(template_type)
        template = _ensure_sections(template=template, template_type=template_type)
        if eval_feedback and eval_feedback.strip():
            template += "\n\n## Optimization Notes\n"
            for line in _compact_lines(eval_feedback)[:5]:
                template += f"- {line}\n"
        return template.strip()

    def _generate_with_llm(
        self,
        template_type: TemplateType,
        eval_feedback: str | None,
        prev_template: str | None,
    ) -> str:
        system_prompt = "You are a summary template optimization agent. Output Markdown only."
        user_prompt = (
            "Create or improve a summary template.\n"
            f"Template type: {template_type}\n\n"
            f"Previous template:\n{prev_template or '(none)'}\n\n"
            f"Evaluation feedback:\n{eval_feedback or '(none)'}\n\n"
            "Keep the template clear, reusable, and easy for a summary agent to follow."
        )
        content = self._llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        return _ensure_sections(template=content, template_type=template_type)


class SummaryGeneratorAgent:
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def generate(self, context: str, template_draft: TemplateDraft) -> SummaryDraft:
        if self._llm.backend_name == "openai":
            content = self._generate_with_llm(context=context, template_draft=template_draft)
        else:
            content = self._generate_heuristic(context=context, template_draft=template_draft)
        return SummaryDraft(content=content)

    def _generate_with_llm(self, context: str, template_draft: TemplateDraft) -> str:
        system_prompt = "You are a summary generation agent. Follow the template and output Markdown."
        user_prompt = (
            f"Template type: {template_draft.template_type}\n\n"
            f"Template:\n{template_draft.content}\n\n"
            f"Source document:\n{context}\n\n"
            "Requirements: preserve facts, cover important information, and keep the structure clear."
        )
        return self._llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)

    def _generate_heuristic(self, context: str, template_draft: TemplateDraft) -> str:
        headings = [line.strip()[3:].strip() for line in template_draft.content.splitlines() if line.strip().startswith("## ")]
        if not headings:
            headings = ["Summary"]

        output_lines: list[str] = ["# Summary"]
        for heading in headings:
            output_lines.append(f"## {heading}")
            output_lines.append(_build_section_content(heading=heading, context=context))
            output_lines.append("")
        return "\n".join(output_lines).strip()


class EvaluatorAgent:
    def __init__(self, llm_client: LLMClient):
        self._llm = llm_client

    def evaluate(
        self,
        context: str,
        summary_draft: SummaryDraft,
        rules: Sequence[Rule],
        base_score: int = 100,
    ) -> EvaluationReport:
        deductions: list[DeductionItem] = []
        warnings: list[str] = []
        suggestions: list[str] = []
        evaluated_rule_ids: list[str] = []

        for rule in rules:
            evaluated_rule_ids.append(rule.id)
            raw_points, evidence, rationale = self._evaluate_single_rule(
                rule=rule,
                context=context,
                summary=summary_draft.content,
            )
            deducted_points, warning = _clamp_deduction(
                raw_points=raw_points,
                max_deduction=rule.max_deduction,
                rule_id=rule.id,
            )
            if warning:
                warnings.append(warning)
            if deducted_points > 0:
                deductions.append(
                    DeductionItem(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        deducted_points=deducted_points,
                        evidence=evidence,
                        rationale=rationale,
                    )
                )
                suggestions.append(f"Improve '{rule.name}': {_to_suggestion_text(rule.id, rationale)}")

        total_score = max(0, base_score - sum(item.deducted_points for item in deductions))
        return EvaluationReport(
            base_score=base_score,
            total_score=total_score,
            deductions=deductions,
            evaluated_rule_ids=evaluated_rule_ids,
            suggestions=suggestions,
            warnings=warnings,
        )

    def _evaluate_single_rule(self, rule: Rule, context: str, summary: str) -> tuple[int, str, str]:
        if self._llm.backend_name == "openai":
            try:
                return self._evaluate_single_rule_with_llm(rule=rule, context=context, summary=summary)
            except Exception as exc:
                raw, evidence, rationale = self._evaluate_single_rule_heuristic(
                    rule=rule,
                    context=context,
                    summary=summary,
                )
                return raw, f"{evidence}; fallback={exc}", rationale
        return self._evaluate_single_rule_heuristic(rule=rule, context=context, summary=summary)

    def _evaluate_single_rule_with_llm(self, rule: Rule, context: str, summary: str) -> tuple[int, str, str]:
        system_prompt = "You are a summary evaluation agent. Output JSON only."
        user_prompt = (
            f"Rule ID: {rule.id}\n"
            f"Rule name: {rule.name}\n"
            f"Max deduction: {rule.max_deduction}\n"
            f"Judge prompt: {rule.judge_prompt}\n"
            f"Deduction guide: {rule.deduction_guide}\n\n"
            f"Source document:\n{context}\n\n"
            f"Summary:\n{summary}\n\n"
            'Return JSON: {"raw_deduction": <int>, "evidence": "<str>", "rationale": "<str>"}'
        )
        response = self._llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        payload = _extract_json_object(response)
        return int(payload["raw_deduction"]), str(payload["evidence"]), str(payload["rationale"])

    def _evaluate_single_rule_heuristic(self, rule: Rule, context: str, summary: str) -> tuple[int, str, str]:
        rule_text = f"{rule.id} {rule.name} {rule.judge_prompt} {rule.deduction_guide}".lower()
        summary_len = len(summary.strip())
        section_count = len(re.findall(r"^##\s+", summary, flags=re.MULTILINE))
        raw_points = 0
        reasons: list[str] = []
        evidence: list[str] = []

        if "force_over_max" in rule_text:
            raw_points = rule.max_deduction + 7
            reasons.append("Test hook requested an over-limit deduction.")
            evidence.append("judge_prompt contains force_over_max.")

        if _matches(rule_text, ["structure", "template", "heading", "alignment", "structure_template_alignment"]):
            if section_count < 3:
                raw_points += max(1, int(rule.max_deduction * 0.7))
                reasons.append("Summary has too few sections.")
                evidence.append(f"section_count={section_count}.")

        if _matches(rule_text, ["completeness", "complete", "coverage", "core", "completeness_core_points"]):
            if summary_len < 180:
                raw_points += max(1, int(rule.max_deduction * 0.6))
                reasons.append("Summary is short and may miss important content.")
                evidence.append(f"summary_length={summary_len}.")

        if _matches(rule_text, ["action", "owner", "deadline", "meeting_action_items"]):
            has_table = "|" in summary
            has_action_signal = _contains_any(summary, ["owner", "deadline", "responsible", "action", "负责人", "截止"])
            if not (has_table and has_action_signal):
                raw_points += max(1, int(rule.max_deduction * 0.7))
                reasons.append("Action items are not structured with owner/deadline signals.")
                evidence.append(f"has_table={has_table}, has_action_signal={has_action_signal}.")

        if _matches(rule_text, ["qa", "q:", "a:", "interview_qa_signal"]):
            has_qa = _contains_any(summary, ["Q:", "A:", "问：", "答："])
            if not has_qa:
                raw_points += max(1, int(rule.max_deduction * 0.7))
                reasons.append("Question-answer relationship is not explicit.")
                evidence.append("No Q/A marker found.")

        if _matches(rule_text, ["fact", "accuracy", "consistent", "hallucination", "factual_consistency"]):
            overlap = _lexical_overlap_ratio(context=context, summary=summary)
            if overlap < 0.18:
                raw_points += max(1, int(rule.max_deduction * 0.7))
                reasons.append("Low lexical overlap indicates possible factual drift.")
                evidence.append(f"overlap={overlap:.2f}.")
            elif overlap < 0.30:
                raw_points += max(1, int(rule.max_deduction * 0.35))
                reasons.append("Moderate lexical overlap; fact consistency should be checked.")
                evidence.append(f"overlap={overlap:.2f}.")

        if raw_points <= 0:
            return 0, "No obvious issue found by heuristic checks.", "Rule passed."
        return raw_points, " ".join(evidence), " ".join(reasons)


def _default_template(template_type: TemplateType) -> str:
    defaults = {
        "meeting": "\n".join(
            [
                "# Meeting Summary Template",
                "## Meeting Topic",
                "## Key Conclusions",
                "## Decisions",
                "## Action Items",
                "| Item | Owner | Deadline |",
                "|---|---|---|",
                "## Risks and Open Questions",
            ]
        ),
        "interview": "\n".join(
            [
                "# Interview Summary Template",
                "## Interview Background",
                "## Core Viewpoints",
                "## Q&A Highlights",
                "## Interviewee Concerns",
                "## Follow-up Suggestions",
            ]
        ),
    }
    return defaults[template_type]


def _ensure_sections(template: str, template_type: TemplateType) -> str:
    required = {
        "meeting": ["Meeting Topic", "Key Conclusions", "Decisions", "Action Items", "Risks and Open Questions"],
        "interview": ["Interview Background", "Core Viewpoints", "Q&A Highlights", "Interviewee Concerns", "Follow-up Suggestions"],
    }
    lines = template.splitlines()
    for section in required[template_type]:
        if f"## {section}" not in template:
            lines.append(f"## {section}")
    return "\n".join(lines)


def _build_section_content(heading: str, context: str) -> str:
    heading_l = heading.lower()
    sentences = _split_sentences(context)
    if not sentences:
        return "- Source document is empty."

    if _contains_any(heading_l, ["topic", "background"]):
        return f"- {sentences[0]}"
    if _contains_any(heading_l, ["conclusion", "viewpoint", "decision"]):
        return "\n".join(f"- {line}" for line in _pick_sentences(sentences, ["决定", "结论", "建议", "目标", "plan", "decision"]))
    if "action" in heading_l:
        rows = _extract_action_rows(sentences)
        if not rows:
            return "- No explicit action item detected."
        lines = ["| Item | Owner | Deadline |", "|---|---|---|"]
        for item, owner, deadline in rows:
            lines.append(f"| {item} | {owner} | {deadline} |")
        return "\n".join(lines)
    if _contains_any(heading_l, ["risk", "question", "concern"]):
        return "\n".join(f"- {line}" for line in _pick_sentences(sentences, ["风险", "问题", "担忧", "risk", "issue"]))
    if _contains_any(heading_l, ["q&a", "qa"]):
        qa_lines = _extract_qa_pairs(context)
        if qa_lines:
            return "\n".join(qa_lines)
        picked = _pick_sentences(sentences, ["为什么", "如何", "是否", "why", "how"])
        return "\n".join([f"Q: {picked[0]}", f"A: {picked[-1]}"])
    return "\n".join(f"- {line}" for line in sentences[:2])


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"[。！？!?\n\r]+", text)
    return [chunk.strip(" -\t") for chunk in chunks if chunk.strip()]


def _pick_sentences(sentences: list[str], keywords: list[str], fallback_count: int = 2) -> list[str]:
    hits = [sentence for sentence in sentences if _contains_any(sentence, keywords)]
    return (hits or sentences)[: max(1, fallback_count)]


def _extract_action_rows(sentences: list[str]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for sentence in sentences:
        if not _contains_any(sentence, ["负责", "完成", "截止", "下周", "本周", "owner", "deadline"]):
            continue
        owner_match = re.search(r"([A-Za-z\u4e00-\u9fa5]{1,12})(?:负责|牵头|跟进|owns|owner)", sentence)
        deadline_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}月\d{1,2}日|本周|下周|月底|deadline)", sentence)
        rows.append((sentence[:60], owner_match.group(1) if owner_match else "TBD", deadline_match.group(1) if deadline_match else "TBD"))
        if len(rows) >= 3:
            break
    return rows


def _extract_qa_pairs(context: str) -> list[str]:
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    return [line for line in lines if line.startswith(("Q:", "A:", "问：", "答："))][:8]


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z]{2,}", text.lower())
    return {word for word in words if len(word) >= 2}


def _lexical_overlap_ratio(context: str, summary: str) -> float:
    context_tokens = _tokenize(context)
    summary_tokens = _tokenize(summary)
    if not summary_tokens:
        return 0.0
    if not context_tokens:
        return 1.0
    return len(context_tokens.intersection(summary_tokens)) / len(summary_tokens)


def _extract_json_object(text: str) -> dict[str, object]:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response.")
    return json.loads(text[start : end + 1])


def _clamp_deduction(raw_points: int, max_deduction: int, rule_id: str) -> tuple[int, str | None]:
    if raw_points < 0:
        return 0, f"Rule {rule_id} deduction {raw_points} below 0; clamped to 0."
    if raw_points > max_deduction:
        return max_deduction, f"Rule {rule_id} deduction {raw_points} exceeds max {max_deduction}; clamped."
    return raw_points, None


def _to_suggestion_text(rule_id: str, rationale: str) -> str:
    if "structure" in rule_id:
        return "Add missing template sections and keep headings consistent."
    if "action" in rule_id:
        return "Use an action-item table with owner and deadline columns."
    if "qa" in rule_id:
        return "Represent questions and answers explicitly."
    if "fact" in rule_id:
        return "Reduce unsupported extrapolation and keep claims traceable to the source."
    if "complete" in rule_id:
        return "Cover key conclusions, facts, and decisions more fully."
    return rationale


def _compact_lines(text: str) -> list[str]:
    return [line.strip("- ").strip() for line in text.splitlines() if line.strip()]


def _matches(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _contains_any(text: str, keywords: list[str]) -> bool:
    text_l = text.lower()
    return any(keyword.lower() in text_l for keyword in keywords)
