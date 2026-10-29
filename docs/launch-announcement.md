# 上线公告草稿（T1.6 · 发布前由维护者补全并发布）

> 使用说明：这是借势发布的文案草稿。**发布时机：加拿大 2027-29 移民水平计划公布当日或次日**（预计 2026-11 初）——哨兵会在计划公布后自动捕获 IRCC 页面变更，届时把真实变更写进公告的"首次实战"段落，借热点完成冷启动。
> 发布渠道：Reddit（r/ImmigrationCanada 等，按 subreddit 自我宣传规则）、V2EX / 即刻 / X、Telegram 群组、Hacker News（Show HN）。

---

## 中文版

### 做了个开源移民政策哨兵：盯官方页面，变更 24 小时内推给你

等邀请轮的人都有过这种经历：cutoff 出了、轮次日期改了，你几天后才知道。

**immigration-rules sentinel** 是一个开源监测器：每天 Diff 各国移民局官方公开页（IRCC Express Entry 轮次页、日本入管厅公告等），发现变更自动生成摘要草稿，经人工确认后推送到 Telegram / RSS，并永久存档每次快照（git 即历史）。

特点：
- **只盯官方页**——不爬中介、不自造数据，每条通知附官方链接
- **人工确认**——自动检测 + 人工摘要，拒绝误报轰炸
- **全开源**——MIT/Apache 级别的透明度，欢迎认领你熟悉的国家的监控目标
- **不只是通知**——这是跨国移民规则库（Rules-as-Code）的情报层，长期会做成带官方算例回归测试的规则引擎与 Agent Skill

仓库：<GitHub 链接> · Telegram 频道：<频道链接> · RSS：<链接>

## English

### Open-source immigration policy sentinel: official-page changes pushed within 24h

**immigration-rules sentinel** diffs official government pages daily (IRCC Express Entry rounds, Japan ISA announcements, more), drafts a human-reviewed summary for every change, and pushes to Telegram/RSS — with every snapshot archived in git.

- Official pages only; every alert links to the source
- Auto-detection + human-verified summaries (no noise)
- Fully open source — claim a country you know and help monitor
- Long-term: this feeds a cross-border rules-as-code library with official worked-example regression tests and an Agent Skill

Repo: <link> · Telegram: <link> · RSS: <link>

---

## 首次实战段落（占位，公布日填充）

> 加拿大东部时间 X 月 X 日，IRCC 公布 2027-29 移民水平计划：〔由哨兵捕获的真实变更摘要〕。我们的检测 Issue 在变更后 X 小时内创建：〔Issue 链接〕。

## 发布前检查

- [ ] GitHub 仓库已公开、README 完整、snapshot workflow 已连续 3 天绿
- [ ] Telegram 频道已建、bot 已接入、secrets 已配置
- [ ] 公告中所有链接可点开
- [ ] 首条真实变更已在 changelog（有真实案例比介绍更有说服力）
- [ ] 各平台发帖遵守其自我推广规则
