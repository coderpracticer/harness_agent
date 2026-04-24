# 评测规则说明

你可以直接编辑 [`scoring_rules.yaml`](./scoring_rules.yaml) 来控制评测逻辑，无需改代码。

## 文件结构

- `version`: 规则版本
- `base_score`: 基础分，默认 100
- `rules`: 扁平规则列表

## 单条规则字段

- `id`: 规则唯一 ID
- `name`: 规则名称
- `applies_to`: 生效范围，`all | meeting | interview`
- `max_deduction`: 该规则最多可扣分
- `judge_prompt`: 规则提示词（核心可编辑字段）
- `deduction_guide`: 扣分分档说明

## 示例

```yaml
- id: structure_template_alignment
  name: "结构-模板一致性"
  applies_to: all
  max_deduction: 15
  judge_prompt: "检查摘要是否按模板结构组织，标题层级是否清晰。"
  deduction_guide: "结构清晰扣0；个别标题缺失扣5-8；结构混乱扣9-15。"
```

## 注意事项

- `id` 不能重复
- `max_deduction` 必须是非负整数
- 程序会将单条规则扣分强制限制在 `0..max_deduction`，越界会记录 warning
