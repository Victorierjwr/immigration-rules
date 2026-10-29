# CRS 2026-11-03 新政落地核对清单

> 触发条件：2026-11-03 起（建议当日及随后一周内执行）。
> 背景：加拿大 CRS 改革（劳动力市场整合因子、LMIA 取消、job offer 分档）已由官方 2026-10-16 公告、
> 2026-10-29 二次核验确认细节无修订。本清单是「公告 ≠ 落地」的核对程序——公告细节与实际实施
> 之间永远可能存在 PIP 层修正。

## 第一遍：哨兵捕获

1. 查看 `docs/changelog.md` 与 GitHub Issues 中标签 `sentinel-change` 的 `ircc_changes` 相关条目——新政落地时 changes.html 页面必然变化。
2. 若无捕获：人工打开 changes.html 与 crs-criteria.html 确认是否已切换（页面可能静默更新，diff 基线为 2026-10-29 快照）。

## 第二遍：官方实施状态核对（人工，按序）

| # | 检查项 | 通过标准 | 处置 |
|---|---|---|---|
| 1 | IRCC PIPs 发布 | 发布「CRS 2026 年 11 月更新」实施细节 | 下载/抓取，比对数值与公告 |
| 2 | crs-criteria.html 切换为新表 | 页面出现 job offer 分档（100/70/50）、劳动力市场整合因子说明 | 见下 |
| 3 | 邀请轮恢复 | recalc 完成、新一轮 draws 出现 | cutoff 种子数据更新时点 |
| 4 | 官方计算器上线 | IRCC 在线计算器支持新 regime | golden 期望值与新计算器交叉验证（官方算例回归升级） |
| 5 | high-wage 职业清单 | NOC 级 high-wage 清单发布 | 若发布 → 评估是否入库（high-wage 加分 70/40/20） |

## 第三遍：规则库处置（按 SOP）

**场景 A：落地细节与公告一致**（多数情况）
- `ee_crs.yaml`：删除 `pending_changes` 块；把摘要并入 `meta.regime_2026_11_03_note`；`effective_date` 更新为新政生效日（或注明「现行制至 2026-11-02」）；
- `last_verified` 更新为核对日；`verified_by` 署名；
- golden 保留 N1/N2/N3 新制案例并升级为正式回归；
- PR 双合签。

**场景 B：PIPs 修正了数值/机制**
- 按 rule-extraction-sop.md 更新 `regime_switch` 段；
- 新增 golden 案例覆盖修正后的数值；
- 在 changelog 与 PR 中记录「公告 vs 落地」差异——这正是 sentinel 存在的意义：把政策漂移变成公开变更记录。

**场景 C：新政推迟/变更日期**
- 更新 `regime_switch.date`；保留 pending_changes 块（注明推迟原因与新日期）；
- 哨兵继续盯 changes.html 直至新日期确认。

**场景 D：新政提前实施（未公告）**
- 按实际生效日调整 `regime_switch.date`；golden 以官方新表为准重算；
- 记录为哨兵捕获的「未公告变更」事件。

## 第四遍：交付层联动

- `sentinel/summarizer.md`：记录本次变更摘要写法（真实案例供后续参考）；
- `docs/changelog.md`：正式发布条目（人工确认后由 publish 流程追加）；
- `README.md`：若 regime 结构变化，更新「当前阶段」段落；
- skill 侧无需改动（regime 由 `--as-of` 自动选择）——除非新 regime 引入新画像字段，则同步 `profile-schema-v0.json` + `output-guidelines.md` 字段表。

## 核对完成标志

- `python scripts/validate_rules.py`、`python -m unittest engine.tests.test_engine`、`python -m engine.tests.run_golden_tests` 全绿；
- `docs/changelog.md` 有本次变更的正式条目；
- PR 合入后，`ircc_changes` 哨兵基线更新，无 pending_changes 残留（或残留项注明原因）。
