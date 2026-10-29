---
name: immigration-assess
description: >
  跨国移民资格评估工具。当用户询问移民可行性、要求计算打分（加拿大 Express Entry CRS、日本高度専門職 HSP）、比较不同国家通路、或请求移民材料清单与流程时使用。
  执行「画像录入→资格前置(gates)→确定性算分→动态对齐(cutoff gap)→结构化输出」五段流程；打分必须调用 scripts/assess.py，禁止 LLM 心算；输出须附置信度标记与免责声明；杰出人才类通路（澳洲 NIV 等）仅整理官方信息，不做评估。
---

# immigration-assess · 跨国移民资格评估

## 铁律（先于一切流程）

1. **算分只走脚本**：任何打分/资格判定调用 `scripts/assess.py`，禁止凭记忆心算或编造分数。
2. **画像先校验**：用户提供画像后，先对照 `schema/profile-schema-v0.json` 校验（脚本报错即停，让用户补字段），再评估。
3. **gates 前置**：资格前置（一票否决项）未过即输出「不满足 + 原因 + 官方链接」，不进入打分。
4. **不编造**：库中没有的政策数字、类别邀请记录、cutoff 值一律明示「未入库/无记录」，不估计。
5. **输出附免责**：每份报告尾部带免责声明与持牌代理转介；不做个案移民建议。
6. **时效检查**：输出每条结论时展示规则的 `last_verified` 日期与置信度标记（●已验证/◐已溯源/○待复核）；存在 `pending_changes` 的规则必须向用户呈现待生效修订。

## 五段工作流

### 1. 画像录入
向用户收集缺失字段（出生日期、学历、语言成绩、工作年资、年收入、婚姻/子女、意向国家）。收集完成后将画像写入临时 JSON 文件（示例见 `engine/tests/fixtures/sample_profile.json`），字段口径见 `references/output-guidelines.md` 的字段说明。

### 2. 资格前置（gates）
调用 `scripts/assess.py` 执行。脚本先跑 gates：任一未过 → 输出 blocked 状态（原因 + 补足路径 + 官方链接），终止该通路评估。

### 3. 确定性算分
gates 全过后，脚本用纯函数计算器（加拿大 CRS / 日本 HSP）算分。脚本输出含分项明细与「未计入项」清单——把未计入项如实转述给用户（总分可能被低估）。

### 4. 动态对齐（gap）
脚本将分数与官方邀请轮 cutoff 历史对比（按轮次类型×类别）；无邀请记录的类别输出「本年度无邀请」而非估分。加拿大按评估日期自动选择现行制或 2026-11-03 新政制。

### 5. 结构化输出
按 `assets/report-template.md` 输出：资格矩阵（✅/⚠️/◻️/❌ 五态 + 原因 + 置信度标记）→ 各通路明细（分项、gap、未计入项）→ 免责区块。国家流程与材料清单问题从 `references/process/` 取，标注 ◐ 置信度。

**多语言**：用户语言为 en/ja 时传 `--lang en` / `--lang ja`（固定标签本地化）。脚本输出中规则数据文本（fail_output、unsupported 等）保持中文——向非中文用户呈现时由你翻译，数字与官方链接保持原样（翻译不碰数字，防误读）。其他语言（如韩语、西班牙语）：不传 --lang，由你翻译固定标签（规则数据文本同规则翻译）。回复始终使用用户的语言。

## 资源索引

| 路径 | 用途 |
|---|---|
| `scripts/assess.py` | 主入口（画像 → 矩阵报告），参数 `--format md/json`、`--as-of 日期`、`--lang zh/en/ja` |
| `scripts/assess.py` 定位机制 | 优先 `ENGINE_ROOT` 环境变量 → skill 目录下 `.engine-root` 文件 → 向上找仓库；skill 被复制出仓库时写入 `.engine-root` 指向仓库路径 |
| `engine/tests/fixtures/sample_profile.json` | 画像字段示例 |
| `schema/profile-schema-v0.json` | canonical 画像 schema（校验依据） |
| `rules/<country>/*.yaml` | 国别规则数据（脚本读取，不直接进上下文） |
| `references/rule-extraction-sop.md` | 规则抽取与人工校验 SOP（维护者用） |
| `references/output-guidelines.md` | 输出措辞、不确定性呈现、置信度标记规范 |
| `references/process/{canada,japan}.md` | 流程与材料清单（问流程时按国别加载） |
| `assets/report-template.md` | 报告模板（矩阵 + 明细 + 免责固定区块） |
| `docs/trigger-matrix.md` | 触发语句测试表（新会话自测用） |

## 边界（不做什么）

- 不做个案移民建议（「你应该走 X」）——输出条件式信息与转介。
- 不评估澳洲 NIV/杰出人才、德国机会卡（v1 信息层）：只整理官方链接与说明。
- 不替用户查实时政策新闻——告知用户哨兵 changelog 在 `docs/changelog.md`。
- 不做翻译、申诉信、签证预约操作类请求——明示超出能力范围。
