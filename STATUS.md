# STATUS

## Done

- 项目结构初始化完成（`src/harness`、`rules`、`outputs`、`tests`）
- 三智能体完成：模板生成、摘要生成、评测
- 统一 LLM 客户端适配层完成（`heuristic` 默认，支持 `openai` 后端）
- 本地 OpenAI 兼容地址（如 vLLM）支持无 `OPENAI_API_KEY`
- 规则系统完成：YAML 加载、Pydantic 校验、按模板类型筛选
- 主流程完成：模板生成 -> 摘要生成 -> 评测 -> 反馈优化（最多 3 轮 / 目标 85 分）
- 报告系统完成：输出最终分数、逐条扣分依据、未触发规则、优化建议
- CLI 完成：`python -m harness.cli run ...`
- 测试完成：单元、集成、e2e
- 依赖导出完成：生成可用于远程 conda 环境安装的 `requirements.txt`
- conda 部署配置完成：新增 `environment.yml` 和 `requirements-dev.txt`
- CLI 支持直接传入本地模型服务配置：`--base-url`、`--model`、`--api-key`、`--timeout-seconds`
- 新增 `.docx` 文档读取：支持段落、表格文本，检测嵌入对象
- 新增 `optimize` 命令：仅读取 `file_processing/original`，用指定初始模板执行模板优化循环
- 新增 `evaluate` 命令：读取 `file_processing/original` 和所有摘要候选文件夹，输出横向对比报告
- 新增模板目录：`templates/initial` 存放用户初始模板，`templates/generated` 存放优化生成模板
- 新增中文母模板机制：`templates/母模板.md` 使用 `{requirement}` 和 `{format}` 占位符
- 新增中文场景模板：`templates/场景/<场景名>/要求.md` 与 `格式.md`
- 新增可选多模态 `.docx` 解析：`--enable-multimodal-docx` 会把提取到的图片发送给本地多模态 vLLM/OpenAI-compatible 模型
- 新增类型映射文件：`file_processing/类型映射.yaml`
- 内置默认关键词映射：`发布会 -> press_conference`、`工作 -> meeting`、`知识 -> knowledge`、`新闻 -> news`
- `optimize` / `evaluate` 会遍历全部 `.docx` 文件，并按每个文件名独立选择模板类型
- `evaluate` 遇到缺失、空白或无法读取的摘要文件会记录跳过原因并继续处理其他文件
- `optimize` 改为读取 `file_processing/150data.xlsx`，按 A 列场景归并多条样本
- 同一场景只产出一个最终模板，输出到 `templates/generated/<run_id>/<scene>/final.md`
- 未覆盖的新场景会自动生成 `templates/场景/<scene>/要求.md` 与 `格式.md` 后再开始优化

## In Progress

- 无

## Next Actions

- 可接入真实 LLM 模型并调优 prompt
- 扩展模板类型（如周报）
- 按业务数据补充更多评测规则
- 若使用多模态模型，可开启 `--enable-multimodal-docx` 解析图片；未开启时只解析文本和表格

## Blockers

- 无

## Validation Results

- 测试命令：`uv run --offline --with pytest --with python-docx pytest -q --basetemp temp/pytest_run`
- 测试结果：`26 passed`
- 配置校验：`environment.yml` YAML 解析通过
- 未执行项：本机未安装 `conda`，因此未在本机实际创建 conda 环境
## 2026-04-28 Update

### Done

- 模板优化数据读取已支持 `.xlsx` 与 `.json`。
- `.xlsx` 数据源现在只读取 A/C/U/V 列，分别作为场景、发言内容、子场景、领域。
- `.json` 数据源支持 `场景`、`发言内容`、`子场景`、`领域` 以及 `scene`、`content`、`sub_scene`、`domain` 字段。
- 优化分组已升级为“场景 -> 子场景”；同一场景下不同子场景会分别进入模板优化流程。
- 子场景产物会写入 `outputs/<scene>/<sub_scene>/` 与 `templates/generated/<run_id>/<scene>/<sub_scene>/`；无子场景时保持旧路径。
- 模板目录解析兼容 readable 中文目录/文件名：`场景`、`母模板.md`、`要求.md`、`格式.md`，同时保留旧乱码路径兼容。

### In Progress

- 无。

### Next Actions

- 接入真实业务 json/xlsx 样例后，可校验字段别名是否还需要扩展。
- 后续可在 `templates/场景/<scene>/<sub_scene>/` 层级继续细化子场景专属模板组件。

### Blockers

- 当前环境没有可用 `pytest`：`.venv` 中缺少 pytest，`uv run --offline --with pytest` 因离线缓存缺少 pytest 无法解析。

### Validation Results

- `.\.venv\Scripts\python.exe -m compileall -q src tests` 通过。
- 手写端到端验证通过：覆盖 xlsx A/C/U/V 读取、json 读取、场景/子场景分组、`optimize` 子场景输出路径。
- `uv run --offline --with pytest --with python-docx pytest -q --basetemp temp/pytest_run` 未通过，原因是离线缓存缺少 pytest。
- `.\.venv\Scripts\python.exe -m pytest -q --basetemp temp/pytest_run` 未通过，原因是 `.venv` 未安装 pytest。
