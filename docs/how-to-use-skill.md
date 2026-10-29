# 如何使用 immigration-assess skill

> 安装状态：已装入运行时目录 `~/.zcode/skills/immigration-assess/`（Agent 运行时自动扫描）。
> 依赖自引导：脚本检测到缺 jsonschema/pyyaml 会自动用仓库 `.venv` 重跑，任何 Python 环境都能用。

## 一、在 Agent 里用（推荐）

**开一个新会话**（skill 发现机制在会话启动时加载）。之后直接用自然语言提问即可，Agent 会自动触发 skill：

```
硕士 5 年 Java，能移民哪些国家？
帮我算加拿大 EE 的 CRS
日本高度人才 80 分怎么凑？
移民加拿大要准备哪些材料？
我雅思 6.5 能申请加拿大吗？
加拿大和日本哪个快？
```

也支持显式调用：`/immigration-assess`（若运行时将其列为可调用 skill）。

### 它会做什么

1. **收集画像**：缺字段时逐项追问（年龄、学历、语言成绩、工作年资、年收入、婚姻/子女、意向国）
2. **跑确定性计算**：gates 前置 → 算分 → cutoff gap 对齐（脚本执行，Agent 不心算）
3. **输出报告**：资格矩阵（✅/⚠️/◻️/❌ + 原因 + 官方链接 + 置信度标记）→ 各通路明细 → 免责与转介

### 它会说什么不算（边界）

- 不做个案移民建议（「你应该走 X」）——输出条件式信息 + 转介持牌代理
- 不评估澳洲 NIV/杰出人才、德国机会卡（信息层：只给官方链接）
- 不翻译文件、不写申诉信、不办签证预约

## 二、不用 Agent，手动跑 CLI

```bash
# 用仓库 .venv（推荐）
F:\Development\skillsproject\immigration-rules\.venv\Scripts\python.exe \
  skill/immigration-assess/scripts/assess.py 你的画像.json

# 或系统 Python（自动引导到 .venv）
python skill/immigration-assess/scripts/assess.py 你的画像.json

# 参数
--format json        # 机器可读输出
--lang zh|en|ja      # 报告语言（固定标签本地化；规则数据文本保持中文，由 Agent 翻译呈现）
--as-of 2026-11-15   # 评估基准日（CRS 双制切换：11-03 前现行制，之后新政制）
```

画像格式参考 `engine/tests/fixtures/sample_profile.json`（字段口径见 skill 的 `references/output-guidelines.md`）。

## 三、注意事项

- **年龄**：按评估当天计算（评估日 ≠ 申请日时会有差异，报告已注明口径）
- **币种**：日本年收必须以日元计；加拿大 job offer 分档（2x/1.5x/1.3x）相对加拿大平均中位薪资
- **时效**：规则库 `last_verified` 超过 90 天输出降级为 ○ 待复核——看到 ○ 说明该通路近期未人工核对，用官方页复核后再决策
- **未计入项**：报告会显式列出（如 job offer 现行值、法语 NCLC、特别加算等）——总分可能被低估，务必阅读
- **CRS 新政**：2026-11-03 前评估走现行制；11-03 后评估自动走新政制（`regime_switch`），也可手动 `--as-of 2026-11-03` 提前看新政结果

## 四、验证 skill 是否就绪

```bash
python skill/immigration-assess/scripts/run_golden_tests.py   # 应输出 21/21 通过
```
