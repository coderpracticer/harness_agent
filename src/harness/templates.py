from __future__ import annotations

from pathlib import Path

import yaml

from harness.schemas import TemplateType


def load_scene_mapping(mapping_file: str | Path | None) -> dict[str, str]:
    if not mapping_file:
        return {}
    path = Path(mapping_file)
    if not path.exists():
        raise FileNotFoundError(f"Scene mapping file not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        raise ValueError("Scene mapping file must contain a YAML object.")
    mappings = payload.get("files", payload)
    if not isinstance(mappings, dict):
        raise ValueError("Scene mapping 'files' must be a YAML object.")
    return {str(filename): str(scene) for filename, scene in mappings.items()}


def scene_for_file(*, file_name: str, file_stem: str, scene_mapping: dict[str, str], default_scene: str) -> str:
    return scene_mapping.get(file_name) or scene_mapping.get(file_stem) or default_scene


def render_scene_template(
    *,
    templates_dir: str | Path,
    base_template_name: str,
    scene_name: str,
) -> tuple[list[Path], str]:
    base_dir = Path(templates_dir)
    base_template_path = _resolve_template_path(
        base_dir=base_dir,
        candidates=[
            base_dir / base_template_name,
            base_dir / f"{base_template_name}.md",
            base_dir / "母模板.md",
        ],
    )
    scene_dir = base_dir / "场景" / scene_name
    requirement_path = _resolve_template_path(
        base_dir=base_dir,
        candidates=[
            scene_dir / "要求.md",
            scene_dir / "requirement.md",
            scene_dir / f"{scene_name}_requirement.md",
        ],
    )
    format_path = _resolve_template_path(
        base_dir=base_dir,
        candidates=[
            scene_dir / "格式.md",
            scene_dir / "format.md",
            scene_dir / f"{scene_name}_format.md",
        ],
    )
    base_template = base_template_path.read_text(encoding="utf-8")
    requirement = requirement_path.read_text(encoding="utf-8")
    output_format = format_path.read_text(encoding="utf-8")
    return [base_template_path, requirement_path, format_path], base_template.replace("{requirement}", requirement).replace(
        "{format}",
        output_format,
    )


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


def read_template_for_scene(
    *,
    templates_dir: str | Path,
    template_name: str,
    template_type: TemplateType,
    scene_name: str | None = None,
) -> tuple[list[Path], str]:
    if scene_name:
        return render_scene_template(
            templates_dir=templates_dir,
            base_template_name=template_name,
            scene_name=scene_name,
        )
    path, content = read_initial_template(
        templates_dir=templates_dir,
        template_name=template_name,
        template_type=template_type,
    )
    return [path], content


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


def _resolve_template_path(*, base_dir: Path, candidates: list[Path]) -> Path:
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    names = ", ".join(str(path.relative_to(base_dir)) if path.is_relative_to(base_dir) else str(path) for path in candidates)
    raise FileNotFoundError(f"Template component not found. Tried: {names}")
