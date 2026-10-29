# 治理规则

开源政策类项目的死法几乎都是治理失序而非技术失败。本文件定死分工与决策机制；修改本文件本身需要两名 core maintainer 合签。

## 角色

| 角色 | 职责 | 产生方式 |
|---|---|---|
| Core maintainer | 维护 schema/引擎/scripts；合签规则变更；裁决争议 | 发起人为首任；增补需现有 core 全票同意 |
| Country maintainer | 认领并维护一国规则数据；审核该国相关 PR | 自荐认领（见 CONTRIBUTING），一名 core 批准 |
| Contributor | 提 Issue 与 PR | 无门槛 |

## 决策机制

- **规则数据变更**（`rules/` 下任何 YAML/CSV）：PR 提交 → pathway 所属国 maintainer + **一名 core maintainer** 双签 → 合并。改 `source_url` / `effective_date` / `last_verified` 而不附官方链接的 PR 视为洗白行为，直接拒绝并记录。
- **Schema 变更**：版本号 bump（v0 → v1）需两名 core maintainer 一致同意，附迁移说明与全部样例更新。CI 只认 `schema_version` 当前值。
- **Golden tests**：官方算例是规则的最高裁判。算例与官方页冲突时，以官方页为准并同步修算例；二者无法同时成立时，该通路降级为信息层。
- **争议裁决**：官方原文 > 一切二手来源。裁决过程与依据留在 PR/Issue 里，可追溯。

## staleness 政策（CI 执行）

| 条件 | 后果 |
|---|---|
| `last_verified` ≤ 90 天 | 正常 |
| > 90 天 | 输出降级为「待复核」，前端标灰 |
| > 180 天 | CI 阻断合并；该规则不得参与评估输出 |

`pending_changes` 中已生效（`takes_effect` ≤ 今天）超过 14 天仍未并入主规则的，core 有权直接下线该通路至信息层。

## 错误响应承诺

- 用户报告的规则错误：48 小时内评估；确认错误后优先级高于一切新功能。
- 已造成用户误判的错误：修复后在 changelog 公示，注明影响范围与时间窗。

## 行为准则

对事不对人；指错要给官方链接；被指出错误时先核对再辩护。骚扰与贬低性言论零容忍。
