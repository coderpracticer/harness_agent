from pathlib import Path

from docx import Document

from harness.cli import main
from harness.document_reader import read_document_text


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


def test_optimize_command_reads_original_docx_and_writes_generated_templates(tmp_path: Path):
    file_processing = tmp_path / "file_processing"
    original_dir = file_processing / "original"
    original_dir.mkdir(parents=True)
    _write_docx(
        original_dir / "task1.docx",
        "The meeting decided to ship. Alice owns validation by 2026-05-10.",
    )

    templates_dir = tmp_path / "templates"
    initial_dir = templates_dir / "initial"
    initial_dir.mkdir(parents=True)
    (initial_dir / "meeting_default.md").write_text(
        "# Meeting\n\n## Meeting Topic\n\n## Action Items\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "outputs" / "opt"

    code = main(
        [
            "optimize",
            "--file-processing-dir",
            str(file_processing),
            "--templates-dir",
            str(templates_dir),
            "--initial-template",
            "meeting_default.md",
            "--template-type",
            "meeting",
            "--rules-file",
            "rules/scoring_rules.yaml",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    assert (output_dir / "task1" / "final" / "report.md").exists()
    generated = list((templates_dir / "generated").glob("*/*/final.md"))
    assert generated


def test_evaluate_command_compares_multiple_summary_folders(tmp_path: Path):
    file_processing = tmp_path / "file_processing"
    original_dir = file_processing / "original"
    candidate_a = file_processing / "candidate_a"
    candidate_b = file_processing / "candidate_b"
    original_dir.mkdir(parents=True)
    candidate_a.mkdir()
    candidate_b.mkdir()

    _write_docx(original_dir / "task1.docx", "Q: What changed?\nA: The onboarding flow changed.")
    _write_docx(candidate_a / "task1.docx", "Q: What changed?\nA: The onboarding flow changed.")
    _write_docx(candidate_b / "task1.docx", "A short summary without QA structure.")
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


def _write_docx(path: Path, text: str) -> None:
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(path)
