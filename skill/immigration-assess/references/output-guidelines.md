# 输出规范：措辞、不确定性、置信度标记

## 画像字段收集口径（canonical）

用户表达 → canonical 字段映射：

| 用户说 | 字段 |
|---|---|
| 年龄/生日 | `person.birth_date`（YYYY-MM-DD） |
| 雅思/思培/托福分数 | `language.english.{test,overall,speaking,listening,reading,writing}` |
| 法语 TEF/TCF | `language.french.{test,...}`（NCLC 换算未入库——收集后告知用户） |
| JLPT | `language.other.jlpt`（N1/N2） |
| 学历 | `education.highest_degree`（phd/master/bachelor/diploma/other）+ `country` |
| 工作年资 | `work.years_related`（职业相关）；加拿大本地年资 `work.years_in.CA` |
| 年收入 | `work.income_annual.{amount,currency}`——币种必须与目标国一致（日本以日元计） |
| 婚姻/子女 | `person.marital_status` / `children`；配偶信息 `person.spouse_profile` |
| ECA/职业评估 | `education.eca_done` / `credentials.skills_assessment` |
| job offer | `intent.job_offer_wage_tier`（none/2x/1.5x/1.3x，相对平均中位薪资） |

缺失字段逐项追问；收集完成后写入 JSON 跑 `scripts/assess.py`。

## 置信度标记

| 标记 | 含义 | 何时出现 |
|---|---|---|
| ● 已验证 | 库内规则 + golden 算例覆盖 + 核对日期新鲜（≤90 天） | 正常评估输出 |
| ◐ 已溯源 | 有官方来源与核对日期，但无算例回归覆盖 | 流程、材料清单、未实现评估的通路 |
| ○ 待复核 | 规则超龄 / 存在 `pending_changes` / 临时检索所得 | 政策窗口期（如 2026-11-03 CRS 新政落地前） |

## 不确定性呈现

- 有差距时：给出「差多少 + 可提升路径」（如「雅思每项 +0.5 → CRS +X」），用脚本输出的 gap 值说话。
- 未计入项必须原文转述（脚本 `unsupported` 字段），告诉用户「总分可能被低估」。
- 库中无记录/无规则：明说「规则库暂无此通路/此记录」，给官方链接，不估计。

## 措辞红线

- ❌ 「你应该申请 X」——个案建议，合规红线。
- ❌ 「你肯定能移民」——任何确定性承诺。
- ✅ 「你的 CRS 478 分，高于该类别最近邀请轮 cutoff 476（来源 X）」——条件式信息呈现。
- ✅ 「若雅思提升至 CLB 9，可增加 X 分」——条件式建议 + 转介。
- 杰出人才类通路（NIV/J-Skipper）只整理官方信息，结尾注明「此类通路评估建议咨询持牌代理」。

## 多语言呈现

- `--lang zh|en|ja` 本地化固定标签（标题、矩阵、分项标签、gap 参考行、免责）。
- 规则数据文本（fail_output、unsupported 等）保持中文，由你翻译呈现；数字与官方链接永不翻译。
- 其他语言不传 `--lang`，翻译固定标签即可；回复始终用用户的语言。

## 免责区块

每份报告尾部固定附 `assets/report-template.md` 的免责区块原文，措辞不掺模型发挥。转介行：加拿大 RCIC / 澳洲 MARA / 日本行政书士 / 德国相关资格人员。
