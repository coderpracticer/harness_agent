from pathlib import Path

from docx import Document

from harness.cli import main
from harness.document_reader import read_document_content, read_document_text
from harness.templates import render_scene_template


def test_read_document_text_extracts_paragraphs_and_tables(tmp_path: Path):
    docx_path = tmp_path / "sample.docx"
    document = Document()
    document.add_paragraph("Meeting source paragraph.")
    table = document.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Owner"
    table.rows[0].cells[1].text = "Deadline"
    document.save(docx_path)

    text = read_document_text(docx_path)

    assert "Meeting source paragraph." in text
    assert "Owner | Deadline" in text


def test_scene_template_replaces_requirement_and_format(tmp_path: Path):
    templates_dir = tmp_path / "templates"
    scene_dir = templates_dir / "场景" / "专项讨论会"
    scene_dir.mkdir(parents=True)
    (templates_dir / "母模板.md").write_text("A\n{requirement}\nB\n{format}", encoding="utf-8")
    (scene_dir / "要求.md").write_text("专项要求", encoding="utf-8")
    (scene_dir / "格式.md").write_text("专项格式", encoding="utf-8")

    paths, content = render_scene_template(
        templates_dir=templates_dir,
        base_template_name="母模板.md",
        scene_name="专项讨论会",
    )

    assert len(paths) == 3
    assert "专项要求" in content
    assert "专项格式" in content


def test_optimize_command_reads_original_docx_and_writes_generated_templates(tmp_path: Path):
    file_processing = tmp_path / "file_processing"
    original_dir = file_processing / "original"
    original_dir.mkdir(parents=True)
    _write_docx(original_dir / "专项讨论会一.docx", "The meeting decided to ship. Alice owns validation by 2026-05-10.")

    templates_dir = tmp_path / "templates"
    scene_dir = templates_dir / "场景" / "专项讨论会"
    scene_dir.mkdir(parents=True)
    (templates_dir / "母模板.md").write_text("# 母模板\n\n{requirement}\n\n{format}", encoding="utf-8")
    (scene_dir / "要求.md").write_text("专项讨论会要求", encoding="utf-8")
    (scene_dir / "格式.md").write_text("## 议题背景\n\n## 后续行动", encoding="utf-8")
    mapping_file = file_processing / "场景映射.yaml"
    mapping_file.write_text("files:\n  专项讨论会一.docx: 专项讨论会\n", encoding="utf-8")
    output_dir = tmp_path / "outputs" / "opt"

    code = main(
        [
            "optimize",
            "--file-processing-dir",
            str(file_processing),
            "--templates-dir",
            str(templates_dir),
            "--initial-template",
            "母模板.md",
            "--scene-mapping-file",
            str(mapping_file),
            "--template-type",
            "meeting",
            "--rules-file",
            "rules/scoring_rules.yaml",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    assert (output_dir / "专项讨论会一" / "final" / "report.md").exists()
    generated = list((templates_dir / "generated").glob("*/*/final.md"))
    assert generated
    assert "专项讨论会要求" in generated[0].read_text(encoding="utf-8")


def test_evaluate_command_compares_multiple_summary_folders(tmp_path: Path):
    file_processing = tmp_path / "file_processing"
    original_dir = file_processing / "original"
    candidate_a = file_processing / "candidate_a"
    candidate_b = file_processing / "candidate_b"
    original_dir.mkdir(parents=True)
    candidate_a.mkdir()
    candidate_b.mkdir()

    _write_docx(original_dir / "访谈记录一.docx", "Q: What changed?\nA: The onboarding flow changed.")
    _write_docx(candidate_a / "访谈记录一.docx", "Q: What changed?\nA: The onboarding flow changed.")
    _write_docx(candidate_b / "访谈记录一.docx", "A short summary without QA structure.")
    output_dir = tmp_path / "outputs" / "eval"

    code = main(
        [
            "evaluate",
            "--file-processing-dir",
            str(file_processing),
            "--template-type",
            "interview",
            "--rules-file",
            "rules/scoring_rules.yaml",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    comparison = (output_dir / "comparison.md").read_text(encoding="utf-8")
    assert "candidate_a" in comparison
    assert "candidate_b" in comparison
    assert (output_dir / "comparison.csv").exists()
    assert len(list((output_dir / "details").glob("*.json"))) == 2


def test_read_document_content_can_extract_images(tmp_path: Path):
    docx_path = tmp_path / "含图文档.docx"
    image_path = tmp_path / "tiny.png"
    image_path.write_bytes(
        bytes.fromhex(
            "89504E470D0A1A0A0000000D4948445200000001000000010802000000907753DE"
            "0000000C4944415408D763F8FFFF3F0005FE02FEA73581E40000000049454E44AE426082"
        )
    )
    document = Document()
    document.add_paragraph("Document with image.")
    document.add_picture(str(image_path))
    document.save(docx_path)

    content = read_document_content(docx_path, include_images=True)

    assert "Document with image." in content.text
    assert len(content.images) == 1
    assert content.images[0].mime_type == "image/png"


def _write_docx(path: Path, text: str) -> None:
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(path)
