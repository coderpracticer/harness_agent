from __future__ import annotations

from pathlib import Path

import yaml

from harness.schemas import Rule, RulesConfig, TemplateType


def load_rules_config(rules_file: str | Path) -> RulesConfig:
    path = Path(rules_file)
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)
    if not isinstance(payload, dict):
        raise ValueError("Rules file must contain a YAML object.")

    try:
        config = RulesConfig.model_validate(payload)
    except Exception as exc:
        raise ValueError(f"Invalid rules config: {exc}") from exc
    return config


def select_rules_for_type(config: RulesConfig, template_type: TemplateType) -> list[Rule]:
    selected: list[Rule] = []
    for rule in config.rules:
        if rule.applies_to in ("all", template_type):
            selected.append(rule)
    return selected
