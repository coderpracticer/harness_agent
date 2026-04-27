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
- `.docx` source and summary files under `file_processing`

## Data Layout

Place `.docx` files under `file_processing`.

```text
file_processing/
  original/
    task_001.docx
    task_002.docx
  candidate_a/
    task_001.docx
    task_002.docx
  candidate_b/
    task_001.docx
    task_002.docx
  场景映射.yaml
```

`original` contains source documents. Every other folder is treated as a summary candidate set.
Files are matched by file name first, then by stem prefix.

The `.docx` reader extracts paragraph text and table text. If `--enable-multimodal-docx` is set, embedded images are attached to OpenAI-compatible multimodal model requests.

Scene mapping example:

```yaml
files:
  专项讨论会示例.docx: 专项讨论会
```

## Template Layout

```text
templates/
  母模板.md
  initial/
    meeting_default.md
    interview_default.md
  场景/
    专项讨论会/
      要求.md
      格式.md
  generated/
```

The recommended template mode uses a parent template with placeholders:

```markdown
# 摘要模板

## 场景要求
{requirement}

## 输出格式
{format}
```

For a scene such as `专项讨论会`, `templates/场景/专项讨论会/要求.md` replaces `{requirement}`, and `templates/场景/专项讨论会/格式.md` replaces `{format}`.

Legacy user-authored initial templates can still be placed under `templates/initial`.
Optimization outputs generated templates under `templates/generated/<run_id>/<document_stem>`.

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

## Optimize Templates

Optimization reads only `file_processing/original`, generates summaries, evaluates them, and writes optimized templates:

```bash
python -m harness.cli optimize \
  --file-processing-dir file_processing \
  --template-type meeting \
  --initial-template 母模板.md \
  --templates-dir templates \
  --scene-mapping-file file_processing/场景映射.yaml
```

## Evaluate Summary Folders

Evaluation reads `file_processing/original` plus every other summary folder and produces comparison reports:

```bash
python -m harness.cli evaluate \
  --file-processing-dir file_processing \
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
python -m harness.cli optimize \
  --file-processing-dir file_processing \
  --template-type meeting \
  --initial-template 母模板.md \
  --scene-mapping-file file_processing/场景映射.yaml \
  --llm-backend openai \
  --base-url http://127.0.0.1:8000/v1 \
  --model /path/to/model \
  --timeout-seconds 120
```

`--api-key` is optional for local or private-network base URLs.

For a multimodal model served by vLLM, add:

```bash
--enable-multimodal-docx
```

The harness will attach extracted `.docx` images to summary generation and evaluation requests. This is the path for OCR-like or chart-aware behavior; the actual visual understanding quality depends on the served multimodal model.

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
