from pathlib import Path

import pytest

from harness.rules import load_rules_config, select_rules_for_type


def test_load_rules_config_success():
    config = load_rules_config(Path("rules/scoring_rules.yaml"))
    assert config.base_score == 100
    assert len(config.rules) >= 3


def test_load_rules_config_invalid_max_deduction(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        """
version: "1.0"
base_score: 100
rules:
  - id: x
    name: x
    applies_to: press_conference
    max_deduction: -1
    judge_prompt: "p"
    deduction_guide: "g"
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_rules_config(bad)


def test_load_rules_config_missing_field(tmp_path: Path):
    bad = tmp_path / "bad_missing.yaml"
    bad.write_text(
        """
version: "1.0"
base_score: 100
rules:
  - id: x
    name: x
    applies_to: all
    judge_prompt: "p"
    deduction_guide: "g"
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        load_rules_config(bad)


def test_select_rules_for_type_filters_correctly():
    config = load_rules_config("rules/scoring_rules.yaml")
    meeting_rules = select_rules_for_type(config, "meeting")
    interview_rules = select_rules_for_type(config, "interview")

    assert any(rule.id == "meeting_action_items" for rule in meeting_rules)
    assert not any(rule.id == "meeting_action_items" for rule in interview_rules)
    assert any(rule.id == "interview_qa_signal" for rule in interview_rules)
