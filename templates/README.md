# Template Directory

Place user-provided initial templates under `templates/initial`.

Generated templates from optimization runs are written under `templates/generated/<run_id>/<document_stem>`.

Examples:

```text
templates/
  initial/
    meeting_default.md
    interview_default.md
  generated/
```

Use an initial template by name:

```bash
python -m harness.cli optimize \
  --file-processing-dir file_processing \
  --template-type meeting \
  --initial-template meeting_default.md
```
