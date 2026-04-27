# Template Directory

Recommended layout:

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

`母模板.md` provides the shared prompt skeleton. Each scene folder provides `要求.md` for `{requirement}` and `格式.md` for `{format}`.

Optimization writes generated templates to `templates/generated/<run_id>/<document_stem>`.
