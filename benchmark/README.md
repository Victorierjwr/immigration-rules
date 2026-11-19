# 评测基准（形态 E）：Agent 法规任务可靠性评测

把 golden 测试转化为可机判的评测集——测的不是模型能不能背出规则，而是 **Agent 在确定性法规任务上的端到端可靠率**（正确调用工具 → 正确算分 → 不越过资格前置）。

## 构成

- `cases-zh.jsonl` / `cases-en.jsonl`：由 `build_cases.py` 从 `engine/tests/golden/` 生成，每条 = 自然语言 prompt（含画像 JSON）+ 机判期望（总分精确匹配，或 gates 拦截匹配）+ 官方来源
- `score.py`：评分器。期望来自官方算例（每条案例带 source_url）——**期望值与实现相互独立**，这正是可靠性的裁判标准
- `build_cases.py`：golden 变更后重新生成

## 用法

```bash
python benchmark/build_cases.py --lang zh          # 生成评测集（31 条）
# 把评测集交给被测 Agent（CLI/Skill/Web 均可），收集结果为 submission JSONL：
#   {"case_id": "canada_ee_crs/01_single_master_clb9", "total": 469}
#   {"case_id": "canada_ee_crs/90_blocked_language",  "blocked": ["language_clb7"]}
python benchmark/score.py submission.jsonl
```

## 评测维度

1. **算分正确率**：总分与 golden 期望精确匹配（含 CRS 双制 as_of 案例、边界 case）
2. **gates 行为**：资格前置拦截时必须输出未过门槛 id 且**不产出分数**
3. **对抗项**：被测系统若试图直接心算而不调用工具，边界案例（恰好分数线、恰好像素门槛）会暴露

## 防背题

- prompt 可换皮（build_cases.py 的 PROMPTS 模板），画像数值可旋转——期望值始终来自 golden
- 新政双制案例（as_of 标注）测试系统对生效日期的处理
- 规则库更新时 golden 与评测集同步再生成

> 研究合作与结果发布欢迎联系仓库维护者。期望值溯源：每条案例的 source_url 指向官方算例或官方规则页。
