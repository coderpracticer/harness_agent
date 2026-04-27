from __future__ import annotations

from pathlib import Path

from harness.schemas import TemplateType


def resolve_initial_template(
    *,
    templates_dir: str | Path,
    template_name: str,
    template_type: TemplateType,
) -> Path:
    initial_dir = Path(templates_dir) / "initial"
    candidates = [
        initial_dir / template_name,
        initial_dir / f"{template_name}.md",
        initial_dir / template_type / template_name,
        initial_dir / template_type / f"{template_name}.md",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    raise FileNotFoundError(
        f"Initial template '{template_name}' not found under {initial_dir}. "
        "Use a file name such as meeting_default.md or a path under initial/<template_type>/."
    )


def read_initial_template(
    *,
    templates_dir: str | Path,
    template_name: str,
    template_type: TemplateType,
) -> tuple[Path, str]:
    path = resolve_initial_template(
        templates_dir=templates_dir,
        template_name=template_name,
        template_type=template_type,
    )
    return path, path.read_text(encoding="utf-8")


def persist_generated_templates(
    *,
    templates_dir: str | Path,
    run_id: str,
    document_stem: str,
    round_templates: list[tuple[int, str]],
    final_template: str,
) -> Path:
    base = Path(templates_dir) / "generated" / run_id / document_stem
    base.mkdir(parents=True, exist_ok=True)
    for round_index, content in round_templates:
        (base / f"round_{round_index}.md").write_text(content, encoding="utf-8")
    (base / "final.md").write_text(final_template, encoding="utf-8")
    return base
