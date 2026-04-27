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
- local OpenAI-compatible LLM endpoints such as vLLM

## Conda Setup

Create the environment on the remote server:

```bash
conda env create -f environment.yml
conda activate harness-summary-iteration
```

If the environment already exists:

```bash
conda activate harness-summary-iteration
pip install -r requirements.txt
pip install -e .
```

For test dependencies:

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Run With Heuristic Backend

This mode does not call an LLM and is useful for smoke tests:

```bash
python -m harness.cli run \
  --prompt-file tests/fixtures/meeting_input.md \
  --template-type meeting
```

## Run With vLLM On A800

Start vLLM on the A800 server separately, for example:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /path/to/model \
  --host 0.0.0.0 \
  --port 8000
```

Then run the harness against the local OpenAI-compatible endpoint:

```bash
python -m harness.cli run \
  --prompt-file tests/fixtures/meeting_input.md \
  --template-type meeting \
  --llm-backend openai \
  --base-url http://127.0.0.1:8000/v1 \
  --model /path/to/model \
  --timeout-seconds 120
```

`--api-key` is optional for local or private-network base URLs.

## Environment Variables

The same LLM settings can also be configured through environment variables:

```bash
export HARNESS_LLM_BACKEND=openai
export OPENAI_BASE_URL=http://127.0.0.1:8000/v1
export OPENAI_MODEL=/path/to/model
export HARNESS_LLM_TIMEOUT_SECONDS=120
```

`OPENAI_API_KEY` is only required for non-local public endpoints.

## Outputs

Each run writes artifacts under `outputs/<run_id>` unless `--output-dir` is provided:

- `round_N/template.md`
- `round_N/summary.md`
- `round_N/evaluation.json`
- `final/template.md`
- `final/summary.md`
- `final/report.json`
- `final/report.md`
