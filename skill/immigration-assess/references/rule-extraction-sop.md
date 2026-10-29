# 规则抽取与人工校验 SOP

> 面向国别 maintainer。规则入库的唯一合法路径：官方原文 → 人工逐条对照 → YAML + 官方算例 golden test。LLM 抽取永远只是草稿，人工核对是硬性环节。

## 六步流程

1. **定位官方原文**：只认官方域名（政府/移民局/官方指定机构）。中介博客、新闻只作为线索，不能作为 `source_url`。
2. **LLM 抽取草稿**：把官方原文喂给模型生成 YAML 草稿——只做结构化，不承诺正确。
3. **人工逐条核对**：对照官方原文逐字段检查。数字、日期、口径逐一过；术语与官方现行口径逐字对齐（例：澳洲用 CSOL/MLTSSL，不用已废止的 SOL）。
4. **官方算例验证**：找官方 worked examples 或官方算分表算例，构造 golden test（`engine/tests/golden/<pathway>/`）。算例期望值由人手工推算——与计算器相互独立验证。
5. **本地回归**：`python scripts/validate_rules.py && python -m unittest engine.tests.test_engine && python -m engine.tests.run_golden_tests`，全绿才提 PR。
6. **PR + 双合签**：按 CONTRIBUTING.md 模板（官方 URL + 生效日期 + 算例必填），两位 maintainer 合签后合并。

## 变更类型处理

| 类型 | 处理 |
|---|---|
| 现行规则微调（分数/日期/门槛） | 改 YAML + 补/更新 golden + PR |
| 已公布待生效修订 | 不动主规则，写进 `pending_changes` 块；生效日过后按官方原文并入主规则并删除该块 |
| 新政制度性重构（如 2026-11-03 CRS） | 增加 regime 切换段（`regime_switch`）+ 新 regime golden 案例 + 评估日期自动选择 |
| 官方页术语改名/编号变更 | 同步改规则文件所有引用；术语口径写入 `meta` |

## 常见陷阱（历史教训）

- **YAML 整数键**：`2: 53` 是整数键，代码按字符串查会静默得 0——入库后跑一遍 golden 就能发现。
- **年龄档边界**：官方表的 18/19/20-29 等档位，注意「≥」还是「>」语义，golden 必须覆盖边界。
- **转换表缺失**：没有官方对照表的能力（如 TEF→NCLC）不要猜——进 `unsupported` 清单明示。
- **时效降级**：`last_verified` 超过 90 天 CI 降 ○、180 天阻断——维护者看到 ○ 要主动核对。
