# Harness Summary Iteration

## Optimization Data Format

Template optimization accepts `.xlsx` and `.json` inputs.

For `.xlsx`, only these columns are read:

- A: scene
- C: utterance/content
- U: sub-scene
- V: domain

For `.json`, each record may use either Chinese or English field names:

- `场景` / `scene`
- `发言内容` / `content`
- `子场景` / `sub_scene`
- `领域` / `domain`

Sub-scenes belong to scenes. When `子场景` / `sub_scene` is present, optimization runs separately for each `(scene, sub_scene)` group and writes artifacts under `outputs/<scene>/<sub_scene>/` and `templates/generated/<run_id>/<scene>/<sub_scene>/`.

This project runs an iterative summary harness for `.docx` documents:

1. Optimize scene-level templates from `file_processing/150data.xlsx`
2. Evaluate `.docx` summaries from `file_processing`
3. Route each file or scene to a template type by keyword
4. Write full reports under `outputs`

## Conda Setup

```bash
conda env create -f environment.yml
conda activate harness-summary-iteration
```

For an existing conda env:

```bash
pip install -r requirements.txt
pip install -e .
```

For tests:

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Data Layout

```text
file_processing/
  150data.xlsx
  original/
    新品发布会.docx
    工作纪要.docx
    知识材料.docx
    新闻事件.docx
  candidate_a/
    新品发布会.docx
    工作纪要.docx
    知识材料.docx
    新闻事件.docx
  candidate_b/
    新品发布会.docx
    工作纪要.docx
    知识材料.docx
    新闻事件.docx
  类型映射.yaml
```

`original` stores source documents. Every other folder is treated as one summary candidate set.
Both `optimize` and `evaluate` process all matched files, not a single file.

## Type Mapping

The default mapping is also built into the code, and can be edited in `file_processing/类型映射.yaml`:

```yaml
keywords:
  发布会: press_conference
  工作: meeting
  知识: knowledge
  新闻: news

files:
  某个特殊文件.docx: knowledge
```

Exact `files` mappings take priority. If no exact match exists, the harness checks whether the filename contains a configured keyword.

For optimization, the mapping is applied to normalized scene names from column A in `150data.xlsx`.

## Template Layout

```text
templates/
  母模板.md
  场景/
    press_conference/
      要求.md
      格式.md
    meeting/
      要求.md
      格式.md
    knowledge/
      要求.md
      格式.md
    news/
      要求.md
      格式.md
  generated/
```

`母模板.md` contains placeholders:

```markdown
## 场景要求
{requirement}

## 输出格式
{format}
```

For each file, the detected type chooses `templates/场景/<type>/要求.md` and `格式.md`.

## Optimize

Optimization reads `file_processing/150data.xlsx` only. The Excel columns are:

- Column A: scene type, usually with a numeric suffix such as `发布会议1`, `发布会议2`
- Column B: title
- Column C: content

Rows with the same normalized scene are grouped together. For example, `发布会议1` and `发布会议2` are grouped as `发布会议`, and one final template is generated for that scene.

If a scene is not covered by `templates/场景/<type>` or the mapping file, the harness automatically creates an initial scene template folder before optimization.

```bash
python -m harness.cli optimize \
  --file-processing-dir file_processing \
  --optimization-data-file file_processing/150data.xlsx \
  --initial-template 母模板.md \
  --type-mapping-file file_processing/类型映射.yaml
```

`--template-type meeting` is only a fallback when no mapping matches.

## Evaluate

Evaluation reads `file_processing/original` and every other summary folder, routes every source file by mapping, and writes a comparison report:

```bash
python -m harness.cli evaluate \
  --file-processing-dir file_processing \
  --type-mapping-file file_processing/类型映射.yaml
```

Evaluation does not load templates.
If a summary file is missing, empty, or unreadable, that pair is skipped and recorded under `Skipped Files` in `comparison.md`; the rest of the batch continues.

## vLLM On A800

Start vLLM separately:

```bash
python -m vllm.entrypoints.openai.api_server \
  --model /path/to/model \
  --host 0.0.0.0 \
  --port 8000
```

Run the harness:

```bash
python -m harness.cli optimize \
  --file-processing-dir file_processing \
  --initial-template 母模板.md \
  --type-mapping-file file_processing/类型映射.yaml \
  --llm-backend openai \
  --base-url http://127.0.0.1:8000/v1 \
  --model /path/to/model \
  --timeout-seconds 120
```

For multimodal vLLM models, add:

```bash
--enable-multimodal-docx
```

The harness attaches extracted `.docx` images to summary generation and evaluation requests. Paragraph and table text are always extracted.

## Outputs

Optimization outputs:

- `outputs/optimize_<run_id>/<scene>/round_N/...`
- `outputs/optimize_<run_id>/<scene>/final/report.md`
- `templates/generated/<run_id>/<scene>/final.md`

Evaluation outputs:

- `outputs/evaluate_<run_id>/comparison.md`
- `outputs/evaluate_<run_id>/comparison.csv`
- `outputs/evaluate_<run_id>/comparison.json`
- `outputs/evaluate_<run_id>/details/*.json`
