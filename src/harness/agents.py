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
        base_templates = {
            "meeting": "\n".join(
                [
                    "# 会议摘要模板",
                    "## 会议主题",
                    "## 关键结论",
                    "## 决策事项",
                    "## 行动项",
                    "| 事项 | 负责人 | 截止日期 |",
                    "|---|---|---|",
                    "## 风险与待确认",
                ]
            ),
            "interview": "\n".join(
                [
                    "# 访谈摘要模板",
                    "## 访谈背景",
                    "## 核心观点",
                    "## 问答要点",
                    "## 受访者关切与动机",
                    "## 后续跟进建议",
                ]
            ),
        }
        template = (prev_template or "").strip() or base_templates[template_type]
        template = self._ensure_sections(template=template, template_type=template_type)
        if eval_feedback and eval_feedback.strip():
            feedback_lines = [line.strip("- ").strip() for line in eval_feedback.splitlines() if line.strip()]
            feedback_lines = [line for line in feedback_lines if line]
            if feedback_lines:
                template += "\n\n## 优化提醒\n"
                for line in feedback_lines[:4]:
                    template += f"- {line}\n"
        return template.strip()

    def _generate_with_llm(
        self,
        template_type: TemplateType,
        eval_feedback: str | None,
        prev_template: str | None,
    ) -> str:
        system_prompt = "你是摘要模板生成智能体。输出 Markdown 模板。"
        user_prompt = (
            "请基于以下信息生成摘要模板，只输出模板本体。\n"
            f"模板类型: {template_type}\n"
            f"上一版模板:\n{prev_template or '(none)'}\n"
            f"评测反馈:\n{eval_feedback or '(none)'}\n"
            "要求: 结构清晰，便于后续摘要填写。"
        )
        content = self._llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        return self._ensure_sections(template=content, template_type=template_type)

    def _ensure_sections(self, template: str, template_type: TemplateType) -> str:
        required = {
            "meeting": ["会议主题", "关键结论", "决策事项", "行动项", "风险与待确认"],
            "interview": ["访谈背景", "核心观点", "问答要点", "受访者关切与动机", "后续跟进建议"],
        }
        lines = template.splitlines()
        for section in required[template_type]:
            if f"## {section}" not in template:
                lines.append(f"## {section}")
        return "\n".join(lines)


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
        system_prompt = "你是摘要生成智能体。请严格遵循模板生成摘要，输出 Markdown。"
        user_prompt = (
            f"模板类型: {template_draft.template_type}\n\n"
            f"模板:\n{template_draft.content}\n\n"
            f"原文:\n{context}\n\n"
            "要求: 保持事实一致，信息完整，结构清晰。"
        )
        return self._llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)

    def _generate_heuristic(self, context: str, template_draft: TemplateDraft) -> str:
        headings = [line.strip()[3:].strip() for line in template_draft.content.splitlines() if line.strip().startswith("## ")]
        if not headings:
            headings = ["摘要"]

        output_lines: list[str] = ["# 摘要"]
        for heading in headings:
            output_lines.append(f"## {heading}")
            output_lines.append(self._build_section_content(heading=heading, context=context))
            output_lines.append("")
        return "\n".join(output_lines).strip()

    def _build_section_content(self, heading: str, context: str) -> str:
        heading_l = heading.lower()
        sentences = _split_sentences(context)
        if not sentences:
            return "- 原文为空，无法生成摘要。"

        if any(k in heading_l for k in ["主题", "背景"]):
            return f"- {sentences[0]}"

        if any(k in heading_l for k in ["关键结论", "核心观点", "决策"]):
            selected = _pick_sentences(sentences, ["决定", "结论", "达成", "建议", "目标", "方案"], fallback_count=2)
            return "\n".join(f"- {line}" for line in selected)

        if "行动" in heading_l:
            rows = _extract_action_rows(sentences)
            if not rows:
                return "- 暂未识别明确行动项，建议补充负责人与时间节点。"
            lines = ["| 事项 | 负责人 | 截止日期 |", "|---|---|---|"]
            for item, owner, deadline in rows:
                lines.append(f"| {item} | {owner} | {deadline} |")
            return "\n".join(lines)

        if any(k in heading_l for k in ["风险", "待确认", "关切"]):
            selected = _pick_sentences(sentences, ["风险", "问题", "阻塞", "担忧", "待确认"], fallback_count=2)
            return "\n".join(f"- {line}" for line in selected)

        if "问答" in heading_l:
            qa_lines = _extract_qa_pairs(context)
            if qa_lines:
                return "\n".join(qa_lines)
            fallback = _pick_sentences(sentences, ["为什么", "如何", "是否"], fallback_count=2)
            return "\n".join([f"Q: {fallback[0]}", f"A: {fallback[-1]}"])

        if "后续跟进" in heading_l:
            selected = _pick_sentences(sentences, ["下一步", "计划", "跟进", "安排"], fallback_count=2)
            return "\n".join(f"- {line}" for line in selected)

        return "\n".join(f"- {line}" for line in sentences[:2])


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
            raw_points, evidence, rationale = self._evaluate_single_rule(rule=rule, context=context, summary=summary_draft.content)
            deducted_points, warning = _clamp_deduction(raw_points=raw_points, max_deduction=rule.max_deduction, rule_id=rule.id)
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
                suggestions.append(f"针对“{rule.name}”优化：{_to_suggestion_text(rationale)}")

        total_deduction = sum(item.deducted_points for item in deductions)
        total_score = max(0, base_score - total_deduction)
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
                raw, evidence, rationale = self._evaluate_single_rule_heuristic(rule=rule, context=context, summary=summary)
                return raw, f"{evidence}; fallback={exc}", rationale
        return self._evaluate_single_rule_heuristic(rule=rule, context=context, summary=summary)

    def _evaluate_single_rule_with_llm(self, rule: Rule, context: str, summary: str) -> tuple[int, str, str]:
        system_prompt = "你是摘要评测智能体。只输出 JSON。"
        user_prompt = (
            f"规则ID: {rule.id}\n"
            f"规则名称: {rule.name}\n"
            f"适用范围: {rule.applies_to}\n"
            f"最大扣分: {rule.max_deduction}\n"
            f"规则提示词: {rule.judge_prompt}\n"
            f"扣分说明: {rule.deduction_guide}\n\n"
            f"原文:\n{context}\n\n"
            f"摘要:\n{summary}\n\n"
            "请给出 JSON: "
            '{"raw_deduction": <int>, "evidence": "<str>", "rationale": "<str>"}'
        )
        response = self._llm.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        payload = _extract_json_object(response)
        raw = int(payload["raw_deduction"])
        evidence = str(payload["evidence"])
        rationale = str(payload["rationale"])
        return raw, evidence, rationale

    def _evaluate_single_rule_heuristic(self, rule: Rule, context: str, summary: str) -> tuple[int, str, str]:
        raw_points = 0
        reasons: list[str] = []
        evidences: list[str] = []

        summary_len = len(summary.strip())
        section_count = len(re.findall(r"^##\s+", summary, flags=re.MULTILINE))
        rule_text = f"{rule.name} {rule.judge_prompt} {rule.deduction_guide}".lower()

        if "force_over_max" in rule_text:
            raw_points = rule.max_deduction + 7
            reasons.append("测试用：强制触发超上限扣分。")
            evidences.append("judge_prompt 含 force_over_max。")

        if any(k in rule_text for k in ["结构", "模板", "标题", "层级"]):
            if section_count < 3:
                raw_points += max(1, int(rule.max_deduction * 0.7))
                reasons.append("摘要结构不完整，标题层级不足。")
                evidences.append(f"检测到 {section_count} 个二级标题。")
            elif section_count < 4:
                raw_points += max(1, int(rule.max_deduction * 0.3))
                reasons.append("摘要结构完整度一般。")
                evidences.append(f"检测到 {section_count} 个二级标题。")

        if any(k in rule_text for k in ["完整", "覆盖", "核心", "要点"]):
            if summary_len < 180:
                raw_points += max(1, int(rule.max_deduction * 0.6))
                reasons.append("摘要内容偏短，可能存在关键信息遗漏。")
                evidences.append(f"摘要长度={summary_len}。")

        if any(k in rule_text for k in ["行动", "负责人", "截止", "执行"]):
            has_owner = "负责人" in summary
            has_deadline = any(key in summary for key in ["截止", "日期", "月", "下周", "本周"])
            has_table = "|" in summary
            if not (has_owner and has_deadline and has_table):
                raw_points += max(1, int(rule.max_deduction * 0.7))
                reasons.append("行动项缺少负责人/时间节点/结构化呈现。")
                evidences.append(
                    f"负责人={has_owner}, 时间节点={has_deadline}, 表格={has_table}。"
                )

        if any(k in rule_text for k in ["问答", "qa", "q:", "a:", "采访"]):
            has_qa = any(k in summary for k in ["Q:", "A:", "问：", "答："])
            if not has_qa:
                raw_points += max(1, int(rule.max_deduction * 0.7))
                reasons.append("问答关系不明显。")
                evidences.append("未检测到 Q/A 标识。")

        if any(k in rule_text for k in ["事实", "准确", "一致", "幻觉"]):
            overlap = _lexical_overlap_ratio(context=context, summary=summary)
            if overlap < 0.18:
                raw_points += max(1, int(rule.max_deduction * 0.7))
                reasons.append("与原文词汇重合度低，存在事实偏移风险。")
                evidences.append(f"词汇重合度={overlap:.2f}。")
            elif overlap < 0.30:
                raw_points += max(1, int(rule.max_deduction * 0.35))
                reasons.append("与原文一致性一般。")
                evidences.append(f"词汇重合度={overlap:.2f}。")

        if any(k in rule_text for k in ["简洁", "冗长"]):
            if summary_len > 1500:
                raw_points += max(1, int(rule.max_deduction * 0.4))
                reasons.append("摘要偏冗长。")
                evidences.append(f"摘要长度={summary_len}。")

        if raw_points <= 0:
            return 0, "启发式检查未发现明显问题。", "该规则通过。"
        return raw_points, "; ".join(evidences), "；".join(reasons)


def _split_sentences(text: str) -> list[str]:
    chunks = re.split(r"[。！？!?\n\r]+", text)
    return [chunk.strip(" -\t") for chunk in chunks if chunk.strip()]


def _pick_sentences(sentences: list[str], keywords: list[str], fallback_count: int = 2) -> list[str]:
    hits: list[str] = []
    for sentence in sentences:
        if any(keyword in sentence for keyword in keywords):
            hits.append(sentence)
        if len(hits) >= max(1, fallback_count):
            break
    if hits:
        return hits
    return sentences[: max(1, fallback_count)]


def _extract_action_rows(sentences: list[str]) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for sentence in sentences:
        if not any(keyword in sentence for keyword in ["负责", "完成", "截止", "下周", "本周", "计划"]):
            continue
        owner_match = re.search(r"([A-Za-z\u4e00-\u9fa5]{1,12})(?:负责|牵头|跟进)", sentence)
        owner = owner_match.group(1) if owner_match else "待定"
        deadline_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}月\d{1,2}日|本周|下周|月底|下月底)", sentence)
        deadline = deadline_match.group(1) if deadline_match else "待定"
        item = sentence
        rows.append((item[:40], owner, deadline))
        if len(rows) >= 3:
            break
    return rows


def _extract_qa_pairs(context: str) -> list[str]:
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    qa_lines: list[str] = []
    for line in lines:
        if line.startswith(("Q:", "A:", "问：", "答：")):
            qa_lines.append(line)
    return qa_lines[:6]


def _tokenize(text: str) -> set[str]:
    words = re.findall(r"[\u4e00-\u9fa5]{2,}|[A-Za-z]{2,}", text.lower())
    return {w for w in words if len(w) >= 2}


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


def _to_suggestion_text(rationale: str) -> str:
    if "结构" in rationale:
        return "补齐模板关键章节并保持标题层级一致。"
    if "行动项" in rationale:
        return "增加行动项表格，明确负责人与截止时间。"
    if "问答" in rationale:
        return "补充问答对，确保问题与回答成对出现。"
    if "事实" in rationale or "一致" in rationale:
        return "减少外推内容，优先保留原文可核验事实。"
    if "遗漏" in rationale:
        return "补充核心信息覆盖范围，尤其是结论与决策。"
    return rationale
