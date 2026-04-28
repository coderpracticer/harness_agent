from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook


@dataclass(frozen=True)
class OptimizationRecord:
    scene_raw: str
    scene_key: str
    title: str
    content: str
    row_index: int


def read_optimization_records(path: str | Path) -> list[OptimizationRecord]:
    xlsx_path = Path(path)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Optimization data file not found: {xlsx_path}")
    if xlsx_path.suffix.lower() != ".xlsx":
        raise ValueError(f"Only .xlsx optimization data is supported: {xlsx_path}")

    workbook = load_workbook(xlsx_path, read_only=True, data_only=True)
    sheet = workbook.active
    records: list[OptimizationRecord] = []

    for row_index, row in enumerate(sheet.iter_rows(min_row=1, values_only=True), start=1):
        scene_raw = _cell_text(row[0] if len(row) > 0 else "")
        title = _cell_text(row[1] if len(row) > 1 else "")
        content = _cell_text(row[2] if len(row) > 2 else "")
        if row_index == 1 and _looks_like_header(scene_raw, title, content):
            continue
        if not scene_raw and not title and not content:
            continue
        if not scene_raw:
            scene_raw = "unknown"
        records.append(
            OptimizationRecord(
                scene_raw=scene_raw,
                scene_key=normalize_scene_key(scene_raw),
                title=title,
                content=content,
                row_index=row_index,
            )
        )

    workbook.close()
    return records


def group_records_by_scene(records: list[OptimizationRecord]) -> dict[str, list[OptimizationRecord]]:
    grouped: dict[str, list[OptimizationRecord]] = {}
    for record in records:
        grouped.setdefault(record.scene_key, []).append(record)
    return grouped


def build_scene_context(scene_key: str, records: list[OptimizationRecord]) -> str:
    lines = [f"# Scene: {scene_key}", f"Sample count: {len(records)}", ""]
    for idx, record in enumerate(records, start=1):
        lines.append(f"## Sample {idx}")
        lines.append(f"Raw scene: {record.scene_raw}")
        lines.append(f"Title: {record.title or '(empty title)'}")
        lines.append("Content:")
        lines.append(record.content or "(empty content)")
        lines.append("")
    return "\n".join(lines).strip()


def normalize_scene_key(scene_raw: str) -> str:
    text = scene_raw.strip()
    text = re.sub(r"[\s_-]*[0-9０-９]+$", "", text)
    text = re.sub(r"[\s_-]+$", "", text)
    return text or scene_raw.strip() or "unknown"


def _cell_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _looks_like_header(scene: str, title: str, content: str) -> bool:
    scene_l = scene.lower().strip()
    title_l = title.lower().strip()
    content_l = content.lower().strip()
    scene_tokens = {"scene", "type", "scene type", "场景", "类型", "场景类型"}
    title_tokens = {"title", "标题"}
    content_tokens = {"content", "内容", "正文"}
    return (
        scene_l in scene_tokens
        and title_l in title_tokens
        and content_l in content_tokens
    )
