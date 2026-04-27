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

## In Progress

- 无

## Next Actions

- 可接入真实 LLM 模型并调优 prompt
- 扩展模板类型（如周报）
- 按业务数据补充更多评测规则

## Blockers

- 无

## Validation Results

- 测试命令：`uv run --with pytest pytest -q`
- 测试结果：`14 passed`
- 配置校验：`environment.yml` YAML 解析通过
- 未执行项：本机未安装 `conda`，因此未在本机实际创建 conda 环境
