import json
from pathlib import Path

from openpyxl import Workbook

from harness.cli import main
from harness.excel_reader import group_records_by_scene_and_sub_scene, read_optimization_records


def test_optimization_reader_uses_xlsx_a_c_u_v_columns(tmp_path: Path):
    xlsx_path = tmp_path / "150data.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(_wide_optimization_row("场景", "发言内容", "子场景", "领域"))
    sheet.append(_wide_optimization_row("发布会1", "Speech content", "产品介绍1", "科技"))
    workbook.save(xlsx_path)

    records = read_optimization_records(xlsx_path)

    assert len(records) == 1
    assert records[0].scene_key == "发布会"
    assert records[0].content == "Speech content"
    assert records[0].sub_scene_key == "产品介绍"
    assert records[0].domain == "科技"


def test_optimization_reader_supports_json_records_and_sub_scene_groups(tmp_path: Path):
    json_path = tmp_path / "150data.json"
    json_path.write_text(
        json.dumps(
            [
                {"场景": "发布会1", "发言内容": "A", "子场景": "产品介绍1", "领域": "科技"},
                {"场景": "发布会2", "发言内容": "B", "子场景": "问答1", "领域": "科技"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    records = read_optimization_records(json_path)
    grouped = group_records_by_scene_and_sub_scene(records)

    assert len(records) == 2
    assert sorted((key.scene_key, key.sub_scene_key) for key in grouped) == [("发布会", "产品介绍"), ("发布会", "问答")]


def test_optimize_command_outputs_templates_per_sub_scene_from_json(tmp_path: Path):
    file_processing = tmp_path / "file_processing"
    file_processing.mkdir()
    json_path = file_processing / "150data.json"
    json_path.write_text(
        json.dumps(
            [
                {"场景": "发布会1", "发言内容": "Product launch.", "子场景": "产品介绍1", "领域": "科技"},
                {"场景": "发布会2", "发言内容": "Media questions.", "子场景": "媒体问答1", "领域": "科技"},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    mapping_file = file_processing / "类型映射.yaml"
    mapping_file.write_text("keywords:\n  发布会: press_conference\n", encoding="utf-8")

    templates_dir = tmp_path / "templates"
    scene_dir = templates_dir / "鍦烘櫙" / "press_conference"
    scene_dir.mkdir(parents=True)
    (templates_dir / "母模板.md").write_text("# 母模板\n\n{requirement}\n\n{format}", encoding="utf-8")
    (scene_dir / "要求.md").write_text("发布会要求", encoding="utf-8")
    (scene_dir / "格式.md").write_text("## 发布内容", encoding="utf-8")
    output_dir = tmp_path / "outputs" / "opt"

    code = main(
        [
            "optimize",
            "--file-processing-dir",
            str(file_processing),
            "--optimization-data-file",
            str(json_path),
            "--templates-dir",
            str(templates_dir),
            "--initial-template",
            "母模板.md",
            "--type-mapping-file",
            str(mapping_file),
            "--rules-file",
            "rules/scoring_rules.yaml",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    assert (output_dir / "发布会" / "产品介绍" / "final" / "report.md").exists()
    assert (output_dir / "发布会" / "媒体问答" / "final" / "report.md").exists()
    assert len(list((templates_dir / "generated").glob("*/*/*/final.md"))) == 2


def _wide_optimization_row(scene: str, content: str, sub_scene: str, domain: str) -> list[str]:
    row = [""] * 22
    row[0] = scene
    row[2] = content
    row[20] = sub_scene
    row[21] = domain
    return row
