---
name: immigration-assess
description: >
  跨国移民资格评估工具。当用户询问移民可行性、要求计算打分（加拿大 Express Entry CRS、日本高度専門職 HSP）、比较不同国家通路、或请求移民材料清单与流程时使用。
  执行「画像录入→资格前置(gates)→确定性算分→动态对齐(cutoff gap)→结构化输出」五段流程；打分必须调用 scripts/assess.py，禁止 LLM 心算；输出须附置信度标记与免责声明；杰出人才类通路（澳洲 NIV 等）仅整理官方信息，不做评估。
---

# immigration-assess

## 铁律

1. **算分只走脚本**：调用 `scripts/assess.py`，禁止心算或编造分数。
2. **画像先校验**：字段不全先对照 `schema/profile-schema-v0.json` 补齐（脚本报错即停）。
3. **gates 前置**：资格前置未过即输出「不满足 + 原因 + 官方链接」，不进打分。
4. **不编造**：库中没有的政策数字、邀请记录、cutoff 值一律明示「未入库/无记录」。
5. **输出附免责**：每份报告带免责声明与持牌代理转介；不做个案建议。
6. **时效检查**：每条结论展示 `last_verified` 与置信度标记（●/◐/○）；存在 `pending_changes` 的规则必须呈现待生效修订。

## 五段工作流

### 1. 画像录入
收集缺失字段（出生日期、学历、语言成绩、工作年资、年收入、婚姻/子女、意向国）。字段口径见 `references/output-guidelines.md`；示例见 `engine/tests/fixtures/sample_profile.json`。

### 2. 资格前置
运行 `scripts/assess.py`。gates 任一未过 → 输出 blocked（原因 + 补足路径 + 官方链接），终止该通路。

### 3. 确定性算分
gates 全过后脚本算分。把输出的「未计入项」如实转述用户——总分可能被低估。

### 4. 动态对齐
分数对照官方邀请轮 cutoff（按轮次类型×类别）；无邀请记录的类别输出「本年度无邀请」。加拿大按评估日期自动选现行制或 2026-11-03 新政制。

### 5. 结构化输出
按 `assets/report-template.md`：资格矩阵（五态 + 原因 + 置信度）→ 通路明细（分项、gap、未计入项）→ 免责区块。流程与材料清单问题从 `references/process/` 取，标 ◐。

**多语言**：用户语言 en/ja 传 `--lang en|ja`。规则数据文本（fail_output、unsupported 等）保持中文，由你翻译呈现；数字与官方链接永不翻译。其他语言不传 --lang，由你翻译固定标签。回复始终用用户的语言。

## 资源索引

| 路径 | 用途 |
|---|---|
| `scripts/assess.py` | 主入口；参数 `--format md/json`、`--as-of 日期`、`--lang zh/en/ja` |
| `engine/tests/fixtures/sample_profile.json` | 画像字段示例 |
| `schema/profile-schema-v0.json` | canonical 画像 schema |
| `rules/<country>/*.yaml` | 国别规则数据（脚本读取） |
| `references/output-guidelines.md` | 输出措辞、置信度标记规范 |
| `references/process/{canada,japan}.md` | 流程与材料清单（按国别加载） |
| `assets/report-template.md` | 报告模板 |
| `docs/trigger-matrix.md` | 触发语句测试表 |

## 边界

- 不做个案移民建议——输出条件式信息与转介。
- 不评估澳洲 NIV/杰出人才、德国机会卡（v1 信息层）：只整理官方链接。
- 不查实时政策新闻——告知用户哨兵 changelog 在 `docs/changelog.md`。
- 不做翻译、申诉信、签证预约类请求——明示超出能力范围。
