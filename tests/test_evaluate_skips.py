from pathlib import Path

from docx import Document

from harness.cli import main


def test_evaluate_skips_empty_or_missing_summary_files(tmp_path: Path):
    file_processing = tmp_path / "file_processing"
    original_dir = file_processing / "original"
    candidate_ok = file_processing / "candidate_ok"
    candidate_empty = file_processing / "candidate_empty"
    candidate_missing = file_processing / "candidate_missing"
    original_dir.mkdir(parents=True)
    candidate_ok.mkdir()
    candidate_empty.mkdir()
    candidate_missing.mkdir()

    _write_docx(original_dir / "工作纪要.docx", "The meeting decided to ship.")
    _write_docx(candidate_ok / "工作纪要.docx", "The meeting decided to ship.")
    (candidate_empty / "工作纪要.docx").write_bytes(b"")

    output_dir = tmp_path / "outputs"
    code = main(
        [
            "evaluate",
            "--file-processing-dir",
            str(file_processing),
            "--rules-file",
            "rules/scoring_rules.yaml",
            "--output-dir",
            str(output_dir),
        ]
    )

    assert code == 0
    comparison = (output_dir / "comparison.md").read_text(encoding="utf-8")
    assert "candidate_ok" in comparison
    assert "Skipped Files" in comparison
    assert "failed to read summary" in comparison
    assert "missing corresponding summary file" in comparison
    assert len(list((output_dir / "details").glob("*.json"))) == 1


def _write_docx(path: Path, text: str) -> None:
    document = Document()
    document.add_paragraph(text)
    document.save(path)
