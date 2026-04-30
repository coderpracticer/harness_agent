# Harness 摘要模板迭代系统计划

## Checklist

- [x] 初始化 Python 项目结构
- [x] 实现三智能体与统一客户端适配层
- [x] 实现规则加载、YAML 校验、可编辑规则目录
- [x] 实现主流程迭代（最多 3 轮 + 85 分阈值）
- [x] 实现产物落盘（每轮 + final 报告）
- [x] 实现 CLI 入口与默认参数
- [x] 补齐单元/集成/e2e 测试
- [x] 执行验证并更新 `STATUS.md`
- [x] 支持 `file_processing/original` 与多摘要文件夹批量评测
- [x] 支持 `.docx` 原文和摘要读取（段落与表格）
- [x] 支持模板目录：`templates/initial` 与 `templates/generated`
- [x] 增加 `optimize` / `evaluate` 两个项目入口
- [x] 支持中文文件名、中文模板名与中文场景名
- [x] 支持母模板 `{requirement}` / `{format}` 场景化渲染
- [x] 支持可选多模态 `.docx` 图片输入到 vLLM/OpenAI-compatible 请求
- [x] 支持 `file_processing/类型映射.yaml` 通过文件名关键词自动路由模板类型
- [x] 支持优化/评测阶段对多类型文件全量批处理
- [x] 支持 `file_processing/150data.xlsx` 作为模板优化专用数据源
- [x] 支持按 Excel 场景列聚合多条数据，每个场景只产出一个最终模板
- [x] 支持优化时自动为未知场景创建初始模板组件
## 2026-04-28 数据格式与子场景支持

- [x] 支持模板优化数据读取 `.xlsx` 与 `.json`
- [x] `.xlsx` 仅读取 A/C/U/V 列：场景、发言内容、子场景、领域
- [x] `.json` 支持中英文字段名与常见 records/items/data 包装结构
- [x] 优化分组从单层场景扩展为“场景 -> 子场景”
- [x] 子场景存在时，优化报告输出到 `outputs/<scene>/<sub_scene>/`
- [x] 子场景存在时，生成模板输出到 `templates/generated/<run_id>/<scene>/<sub_scene>/final.md`
- [x] 保持无子场景数据的旧路径兼容：`outputs/<scene>/` 与 `templates/generated/<run_id>/<scene>/`
- [x] 补充针对 xlsx A/C/U/V、json、子场景产物路径的测试用例
- [x] 增加 `--optimization-scope`，支持按 `scene`、`sub_scene`、`scene_sub_scene`、`scene_and_sub_scene` 控制模板迭代分组
- [x] 将默认分组改为 `scene_and_sub_scene`：一定生成场景级模板，有子场景时同时生成子场景级模板
- [x] 增加 `--max-context-chars`，支持在模板迭代前截断过长输入
