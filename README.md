# Harness Summary Iteration

An iterative harness that runs three agents in a loop:

1. Summary template generator
2. Summary generator
3. Evaluation agent

It supports:

- template types: `meeting`, `interview`
- editable YAML scoring rules
- score + deduction rationale outputs
- iterative optimization with stopping conditions

Run:

```bash
uv run python -m harness.cli run \
  --prompt-file prompt_dir/task.md \
  --template-type meeting
```

## Local model deployment notes

When using a local OpenAI-compatible endpoint (for example vLLM), API key can be omitted.

PowerShell example:

```powershell
$env:HARNESS_LLM_BACKEND="openai"
$env:OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
$env:OPENAI_MODEL="your-local-model"
# OPENAI_API_KEY optional for local base URL
```

## Export requirements

Export currently installed third-party libraries from the local `.venv`:

```powershell
$env:UV_CACHE_DIR=".uv_cache"
uv pip freeze --python .venv\Scripts\python.exe |
  Where-Object { $_ -notmatch '^-e\s+file:///' } |
  Out-File -Encoding utf8 requirements.txt
```
