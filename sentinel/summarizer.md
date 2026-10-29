# Sentinel 摘要撰写与审核规范

Issue 由 snapshot workflow 自动创建（标签 `sentinel-change` + `needs-review`），**摘要必须由人写**——自动 diff 只负责"页面变了"，语义要靠维护者翻译成"政策变了什么"。

## 处理流程

```
snapshot（自动）→ Issue[needs-review] → maintainer 填摘要三段
  ├─ 有政策含义 → 加 confirmed → publish workflow 自动写 changelog/RSS/TG → Issue 自动关闭
  └─ 无政策含义（模板改版/横幅轮换）→ 加 false-positive → 直接关闭
```

## 摘要三段写法

**变了什么**（1-3 句，只写事实）
- ✅ "技能技工类轮于 10 月 1 日发出 3,500 份邀请，cutoff 476。"
- ✅ "高度専門職最低年收要件拟从 300 万日元上调，省令修订预计本年度内。"
- ❌ "页面有更新"（等于没写）／"利好申请人！"（推测与立场）

**对谁有影响**（哪类申请人 / 哪条通路）
- ✅ "技工类申请人（cutoff 下探至 476）；法语类别申请人（cutoff 持续走高至 435）。"
- ❌ "所有人"。

**官方链接**：保留模板里自动填的官方 URL；如正文内有更直达的子页面，替换为子页面。

## 审核清单（加 confirmed 前逐项过）

- [ ] diff 变更行确实涉及政策语义（分数/日期/清单/流程/费用），而非页脚、广告、导航
- [ ] 摘要三段全部填写，无模板注释残留
- [ ] 数值与官方页面原文一致（不凭记忆改写）
- [ ] 该变更是否需要改 `rules/` 规则数据？需要 → **另开 PR**（走 CONTRIBUTING 流程），Issue 只承载信息发布
- [ ] 关键词命中为"无"时，二次确认 diff 是否纯模板改版

## 误报处理

加 `false-positive` 标签后关闭。同一目标一周内 ≥3 次误报 → 在 targets.yaml 为该目标加 `selector`（缩小到正文区域）并 PR。

## 告警 Issue（sentinel-alert）

连续 14 天抓取失败或内容量异常时自动创建。处理：人工打开页面确认 URL 是否迁移（改 targets.yaml PR）或站点临时故障（留言关闭）。**告警期间该目标处于失明状态**——这正是规划里"政策响应滞后"风险的暴露点，优先处理。

## 后续升级（预留）

LLM 自动起草摘要：将 diff 与 targets.yaml 关键词喂给模型生成三段草稿，仍走 `needs-review` 人工确认，绝不自动 confirmed。接口在 publish 流程中预留，Phase 1 先人工。
