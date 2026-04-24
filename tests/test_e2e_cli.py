from pathlib import Path

from harness.cli import main


def test_cli_meeting_end_to_end(tmp_path: Path):
    output_dir = tmp_path / "meeting_run"
    code = main(
        [
            "run",
            "--prompt-file",
            "tests/fixtures/meeting_input.md",
            "--template-type",
            "meeting",
            "--rules-file",
            "rules/scoring_rules.yaml",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert code == 0
    assert (output_dir / "round_1" / "template.md").exists()
    assert (output_dir / "final" / "summary.md").exists()
    report = (output_dir / "final" / "report.md").read_text(encoding="utf-8")
    assert "Final Score:" in report
    assert "Rule ID" in report


def test_cli_interview_end_to_end(tmp_path: Path):
    output_dir = tmp_path / "interview_run"
    code = main(
        [
            "run",
            "--prompt-file",
            "tests/fixtures/interview_input.md",
            "--template-type",
            "interview",
            "--rules-file",
            "rules/scoring_rules.yaml",
            "--output-dir",
            str(output_dir),
        ]
    )
    assert code == 0
    assert (output_dir / "round_1" / "summary.md").exists()
    assert (output_dir / "final" / "report.json").exists()
