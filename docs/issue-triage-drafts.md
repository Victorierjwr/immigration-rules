# 哨兵 Issue 分诊草稿（2026-11-20）

> 用法：打开对应 GitHub Issue → 把「变了什么 / 对谁有影响」段落粘贴进模板 → 按结论加标签。加 `confirmed` 会自动发布到 changelog/RSS/TG 并关闭 Issue；加 `false-positive` 直接关闭。

## Issue #1 — [sentinel] japan isa_japan 页面变更 2026-11-02

**结论：false-positive**

- 变了什么：香川（Takamatsu）机关的招聘信息更新；特定技能（食品服务）旧公告移除。
- 对谁有影响：无——页面内容维护，非政策语义（无分数/日期/清单/流程/费用变化）。
- 处置：加 `false-positive` 标签并关闭。同一目标的后续变更（11-04/11-06/11-09/11-10/11-11/11-13/11-14 快照）均为同类内容维护，一并按误报处理。

## Issue #2 — [sentinel] canada ircc_changes 页面变更 2026-11-18

**结论：confirmed（真实政策变更）**

### 变了什么
2026-11-17 生效：研究员类别资格修正——大学教师/讲师（NOC 41200）的加拿大工作经验与 job offer 可计入由加拿大实体支付的 stipend/grant/bursary/scholarship 等非薪资报酬；中学后教学研究助理（NOC 41201）移出「Researchers with Canadian work experience」类别。同页确认 11-03 条款细化：劳动力市场整合因子的加拿大工作经验计入窗口为**近 10 年**；high-wage 经验要求为近 10 年内至少 1 年（1,560 小时）。

### 对谁有影响
- 博士后/研究者群体：NOC 41201 经历不再计入研究员类别；NOC 41200 非薪资资助经历变得可用。
- 有较长加拿大工龄的申请人：LMI 因子只计近 10 年经验——早期经验不计分。
- 已在规则库更新：categories.yaml（researchers effective_note）、ee_crs.yaml（10 年窗口注记）。

### 官方链接
- https://www.canada.ca/en/immigration-refugees-citizenship/services/immigrate-canada/express-entry/changes.html

### 规则库联动
已在 commit（见 git log）更新 categories.yaml 与 ee_crs.yaml——本 Issue 发布后即完成闭环。
