# 贡献指南

感谢参与。这个项目的信用完全建立在「每条规则可回溯到官方原文」之上——以下约束不是流程繁琐，而是项目的生存条件。

## 认领制：一国一 maintainer

- 认领某个国家的规则维护后，你是该国规则数据的第一责任人（见 [GOVERNANCE.md](GOVERNANCE.md)）。
- 认领方式：开 Issue 标题 `claim: <country>`，写明你与该国移民体系的关系（已上岸/从业/长期研究）。

## 规则变更 PR 的硬性要求

**模板见 [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)，缺任何一项不进入评审：**

1. **官方来源 URL**——每条变更逐条列出，必须 https 且指向官方域名（政府/移民局/官方指定机构）。新闻、中介博客、维基不可以作为 `source_url`，只能作为 Issue 讨论线索。
2. **`effective_date`**——该规则现行文本的官方生效日期，不得晚于今天。
3. **`last_verified`**——你本人对照官方原文核对完成的日期。
4. **官方算例**——新增或修改打分规则（`scoring`）必须附官方 worked examples 作为 golden test（`engine/tests/golden/`），本地跑通：`python scripts/validate_rules.py`。
5. **只改数据**——PR 不得触碰 `engine/`、`schema/`、`scripts/`（这些由 core maintainer 管理）。

## 口径纪律

- 术语必须与官方**现行**口径逐字对齐。例：澳洲用 CSOL / MLTSSL 而不是已废止的 SOL；职业代码用 NOC 2021 而不是旧版。
- 引用官方原文时保留原文语言，附中文/英文注释可以，替换不行。
- 不确定的数字不要猜：宁可留 TODO 开 Issue 讨论，也不写一个「大概对」的值。

## 禁止事项

- 用爬取结果直接改规则（哨兵只提 Issue，规则变更永远走人工 PR）。
- 提交未经人工核对的 LLM 生成的规则内容。
- 在 `source_url` 填非官方链接凑数。

## 本地验证

```bash
python scripts/validate_rules.py   # schema + 溯源 + staleness + golden fixture
```

## 许可

提交即表示同意你的贡献按仓库双许可发布：规则数据 CC BY 4.0，代码 Apache-2.0（见 `LICENSES/`）。

## 响应时效

- 规则错误报告（[模板](.github/ISSUE_TEMPLATE/rule-error.md)）：48 小时内评估并回复。
- 一般 PR：7 天内首次响应。
